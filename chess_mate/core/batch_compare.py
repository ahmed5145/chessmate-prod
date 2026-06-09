"""
Batch-to-batch comparison helpers (structured diff + short coach narrative).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set


def weakness_themes(summary: dict) -> Set[str]:
    themes: Set[str] = set()
    for item in summary.get("recurring_weaknesses") or []:
        if isinstance(item, dict):
            theme = (
                item.get("pattern")
                or item.get("theme")
                or item.get("type")
                or item.get("label")
            )
            if theme:
                themes.add(str(theme))
    return themes


def metric_delta(
    current_summary: dict, other_summary: dict, key: str
) -> Optional[float]:
    cur = current_summary.get(key)
    prev = other_summary.get(key)
    if cur is None or prev is None:
        return None
    try:
        return round(float(cur) - float(prev), 2)
    except (TypeError, ValueError):
        return None


def build_compare_narrative(
    *,
    metrics: Dict[str, Any],
    weaknesses: Dict[str, List[str]],
    current_summary: dict,
    other_summary: dict,
) -> str:
    """
    One-sentence progress readout from structured diffs only (no extra AI call).
    """
    parts: List[str] = []

    acc_delta = metrics.get("overall_accuracy_pct_delta")
    if acc_delta is not None:
        if acc_delta > 1:
            parts.append(f"move match improved by {acc_delta:.1f}%")
        elif acc_delta < -1:
            parts.append(f"move match dipped by {abs(acc_delta):.1f}%")

    stab_delta = metrics.get("overall_eval_stability_delta")
    if stab_delta is not None:
        stab_pct = float(stab_delta) * 100
        if stab_pct > 2:
            parts.append(f"eval stability improved by {stab_pct:.1f}%")
        elif stab_pct < -2:
            parts.append(f"eval stability slipped by {abs(stab_pct):.1f}%")

    resolved = weaknesses.get("resolved") or []
    persisting = weaknesses.get("persisting") or []
    new_patterns = weaknesses.get("new") or []

    if resolved:
        label = resolved[0].replace("_", " ")
        parts.append(f"you improved on {label}")
    if persisting and not resolved:
        label = persisting[0].replace("_", " ")
        parts.append(f"{label} is still recurring")
    if new_patterns:
        label = new_patterns[0].replace("_", " ")
        parts.append(f"watch for new pattern: {label}")

    cur_worst = current_summary.get("worst_phase")
    prev_worst = other_summary.get("worst_phase")
    if cur_worst and prev_worst and cur_worst != prev_worst:
        parts.append(f"weakest phase shifted from {prev_worst} to {cur_worst}")

    if not parts:
        return "Metrics are similar to your previous batch — keep running batches to track trends."

    sentence = ", ".join(parts[:3])
    return sentence[0].upper() + sentence[1:] + "."
