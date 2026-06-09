"""Resolve batch report context for single-game drill-down views."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from django.contrib.auth.models import User

from ..models import BatchAnalysisReport
from .alignment_score import compute_coach_alignment_score


def _normalize_pattern_label(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, dict):
        return (
            str(
                value.get("pattern") or value.get("title") or value.get("label") or ""
            ).strip()
            or None
        )
    text = str(value).strip()
    return text or None


def _lookup_batch_report(user: User, batch_id: Any) -> Optional[BatchAnalysisReport]:
    if batch_id in (None, ""):
        return None

    queryset = BatchAnalysisReport.objects.filter(user=user)

    try:
        numeric_id = int(batch_id)
    except (TypeError, ValueError):
        numeric_id = None

    if numeric_id is not None:
        report = queryset.filter(id=numeric_id).first()
        if report:
            return report

    return queryset.filter(task_id=str(batch_id)).first()


def _per_game_for_saved_id(
    per_game_results: List[Dict[str, Any]],
    game_id: int,
) -> Optional[Dict[str, Any]]:
    for game_result in per_game_results:
        if not isinstance(game_result, dict):
            continue
        saved_id = game_result.get("saved_game_id")
        if saved_id is not None and int(saved_id) == int(game_id):
            return game_result
    return None


def _find_linked_moment(
    *,
    batch_summary: Dict[str, Any],
    per_game_results: List[Dict[str, Any]],
    game_id: int,
    move_number: Optional[int],
) -> Optional[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []

    top_moments = batch_summary.get("top_critical_moments") or []
    if isinstance(top_moments, list):
        for moment in top_moments:
            if not isinstance(moment, dict):
                continue
            saved_id = moment.get("saved_game_id")
            if saved_id is not None and int(saved_id) == int(game_id):
                candidates.append(moment)

    game_result = _per_game_for_saved_id(per_game_results, game_id)
    if game_result:
        for moment in game_result.get("critical_moments") or []:
            if isinstance(moment, dict):
                candidates.append({**moment, "saved_game_id": game_id})

    if not candidates:
        return None

    if move_number is not None:
        for moment in candidates:
            if int(moment.get("move_number") or 0) == int(move_number):
                return moment

    return candidates[0]


def _normalize_match_text(value: Any) -> str:
    return str(value or "").replace("_", " ").strip().lower()


def _match_recurring_weakness(
    batch_summary: Dict[str, Any],
    *,
    priority: Optional[Dict[str, Any]],
    pattern_label: Optional[str],
) -> Optional[Dict[str, Any]]:
    weaknesses = batch_summary.get("recurring_weaknesses") or []
    if not isinstance(weaknesses, list) or not weaknesses:
        return None

    needles = []
    if priority and priority.get("title"):
        needles.append(_normalize_match_text(priority.get("title")))
    if pattern_label:
        needles.append(_normalize_match_text(pattern_label))

    for weakness in weaknesses:
        if not isinstance(weakness, dict):
            continue
        pattern = _normalize_match_text(weakness.get("pattern"))
        if not pattern:
            continue
        for needle in needles:
            if needle and (needle in pattern or pattern in needle):
                return weakness

    if priority:
        first = weaknesses[0]
        return first if isinstance(first, dict) else None
    return None


def _parse_pattern_frequency(
    frequency: Any,
    *,
    games_count: int,
) -> Tuple[Optional[int], Optional[int]]:
    if frequency in (None, ""):
        return None, games_count or None

    text = str(frequency)
    ratio_match = re.search(r"(\d+)\s*/\s*(\d+)", text)
    if ratio_match:
        return int(ratio_match.group(1)), int(ratio_match.group(2))

    count_match = re.search(r"(\d+)", text)
    if count_match:
        return int(count_match.group(1)), games_count or None

    return None, games_count or None


def _resolve_priority(
    coaching_report: Dict[str, Any],
    priority_index: Optional[int],
) -> Optional[Dict[str, Any]]:
    priorities = coaching_report.get("top_3_priorities") or []
    if not isinstance(priorities, list) or not priorities:
        return None

    if priority_index is not None and priority_index > 0:
        idx = priority_index - 1
        if 0 <= idx < len(priorities) and isinstance(priorities[idx], dict):
            return priorities[idx]

    first = priorities[0]
    return first if isinstance(first, dict) else None


def game_qualifies_for_batch_waiver(
    user: User,
    game_id: int,
    batch_id: Any,
) -> bool:
    """True when game is cited inside the user's batch report."""
    report = _lookup_batch_report(user, batch_id)
    if not report:
        return False

    per_game_results = (
        report.per_game_results if isinstance(report.per_game_results, list) else []
    )
    return _per_game_for_saved_id(per_game_results, game_id) is not None


def resolve_batch_context_for_game(
    user: User,
    game_id: int,
    *,
    batch_id: Any = None,
    move_number: Optional[int] = None,
    priority_index: Optional[int] = None,
    single_game_moments: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Build batch_context for GET /games/{id}/analysis when batch_id query param is present.
    """
    report = _lookup_batch_report(user, batch_id)
    if not report:
        return None

    batch_summary = (
        report.batch_summary if isinstance(report.batch_summary, dict) else {}
    )
    coaching_report = (
        report.coaching_report if isinstance(report.coaching_report, dict) else {}
    )
    per_game_results = (
        report.per_game_results if isinstance(report.per_game_results, list) else []
    )

    game_result = _per_game_for_saved_id(per_game_results, game_id)
    linked_moment = _find_linked_moment(
        batch_summary=batch_summary,
        per_game_results=per_game_results,
        game_id=game_id,
        move_number=move_number,
    )
    priority = _resolve_priority(coaching_report, priority_index)

    pattern_label = None
    if priority:
        pattern_label = _normalize_pattern_label(priority.get("title"))
    if not pattern_label:
        weaknesses = batch_summary.get("recurring_weaknesses") or []
        if isinstance(weaknesses, list) and weaknesses:
            pattern_label = _normalize_pattern_label(weaknesses[0])

    opening_name = (game_result or {}).get("opening_name")
    opening_eco = (game_result or {}).get("eco_code")
    game_result_label = (game_result or {}).get("result")

    phase_performance = batch_summary.get("phase_performance") or {}
    if not isinstance(phase_performance, dict):
        phase_performance = {}

    classification_disclaimer = None
    if linked_moment and single_game_moments:
        batch_class = str(linked_moment.get("type") or "").lower()
        move_no = linked_moment.get("move_number")
        for moment in single_game_moments:
            if not isinstance(moment, dict):
                continue
            if int(moment.get("move_number") or 0) != int(move_no or 0):
                continue
            single_class = str(
                moment.get("type") or moment.get("classification") or ""
            ).lower()
            if batch_class and single_class and batch_class != single_class:
                classification_disclaimer = (
                    f"Batch (depth-14) flagged this as {batch_class}; "
                    f"depth-20 review shows {single_class}. "
                    "Use the depth-20 label for this drill-down."
                )
            break

    matched_weakness = _match_recurring_weakness(
        batch_summary,
        priority=priority,
        pattern_label=pattern_label,
    )
    pattern_frequency = (
        matched_weakness.get("frequency")
        if isinstance(matched_weakness, dict)
        else None
    )
    pattern_count, batch_game_count = _parse_pattern_frequency(
        pattern_frequency,
        games_count=report.games_count or len(per_game_results),
    )

    coach_alignment = compute_coach_alignment_score(
        priority=priority,
        batch_worst_phase=batch_summary.get("worst_phase"),
        single_game_moments=single_game_moments,
    )

    return {
        "batch_id": report.pk,
        "task_id": report.task_id,
        "games_count": report.games_count,
        "batch_game_count": batch_game_count,
        "pattern_count": pattern_count,
        "pattern_frequency": pattern_frequency,
        "priority": priority,
        "priority_rank": (
            priority.get("rank") if isinstance(priority, dict) else priority_index
        ),
        "pattern_label": pattern_label,
        "linked_moment": linked_moment,
        "opening_name": opening_name,
        "opening_eco": opening_eco,
        "game_result": game_result_label,
        "batch_phase_performance": phase_performance,
        "batch_worst_phase": batch_summary.get("worst_phase"),
        "classification_disclaimer": classification_disclaimer,
        "coaching_summary": coaching_report.get("executive_summary")
        or coaching_report.get("summary"),
        "coach_alignment": coach_alignment,
    }


def resolve_batch_context_for_analysis(
    user: User,
    game_id: int,
    *,
    batch_id: Any = None,
    move_number: Optional[int] = None,
    priority_index: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Lightweight batch context for coaching generation during analyze."""
    context = resolve_batch_context_for_game(
        user,
        game_id,
        batch_id=batch_id,
        move_number=move_number,
        priority_index=priority_index,
        single_game_moments=None,
    )
    if not context:
        return None

    slim = dict(context)
    slim.pop("classification_disclaimer", None)
    return slim
