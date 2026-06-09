"""Batch-over-batch fix-rate — patterns resolved or improved (SRG-17)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import BatchAnalysisReport
from .moment_timeline import _infer_phase_from_pattern, build_moment_signature

FIX_RATE_TOOLTIP = (
    "Fixed means a recurring pattern from your previous batch no longer appears, "
    "or its average eval swing dropped by at least 0.1 pawns."
)


def _normalize_label(value: Any) -> str:
    return str(value or "").strip()


def _extract_patterns(batch_report: BatchAnalysisReport) -> Dict[str, Dict[str, Any]]:
    patterns: Dict[str, Dict[str, Any]] = {}
    summary = (
        batch_report.batch_summary
        if isinstance(batch_report.batch_summary, dict)
        else {}
    )
    coaching = (
        batch_report.coaching_report
        if isinstance(batch_report.coaching_report, dict)
        else {}
    )

    for weakness in summary.get("recurring_weaknesses") or []:
        if not isinstance(weakness, dict):
            continue
        label = _normalize_label(weakness.get("pattern"))
        if not label:
            continue
        phase = _infer_phase_from_pattern(label)
        signature = build_moment_signature(label, phase)
        patterns[signature] = {
            "signature": signature,
            "label": label,
            "phase": phase,
            "avg_eval_swing": weakness.get("avg_eval_swing"),
            "source": "weakness",
            "example_game_ids": weakness.get("example_game_ids") or [],
        }

    for priority in coaching.get("top_3_priorities") or []:
        if not isinstance(priority, dict):
            continue
        label = _normalize_label(priority.get("title"))
        if not label:
            continue
        signature = build_moment_signature(label, "middlegame")
        if signature in patterns:
            continue
        patterns[signature] = {
            "signature": signature,
            "label": label,
            "phase": "middlegame",
            "avg_eval_swing": None,
            "source": "priority",
            "example_game_ids": [],
            "priority_rank": priority.get("rank"),
        }

    return patterns


def _proof_game_id(
    batch_report: BatchAnalysisReport,
    pattern_label: str,
    *,
    prefer_absent: bool,
) -> Optional[int]:
    summary = (
        batch_report.batch_summary
        if isinstance(batch_report.batch_summary, dict)
        else {}
    )
    per_game = (
        batch_report.per_game_results
        if isinstance(batch_report.per_game_results, list)
        else []
    )
    normalized_label = _normalize_label(pattern_label).lower()

    if prefer_absent:
        for game in per_game:
            if not isinstance(game, dict):
                continue
            result = str(game.get("result") or "").lower()
            if result in ("win", "1-0", "0-1"):
                saved_id = game.get("saved_game_id")
                if saved_id:
                    return int(saved_id)

    for weakness in summary.get("recurring_weaknesses") or []:
        if not isinstance(weakness, dict):
            continue
        if _normalize_label(weakness.get("pattern")).lower() == normalized_label:
            for game_id in weakness.get("example_game_ids") or []:
                return int(game_id)

    for moment in summary.get("top_critical_moments") or []:
        if not isinstance(moment, dict):
            continue
        theme = moment.get("tactical_theme") or moment.get("type")
        if _normalize_label(theme).lower() == normalized_label:
            saved_id = moment.get("saved_game_id")
            if saved_id:
                return int(saved_id)

    for game in per_game:
        if not isinstance(game, dict):
            continue
        saved_id = game.get("saved_game_id")
        if saved_id:
            return int(saved_id)
    return None


def _swing_value(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_fix_rate_payload(
    current: BatchAnalysisReport,
    previous: BatchAnalysisReport,
) -> Dict[str, Any]:
    previous_patterns = _extract_patterns(previous)
    current_patterns = _extract_patterns(current)

    if not previous_patterns:
        return {"show": False, "reason": "no_previous_patterns"}

    rows: List[Dict[str, Any]] = []
    fixed_count = 0

    for signature, prev_row in previous_patterns.items():
        current_row = current_patterns.get(signature)
        prev_swing = _swing_value(prev_row.get("avg_eval_swing"))
        cur_swing = _swing_value(
            current_row.get("avg_eval_swing") if current_row else None
        )

        if current_row is None:
            status = "fixed"
            fixed_count += 1
            proof_game_id = _proof_game_id(
                current, prev_row["label"], prefer_absent=True
            )
        elif (
            prev_swing is not None
            and cur_swing is not None
            and (prev_swing - cur_swing) >= 0.1
        ):
            status = "improved"
            fixed_count += 1
            proof_game_id = _proof_game_id(
                current, prev_row["label"], prefer_absent=False
            )
        else:
            status = "persisting"
            proof_game_id = _proof_game_id(
                current, prev_row["label"], prefer_absent=False
            )

        rows.append(
            {
                "signature": signature,
                "label": prev_row["label"],
                "status": status,
                "previous_avg_swing": prev_swing,
                "current_avg_swing": cur_swing,
                "proof_game_id": proof_game_id,
            }
        )

    total_count = len(previous_patterns)
    month_label = (previous.created_at or previous.updated_at).strftime("%B")
    headline = (
        f"You fixed {fixed_count}/{total_count} patterns from your {month_label} batch."
    )

    return {
        "show": True,
        "fixed_count": fixed_count,
        "total_count": total_count,
        "headline": headline,
        "tooltip": FIX_RATE_TOOLTIP,
        "previous_batch_id": previous.id,
        "previous_batch_month": month_label,
        "patterns": rows,
        "new_patterns": [
            {
                "signature": signature,
                "label": row["label"],
                "status": "new",
            }
            for signature, row in current_patterns.items()
            if signature not in previous_patterns
        ],
    }


def build_dashboard_fix_rate(user) -> Dict[str, Any]:
    batches = list(
        BatchAnalysisReport.objects.filter(
            user=user,
            status__in=["completed", "partial"],
        ).order_by("-pk")[:2]
    )
    if len(batches) < 2:
        return {"show": False}
    return build_fix_rate_payload(batches[0], batches[1])
