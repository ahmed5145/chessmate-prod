"""Deep links from batch reports into single-game drill-down."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .email_utils import get_frontend_base_url


def build_worst_moment_deep_review_url(batch_report) -> Optional[str]:
    """First batch-wide critical moment with a saved game id."""
    summary = batch_report.batch_summary if isinstance(batch_report.batch_summary, dict) else {}
    moments = summary.get("top_critical_moments") or []
    if not isinstance(moments, list):
        return None

    for moment in moments:
        if not isinstance(moment, dict):
            continue
        saved_game_id = moment.get("saved_game_id")
        move_number = moment.get("move_number")
        if saved_game_id in (None, ""):
            continue
        base = f"{get_frontend_base_url()}/game/{saved_game_id}/analysis"
        params = [f"batch={batch_report.pk}"]
        if move_number is not None:
            params.append(f"move={move_number}")
        return f"{base}?{'&'.join(params)}"

    per_game = batch_report.per_game_results if isinstance(batch_report.per_game_results, list) else []
    for game_result in per_game:
        if not isinstance(game_result, dict):
            continue
        saved_game_id = game_result.get("saved_game_id")
        if saved_game_id in (None, ""):
            continue
        moments = game_result.get("critical_moments") or []
        if not moments:
            continue
        first = moments[0] if isinstance(moments[0], dict) else {}
        move_number = first.get("move_number")
        base = f"{get_frontend_base_url()}/game/{saved_game_id}/analysis"
        params = [f"batch={batch_report.pk}"]
        if move_number is not None:
            params.append(f"move={move_number}")
        return f"{base}?{'&'.join(params)}"

    return None


def worst_moment_summary(batch_report) -> Dict[str, Any]:
    summary = batch_report.batch_summary if isinstance(batch_report.batch_summary, dict) else {}
    moments = summary.get("top_critical_moments") or []
    if isinstance(moments, list) and moments and isinstance(moments[0], dict):
        return moments[0]
    return {}
