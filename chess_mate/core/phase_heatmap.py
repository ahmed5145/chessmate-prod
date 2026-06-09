"""Win/loss × phase heatmap for dashboard (SRG-18)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from django.db.models import Q

from .models import BatchAnalysisReport, GameAnalysis, Profile
from .stats_helpers import get_game_counts, resolve_game_opponent_display

RESULTS = ("win", "loss", "draw")
PHASES = ("opening", "middlegame", "endgame")
_MIN_GAMES = 5
_MIN_CELL_GAMES = 3
_LOW_ACCURACY_THRESHOLD = 55.0
_HIGH_EVAL_DROP_THRESHOLD = 0.35


def _normalize_player_result(
    result_value: Any,
    player_color: Optional[str],
) -> Optional[str]:
    raw = str(result_value or "").strip().lower()
    color = str(player_color or "white").lower()

    if raw in ("win", "w"):
        return "win"
    if raw in ("loss", "l"):
        return "loss"
    if raw in ("draw", "d", "1/2-1/2", "1/2", "*"):
        return "draw"
    if raw == "1-0":
        return "win" if color == "white" else "loss"
    if raw == "0-1":
        return "loss" if color == "white" else "win"
    return None


def _phase_accuracy(phase_data: Dict[str, Any]) -> Optional[float]:
    if not isinstance(phase_data, dict):
        return None
    if phase_data.get("accuracy") is not None:
        try:
            return float(phase_data["accuracy"])
        except (TypeError, ValueError):
            pass
    moves = int(phase_data.get("moves") or 0)
    if moves <= 0:
        return None
    blunders = int(phase_data.get("blunders") or 0)
    mistakes = int(phase_data.get("mistakes") or 0)
    inaccuracies = int(phase_data.get("inaccuracies") or 0)
    penalty = blunders * 3 + mistakes * 2 + inaccuracies
    return max(0.0, min(100.0, 100.0 - (penalty / moves) * 20.0))


def _phase_eval_signal(phase_data: Dict[str, Any]) -> Optional[float]:
    if not isinstance(phase_data, dict):
        return None
    if phase_data.get("avg_eval_drop") is not None:
        try:
            return float(phase_data["avg_eval_drop"])
        except (TypeError, ValueError):
            pass
    if phase_data.get("avg_eval_swing") is not None:
        try:
            return float(phase_data["avg_eval_swing"])
        except (TypeError, ValueError):
            pass
    return None


def _review_href(saved_game_id: int, move_number: Optional[int] = None) -> str:
    href = f"/game/{saved_game_id}/analysis?mode=review"
    if move_number is not None:
        href = f"{href}&move={move_number}"
    return href


def _example_from_moments(
    saved_game_id: int,
    moments: List[Dict[str, Any]],
    phase: str,
) -> Dict[str, Any]:
    for moment in moments:
        if not isinstance(moment, dict):
            continue
        if moment.get("phase") and moment.get("phase") != phase:
            continue
        move_number = moment.get("move_number")
        return {
            "saved_game_id": saved_game_id,
            "move_number": move_number,
            "href": _review_href(saved_game_id, move_number),
        }
    return {
        "saved_game_id": saved_game_id,
        "move_number": None,
        "href": _review_href(saved_game_id),
    }


def _collect_batch_games(user) -> Dict[int, Dict[str, Any]]:
    collected: Dict[int, Dict[str, Any]] = {}
    batches = BatchAnalysisReport.objects.filter(
        user=user,
        status__in=["completed", "partial"],
    ).order_by("-created_at")[:8]

    for batch in batches:
        per_game = (
            batch.per_game_results if isinstance(batch.per_game_results, list) else []
        )
        for row in per_game:
            if not isinstance(row, dict):
                continue
            saved_id = row.get("saved_game_id")
            if saved_id is None:
                continue
            try:
                game_id = int(saved_id)
            except (TypeError, ValueError):
                continue
            player_result = _normalize_player_result(
                row.get("result") or row.get("player_result"),
                row.get("player_color"),
            )
            if not player_result:
                continue
            collected[game_id] = {
                "saved_game_id": game_id,
                "player_result": player_result,
                "phase_breakdown": row.get("phase_breakdown") or {},
                "critical_moments": row.get("critical_moments") or [],
                "opponent": row.get("opponent"),
            }
    return collected


def _collect_single_game_rows(
    user, profile: Optional[Profile]
) -> Dict[int, Dict[str, Any]]:
    collected: Dict[int, Dict[str, Any]] = {}
    analyses = (
        GameAnalysis.objects.filter(game__user=user)
        .filter(
            Q(game__status="analyzed")
            | Q(game__analysis_status="analyzed")
            | Q(game__analysis_status="completed")
        )
        .select_related("game")
        .order_by("-created_at")[:80]
    )

    for analysis in analyses:
        game = analysis.game
        if game is None:
            continue
        game_id = game.id
        if game_id in collected:
            continue

        analysis_data = (
            analysis.analysis_data if isinstance(analysis.analysis_data, dict) else {}
        )
        metrics = (
            analysis_data.get("metrics", {})
            if isinstance(analysis_data.get("metrics"), dict)
            else {}
        )
        phases = (
            metrics.get("phases") if isinstance(metrics.get("phases"), dict) else {}
        )
        phase_breakdown = {}
        for phase_name in PHASES:
            phase_metrics = phases.get(phase_name)
            if (
                isinstance(phase_metrics, dict)
                and phase_metrics.get("accuracy") is not None
            ):
                phase_breakdown[phase_name] = {
                    "accuracy": phase_metrics.get("accuracy"),
                    "moves": phase_metrics.get("opportunities")
                    or phase_metrics.get("total_moves")
                    or 1,
                    "mistakes": phase_metrics.get("mistakes", 0),
                    "blunders": phase_metrics.get("blunders", 0),
                }

        if not phase_breakdown:
            continue

        player_color = None
        if profile:
            from .stats_helpers import build_single_game_context

            player_color = build_single_game_context(game, profile).get("player_color")
        player_result = _normalize_player_result(game.result, player_color)
        if not player_result:
            continue

        coaching = analysis_data.get("coaching")
        if not isinstance(coaching, dict):
            coaching = {}
        moments = coaching.get("critical_moments") or analysis_data.get(
            "critical_moments", []
        )

        collected[game_id] = {
            "saved_game_id": game_id,
            "player_result": player_result,
            "phase_breakdown": phase_breakdown,
            "critical_moments": moments if isinstance(moments, list) else [],
            "opponent": resolve_game_opponent_display(game, profile),
        }
    return collected


def _merge_game_sources(
    batch_games: Dict[int, Dict[str, Any]],
    single_games: Dict[int, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    merged = dict(single_games)
    merged.update(batch_games)
    return list(merged.values())


def _cell_key(result: str, phase: str) -> str:
    return f"{result}:{phase}"


def _headline_for_cell(result: str, phase: str, avg_accuracy: float) -> str:
    if result == "loss" and phase == "middlegame":
        return "You lose winning middlegames"
    if result == "loss":
        return f"Trouble in the {phase}"
    if result == "win":
        return f"Shaky {phase} even in wins"
    return f"Low {phase} accuracy in draws"


def build_phase_result_heatmap(
    user, profile: Optional[Profile] = None
) -> Dict[str, Any]:
    counts = get_game_counts(user)
    analyzed_total = int(counts.get("analyzed") or 0)
    if analyzed_total < _MIN_GAMES:
        return {
            "show": False,
            "reason": "insufficient_analyzed_games",
            "analyzed_games": analyzed_total,
        }

    if profile is None:
        profile = Profile.objects.filter(user=user).first()

    games = _merge_game_sources(
        _collect_batch_games(user),
        _collect_single_game_rows(user, profile),
    )
    if len(games) < _MIN_GAMES:
        return {
            "show": False,
            "reason": "insufficient_phase_data",
            "analyzed_games": len(games),
        }

    cells: Dict[str, Dict[str, Any]] = {}
    for result in RESULTS:
        for phase in PHASES:
            key = _cell_key(result, phase)
            cells[key] = {
                "result": result,
                "phase": phase,
                "game_count": 0,
                "avg_accuracy": None,
                "avg_eval_drop": None,
                "highlight": False,
                "headline": None,
                "example_games": [],
                "_accuracy_total": 0.0,
                "_accuracy_count": 0,
                "_eval_total": 0.0,
                "_eval_count": 0,
            }

    for game in games:
        saved_id = game["saved_game_id"]
        player_result = game["player_result"]
        breakdown = game.get("phase_breakdown") or {}
        moments = game.get("critical_moments") or []
        opponent = game.get("opponent")

        for phase in PHASES:
            phase_data = breakdown.get(phase)
            if not isinstance(phase_data, dict):
                continue
            moves = int(phase_data.get("moves") or 0)
            accuracy = _phase_accuracy(phase_data)
            if moves <= 0 and accuracy is None:
                continue

            cell = cells[_cell_key(player_result, phase)]
            cell["game_count"] += 1
            if accuracy is not None:
                cell["_accuracy_total"] += accuracy
                cell["_accuracy_count"] += 1
            eval_signal = _phase_eval_signal(phase_data)
            if eval_signal is not None:
                cell["_eval_total"] += eval_signal
                cell["_eval_count"] += 1

            example = _example_from_moments(saved_id, moments, phase)
            if opponent:
                example["opponent"] = opponent
            if len(cell["example_games"]) < 3:
                if not any(
                    row.get("saved_game_id") == saved_id
                    for row in cell["example_games"]
                ):
                    cell["example_games"].append(example)

    highlighted: List[Dict[str, Any]] = []
    for cell in cells.values():
        if cell["_accuracy_count"]:
            cell["avg_accuracy"] = round(
                cell["_accuracy_total"] / cell["_accuracy_count"], 1
            )
        if cell["_eval_count"]:
            cell["avg_eval_drop"] = round(cell["_eval_total"] / cell["_eval_count"], 2)

        qualifies_accuracy = (
            cell["game_count"] >= _MIN_CELL_GAMES
            and cell["avg_accuracy"] is not None
            and cell["avg_accuracy"] < _LOW_ACCURACY_THRESHOLD
        )
        qualifies_eval = (
            cell["game_count"] >= _MIN_CELL_GAMES
            and cell["avg_eval_drop"] is not None
            and cell["avg_eval_drop"] >= _HIGH_EVAL_DROP_THRESHOLD
        )
        cell["highlight"] = qualifies_accuracy or qualifies_eval
        if cell["highlight"] and cell["avg_accuracy"] is not None:
            cell["headline"] = _headline_for_cell(
                cell["result"], cell["phase"], cell["avg_accuracy"]
            )
            highlighted.append(cell)

        for private_key in (
            "_accuracy_total",
            "_accuracy_count",
            "_eval_total",
            "_eval_count",
        ):
            cell.pop(private_key, None)

    highlighted.sort(
        key=lambda row: (
            -int(row.get("game_count") or 0),
            float(row.get("avg_accuracy") or 100),
        )
    )
    top_insight = None
    if highlighted:
        top = highlighted[0]
        example = (top.get("example_games") or [None])[0]
        top_insight = {
            "headline": top.get("headline"),
            "result": top.get("result"),
            "phase": top.get("phase"),
            "href": example.get("href") if isinstance(example, dict) else None,
        }

    return {
        "show": True,
        "analyzed_games": len(games),
        "results": list(RESULTS),
        "phases": list(PHASES),
        "cells": list(cells.values()),
        "highlighted_count": len(highlighted),
        "top_insight": top_insight,
    }
