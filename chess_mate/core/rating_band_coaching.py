"""
Rating-band study guidance (text only — no AI).
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def rating_band_coaching(player_rating: Optional[int]) -> Optional[Dict[str, Any]]:
    """Return band label + focused drill advice for the batch player's rating."""
    if player_rating is None:
        return None
    try:
        rating = int(player_rating)
    except (TypeError, ValueError):
        return None

    if rating < 1000:
        return {
            "band": "beginner",
            "label": "Under 1000",
            "focus": "Avoid hanging pieces and one-move threats before opening theory.",
            "daily_drill": "15 minutes of mate-in-1 / mate-in-2 puzzles on Lichess.",
        }
    if rating < 1400:
        return {
            "band": "developing",
            "label": "1000–1399",
            "focus": "Convert opening development into simple tactics — forks, pins, and loose pieces.",
            "daily_drill": "20 tactical puzzles emphasizing hanging piece and fork themes.",
        }
    if rating < 1800:
        return {
            "band": "intermediate",
            "label": "1400–1799",
            "focus": "Calculate forcing lines in the middlegame and tighten endgame technique.",
            "daily_drill": "15 puzzles + 10 minutes rook or pawn endgame practice per day.",
        }
    if rating < 2200:
        return {
            "band": "advanced",
            "label": "1800–2199",
            "focus": "Reduce conversion errors — punish imprecise endgames and repeat opening prep gaps.",
            "daily_drill": "Review batch critical moments, then drill the weakest endgame type from your report.",
        }
    return {
        "band": "expert",
        "label": "2200+",
        "focus": "Fine-tune decision quality under time pressure and deepen narrow repertoire lines.",
        "daily_drill": "Annotate one batch blunder deeply; compare engine lines at depth 20+.",
    }
