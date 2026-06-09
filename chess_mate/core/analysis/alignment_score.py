"""Coach alignment score — batch phase claim vs single-game critical moments (SRG-11)."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional

_PHASE_KEYWORDS = {
    "opening": ("opening", "prep", "repertoire", "development"),
    "middlegame": ("middlegame", "tactic", "tactical", "calculation", "vision"),
    "endgame": ("endgame", "conversion", "technique", "pawn endgame"),
}


def _normalize_text(value: Any) -> str:
    return str(value or "").replace("_", " ").strip().lower()


def _infer_priority_phase(
    priority: Optional[Dict[str, Any]],
    batch_worst_phase: Optional[str],
) -> Optional[str]:
    if isinstance(priority, dict):
        blob = _normalize_text(
            " ".join(
                str(priority.get(key) or "")
                for key in ("title", "specific_drill", "how_to_fix", "why_it_matters")
            )
        )
        for phase, keywords in _PHASE_KEYWORDS.items():
            if any(keyword in blob for keyword in keywords):
                return phase

    if batch_worst_phase in ("opening", "middlegame", "endgame"):
        return batch_worst_phase
    return None


def _moment_phase(moment: Dict[str, Any]) -> Optional[str]:
    phase = moment.get("phase")
    if phase in ("opening", "middlegame", "endgame"):
        return phase
    return None


def _alignment_tier(pct: int) -> str:
    if pct >= 75:
        return "high"
    if pct >= 50:
        return "medium"
    return "low"


def compute_coach_alignment_score(
    *,
    priority: Optional[Dict[str, Any]],
    batch_worst_phase: Optional[str],
    single_game_moments: Optional[List[Dict[str, Any]]],
) -> Optional[Dict[str, Any]]:
    """
    Score how well single-game critical moments confirm the batch coaching focus.

    alignment = moments in batch target phase / all single-game critical moments
    """
    moments = [
        moment
        for moment in (single_game_moments or [])
        if isinstance(moment, dict) and _moment_phase(moment)
    ]
    if not moments:
        return None

    target_phase = _infer_priority_phase(priority, batch_worst_phase)
    if not target_phase:
        return None

    relevant_count = len(moments)
    confirmed_count = sum(
        1 for moment in moments if _moment_phase(moment) == target_phase
    )
    alignment_pct = (
        int(round((confirmed_count / relevant_count) * 100)) if relevant_count else 0
    )

    phase_counts = Counter(_moment_phase(moment) for moment in moments)
    dominant_phase = phase_counts.most_common(1)[0][0] if phase_counts else None

    mismatch_note = None
    if confirmed_count == 0 and dominant_phase and dominant_phase != target_phase:
        mismatch_note = (
            f"Batch flagged {target_phase}; this game's biggest swings were in the "
            f"{dominant_phase} — still worth review."
        )

    headline = (
        f"Batch focused on {target_phase} — this game confirms "
        f"{confirmed_count}/{relevant_count} critical moments."
    )

    return {
        "target_phase": target_phase,
        "confirmed_moments": confirmed_count,
        "relevant_moments": relevant_count,
        "alignment_pct": alignment_pct,
        "tier": _alignment_tier(alignment_pct),
        "headline": headline,
        "tooltip": (
            f"{confirmed_count} of {relevant_count} depth-20 critical moments occurred "
            f"in the batch's {target_phase} focus area."
        ),
        "mismatch_note": mismatch_note,
        "dominant_phase": dominant_phase,
    }
