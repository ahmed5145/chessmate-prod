"""
Rating-band study guidance (text only — no AI).
Tailored using batch_summary signals when available.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _top_weakness_label(recurring_weaknesses: Optional[List[dict]]) -> Optional[str]:
    if not recurring_weaknesses:
        return None
    first = recurring_weaknesses[0]
    if not isinstance(first, dict):
        return None
    pattern = first.get("pattern") or first.get("theme")
    if pattern:
        return str(pattern).replace("_", " ")
    return None


def _tailor_band_advice(
    base: Dict[str, Any],
    *,
    worst_phase: Optional[str] = None,
    best_phase: Optional[str] = None,
    recurring_weaknesses: Optional[List[dict]] = None,
    repertoire_gaps: Optional[List[dict]] = None,
    endgame_insights: Optional[List[dict]] = None,
) -> Dict[str, Any]:
    tailored = dict(base)
    weakness = _top_weakness_label(recurring_weaknesses)
    has_repertoire_gaps = bool(repertoire_gaps)
    has_endgame_data = bool(endgame_insights)

    if worst_phase == "opening" or has_repertoire_gaps:
        tailored["focus"] = (
            "Your batch flagged the opening as the weakest phase — review repertoire gaps "
            "and prep before chasing deeper endgame study."
        )
        tailored["daily_drill"] = (
            "Pick one opening line from Opening matchups, study it for 15 minutes, "
            "then replay one critical moment from this batch."
        )
        return tailored

    if worst_phase == "middlegame" or weakness:
        theme = weakness or "tactical patterns"
        tailored["focus"] = (
            f"Middlegame accuracy slipped most often around {theme} — calculate forcing lines before committing."
        )
        tailored["daily_drill"] = (
            f"20 themed tactics on {theme}, then review one batch blunder where the same theme appeared."
        )
        return tailored

    if worst_phase == "endgame" and has_endgame_data:
        eg = endgame_insights[0] if endgame_insights else {}
        label = eg.get("label") or eg.get("endgame_type") or "endgame"
        label_text = str(label).replace("_", " ")
        tailored["focus"] = f"Endgame technique cost you eval — focus on {label_text} positions from this batch."
        study = eg.get("study_focus")
        if study:
            tailored["daily_drill"] = f"{study} Replay one endgame critical moment from the report."
        else:
            tailored["daily_drill"] = (
                f"Practice {label_text} on Lichess, then replay one endgame turning point from this batch."
            )
        return tailored

    if worst_phase and worst_phase != "endgame" and "endgame" in tailored.get("focus", "").lower():
        tailored["focus"] = tailored["focus"].replace(
            "punish imprecise endgames and repeat opening prep gaps",
            "tighten your weakest phase from this batch before adding new study topics",
        )
        if "endgame" in tailored.get("daily_drill", "").lower():
            tailored["daily_drill"] = (
                "Review your top 3 critical moments from this batch, then drill the pattern named in Top priorities."
            )

    if best_phase == "opening" and not has_endgame_data and "endgame" in tailored.get("daily_drill", "").lower():
        tailored["daily_drill"] = (
            "Deepen theory on your strongest opening line from Opening matchups, "
            "then replay one middlegame turning point from the batch."
        )

    return tailored


def rating_band_coaching(
    player_rating: Optional[int],
    *,
    worst_phase: Optional[str] = None,
    best_phase: Optional[str] = None,
    recurring_weaknesses: Optional[List[dict]] = None,
    repertoire_gaps: Optional[List[dict]] = None,
    endgame_insights: Optional[List[dict]] = None,
) -> Optional[Dict[str, Any]]:
    """Return band label + focused drill advice for the batch player's rating."""
    if player_rating is None:
        return None
    try:
        rating = int(player_rating)
    except (TypeError, ValueError):
        return None

    if rating < 1000:
        base = {
            "band": "beginner",
            "label": "Under 1000",
            "focus": "Avoid hanging pieces and one-move threats before opening theory.",
            "daily_drill": "15 minutes of mate-in-1 / mate-in-2 puzzles on Lichess.",
        }
    elif rating < 1400:
        base = {
            "band": "developing",
            "label": "1000–1399",
            "focus": "Convert opening development into simple tactics — forks, pins, and loose pieces.",
            "daily_drill": "20 tactical puzzles emphasizing hanging piece and fork themes.",
        }
    elif rating < 1800:
        base = {
            "band": "intermediate",
            "label": "1400–1799",
            "focus": "Calculate forcing lines in the middlegame and tighten technique in your weakest phase.",
            "daily_drill": "15 puzzles + replay one critical moment from your latest batch.",
        }
    elif rating < 2200:
        base = {
            "band": "advanced",
            "label": "1800–2199",
            "focus": "Reduce conversion errors — punish imprecise play in your weakest phase and shore up repertoire gaps.",
            "daily_drill": "Review batch critical moments, then drill the pattern named in Top priorities.",
        }
    else:
        base = {
            "band": "expert",
            "label": "2200+",
            "focus": "Fine-tune decision quality under time pressure and deepen narrow repertoire lines.",
            "daily_drill": "Annotate one batch blunder deeply; compare engine lines at depth 20+.",
        }

    return _tailor_band_advice(
        base,
        worst_phase=worst_phase,
        best_phase=best_phase,
        recurring_weaknesses=recurring_weaknesses,
        repertoire_gaps=repertoire_gaps,
        endgame_insights=endgame_insights,
    )
