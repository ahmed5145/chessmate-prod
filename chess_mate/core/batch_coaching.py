"""
Shared batch coaching regeneration (API + Django admin).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from .analysis.coaching_generator import (
    CoachingGeneratorError,
    generate_coaching_report,
)
from .analysis.per_game_coach_generator import (
    attach_coach_notes_to_results,
    generate_per_game_coach_notes,
)
from .models import BatchAnalysisReport

logger = logging.getLogger(__name__)


def regenerate_batch_coaching(batch_report: BatchAnalysisReport) -> Tuple[bool, str]:
    """
    Re-run OpenAI coaching from frozen batch_summary + per_game_results.

    Returns (success, message).
    """
    if batch_report.status not in ("completed", "partial"):
        return False, "Batch Coach must finish before regenerating coaching."

    batch_summary = batch_report.batch_summary
    per_game_results: List[Dict[str, Any]] = list(batch_report.per_game_results or [])
    if not batch_summary or len(per_game_results) < 5:
        return False, "Insufficient saved analysis data to regenerate coaching."

    try:
        coaching_report = generate_coaching_report(
            batch_summary,
            per_game_results,
            player_rating=batch_summary.get("player_rating"),
        )
    except CoachingGeneratorError as exc:
        logger.warning(
            "Coaching regeneration failed for batch %s: %s", batch_report.id, exc
        )
        return False, f"Coaching regeneration failed: {exc}"

    try:
        coach_notes = generate_per_game_coach_notes(
            per_game_results,
            player_rating=batch_summary.get("player_rating"),
        )
        per_game_results = attach_coach_notes_to_results(per_game_results, coach_notes)
        batch_report.per_game_results = per_game_results
    except Exception as exc:
        logger.warning(
            "Per-game coach note regeneration failed for batch %s: %s",
            batch_report.id,
            exc,
        )

    batch_report.coaching_report = coaching_report
    update_fields = ["coaching_report", "per_game_results", "updated_at"]
    failed_list = batch_report.failed_games or []
    if batch_report.status == "partial" and not failed_list:
        batch_report.status = "completed"
        update_fields.append("status")
    batch_report.save(update_fields=update_fields)
    try:
        from .priority_inbox import seed_priority_inbox_from_batch

        seed_priority_inbox_from_batch(batch_report)
    except Exception as exc:
        logger.warning(
            "Priority inbox seed failed after coaching regenerate for batch %s: %s",
            batch_report.id,
            exc,
        )
    return True, "Coaching regenerated successfully."
