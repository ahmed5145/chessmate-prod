"""Attach lost-game links to repertoire gaps (SRG-21)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

PHASES_OPENING = "opening"


def _player_outcome(game: Dict[str, Any]) -> str:
    raw = str(game.get("result") or "").strip()
    color = str(game.get("player_color") or "white").lower()
    if raw in ("1/2-1/2", "1/2", "*"):
        return "draw"
    if raw == "1-0":
        return "win" if color == "white" else "loss"
    if raw == "0-1":
        return "loss" if color == "white" else "win"
    lowered = raw.lower()
    if lowered in ("win", "loss", "draw"):
        return lowered
    return "unknown"


def _opening_matches_gap(game: Dict[str, Any], gap: Dict[str, Any]) -> bool:
    gap_name = str(gap.get("opening_name") or "").strip()
    game_name = str(game.get("opening_name") or "").strip()
    gap_eco = str(gap.get("eco_code") or "").strip().upper()
    game_eco = str(game.get("eco_code") or "").strip().upper()

    if gap_name and (game_name == gap_name or game_name.startswith(f"{gap_name}:")):
        return True
    if gap_eco and game_eco and gap_eco == game_eco:
        return True

    eco_codes = gap.get("eco_codes") or []
    if isinstance(eco_codes, list) and game_eco and game_eco in {str(code).strip().upper() for code in eco_codes}:
        return True
    return False


def _review_href(
    saved_game_id: int, batch_id: Optional[int], move_number: Optional[int]
) -> str:
    href = f"/game/{saved_game_id}/analysis?mode=review"
    if batch_id is not None:
        href = f"{href}&batch={batch_id}"
    if move_number is not None:
        href = f"{href}&move={move_number}"
    return href


def _opening_fen_from_game(game: Dict[str, Any]) -> Optional[str]:
    moments = game.get("critical_moments") or []
    if not isinstance(moments, list):
        return None
    for moment in moments:
        if not isinstance(moment, dict):
            continue
        if moment.get("phase") == PHASES_OPENING and moment.get("fen"):
            return str(moment["fen"])
    for moment in moments:
        if isinstance(moment, dict) and moment.get("fen"):
            return str(moment["fen"])
    return None


def _opening_moment_move(game: Dict[str, Any]) -> Optional[int]:
    moments = game.get("critical_moments") or []
    if not isinstance(moments, list):
        return None
    for moment in moments:
        if not isinstance(moment, dict):
            continue
        if (
            moment.get("phase") == PHASES_OPENING
            and moment.get("move_number") is not None
        ):
            try:
                return int(moment["move_number"])
            except (TypeError, ValueError):
                continue
    return None


def collect_lost_games_for_gap(
    gap: Dict[str, Any],
    per_game_results: List[Dict[str, Any]],
    *,
    batch_id: Optional[int] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    lost_games: List[Dict[str, Any]] = []
    gap_color = gap.get("player_color")

    for game in per_game_results:
        if not isinstance(game, dict):
            continue
        if gap_color and game.get("player_color") != gap_color:
            continue
        if not _opening_matches_gap(game, gap):
            continue
        if _player_outcome(game) != "loss":
            continue

        saved_id = game.get("saved_game_id")
        if saved_id is None:
            continue
        try:
            saved_game_id = int(saved_id)
        except (TypeError, ValueError):
            continue

        move_number = _opening_moment_move(game)
        lost_games.append(
            {
                "game_id": game.get("game_id"),
                "saved_game_id": saved_game_id,
                "opponent": game.get("opponent"),
                "date_played": game.get("date_played"),
                "opening_name": game.get("opening_name"),
                "eco_code": game.get("eco_code"),
                "platform": game.get("platform"),
                "platform_game_url": game.get("platform_game_url"),
                "opening_fen": _opening_fen_from_game(game),
                "move_number": move_number,
                "href": _review_href(saved_game_id, batch_id, move_number),
            }
        )
        if len(lost_games) >= limit:
            break

    return lost_games


def enrich_repertoire_gap(
    gap: Dict[str, Any],
    per_game_results: List[Dict[str, Any]],
    *,
    batch_id: Optional[int] = None,
) -> Dict[str, Any]:
    row = dict(gap)
    lost_games = collect_lost_games_for_gap(gap, per_game_results, batch_id=batch_id)
    row["lost_games"] = lost_games
    row["loss_count"] = len(lost_games)
    if row["loss_count"] > 0:
        row["loss_copy"] = f"You lost {row['loss_count']} game{'s' if row['loss_count'] != 1 else ''} in this line"
    else:
        row["loss_copy"] = None
    return row


def enrich_batch_summary_opening_gaps(
    batch_summary: Dict[str, Any],
    per_game_results: Optional[List[Dict[str, Any]]],
    *,
    batch_id: Optional[int] = None,
) -> Dict[str, Any]:
    summary = dict(batch_summary)
    games = per_game_results if isinstance(per_game_results, list) else []
    gaps = summary.get("repertoire_gaps")
    if isinstance(gaps, list) and gaps:
        summary["repertoire_gaps"] = [
            enrich_repertoire_gap(gap, games, batch_id=batch_id) if isinstance(gap, dict) else gap for gap in gaps
        ]
    return summary
