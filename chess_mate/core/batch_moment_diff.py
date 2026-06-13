"""Batch A vs B moment diff — swing trends across recurring patterns (SRG-20)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .fix_rate import _extract_patterns, _normalize_label, _proof_game_id, _swing_value
from .models import BatchAnalysisReport, Profile
from .moment_timeline import (
    _infer_phase_from_pattern,
    build_moment_signature,
    summarize_timeline_for_signature,
)


def _top_weaknesses(batch_report: BatchAnalysisReport, limit: int = 3) -> List[Dict[str, Any]]:
    summary = batch_report.batch_summary if isinstance(batch_report.batch_summary, dict) else {}
    weaknesses = [
        row
        for row in (summary.get("recurring_weaknesses") or [])
        if isinstance(row, dict) and _normalize_label(row.get("pattern"))
    ]
    weaknesses.sort(
        key=lambda row: float(row.get("avg_eval_swing") or 0),
        reverse=True,
    )
    return weaknesses[:limit]


def _build_sparkline(
    profile: Optional[Profile],
    signature: str,
    previous_swing: Optional[float],
    current_swing: Optional[float],
) -> List[float]:
    if profile is not None:
        timeline = summarize_timeline_for_signature(profile, signature)
        sparkline = timeline.get("sparkline")
        if isinstance(sparkline, list) and len(sparkline) >= 2:
            return [round(float(value), 2) for value in sparkline]

    values: List[float] = []
    if previous_swing is not None:
        values.append(round(previous_swing, 2))
    if current_swing is not None:
        values.append(round(current_swing, 2))
    return values


def _resolve_status(
    *,
    current_row: Optional[Dict[str, Any]],
    previous_swing: Optional[float],
    current_swing: Optional[float],
) -> str:
    if current_row is None:
        return "resolved"
    if previous_swing is not None and current_swing is not None and (previous_swing - current_swing) >= 0.1:
        return "resolved"
    return "unchanged"


def build_batch_moment_diff(
    current: BatchAnalysisReport,
    previous: Optional[BatchAnalysisReport],
    profile: Optional[Profile] = None,
) -> Dict[str, Any]:
    if previous is None:
        return {"show": False, "reason": "no_previous_batch"}

    previous_patterns = _extract_patterns(previous)
    current_patterns = _extract_patterns(current)

    if not previous_patterns and not current_patterns:
        return {"show": False, "reason": "no_patterns"}

    rows: List[Dict[str, Any]] = []
    seen_signatures: set[str] = set()
    resolved_count = 0
    unchanged_count = 0
    new_count = 0

    previous_weaknesses = _top_weaknesses(previous, 3)
    if not previous_weaknesses:
        previous_weaknesses = [
            {
                "pattern": row["label"],
                "avg_eval_swing": row.get("avg_eval_swing"),
            }
            for row in sorted(
                previous_patterns.values(),
                key=lambda item: float(item.get("avg_eval_swing") or 0),
                reverse=True,
            )[:3]
        ]

    for weakness in previous_weaknesses:
        label = _normalize_label(weakness.get("pattern"))
        phase = _infer_phase_from_pattern(label)
        signature = build_moment_signature(label, phase)
        seen_signatures.add(signature)

        previous_row = previous_patterns.get(signature, weakness)
        current_row = current_patterns.get(signature)
        previous_swing = _swing_value(
            weakness.get("avg_eval_swing") if isinstance(weakness, dict) else previous_row.get("avg_eval_swing")
        )
        current_swing = _swing_value(current_row.get("avg_eval_swing") if current_row else None)
        status = _resolve_status(
            current_row=current_row,
            previous_swing=previous_swing,
            current_swing=current_swing,
        )
        if status == "resolved":
            resolved_count += 1
            proof_game_id = (
                _proof_game_id(previous, label, prefer_absent=False)
                if current_row is None
                else _proof_game_id(current, label, prefer_absent=False)
            )
        else:
            unchanged_count += 1
            proof_game_id = _proof_game_id(current, label, prefer_absent=False)

        rows.append(
            {
                "signature": signature,
                "label": label,
                "status": status,
                "previous_swing": previous_swing,
                "current_swing": current_swing,
                "swing_delta": (
                    round(previous_swing - current_swing, 2)
                    if previous_swing is not None and current_swing is not None
                    else None
                ),
                "proof_game_id": proof_game_id,
                "sparkline": _build_sparkline(profile, signature, previous_swing, current_swing),
            }
        )

    for weakness in _top_weaknesses(current, 3):
        label = _normalize_label(weakness.get("pattern"))
        phase = _infer_phase_from_pattern(label)
        signature = build_moment_signature(label, phase)
        if signature in seen_signatures or signature in previous_patterns:
            continue
        seen_signatures.add(signature)
        current_swing = _swing_value(weakness.get("avg_eval_swing"))
        new_count += 1
        rows.append(
            {
                "signature": signature,
                "label": label,
                "status": "new",
                "previous_swing": None,
                "current_swing": current_swing,
                "swing_delta": None,
                "proof_game_id": _proof_game_id(current, label, prefer_absent=False),
                "sparkline": _build_sparkline(profile, signature, None, current_swing),
            }
        )

    month_label = (previous.created_at or previous.updated_at).strftime("%B")

    return {
        "show": True,
        "title": "Compared to last batch",
        "previous_batch_id": previous.id,
        "previous_batch_month": month_label,
        "counts": {
            "resolved": resolved_count,
            "unchanged": unchanged_count,
            "new": new_count,
        },
        "rows": rows[:6],
    }
