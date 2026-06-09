"""
Rating-band study guidance (text only — no AI).
Tailored using batch_summary signals when available.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# Conservative static miss-rate ranges (percent) per band + moment theme.
# Labeled "ChessMate benchmark" until aggregated product data exists.
_MOMENT_MISS_RATES: Dict[str, Dict[str, Tuple[int, int]]] = {
    "under_1000": {
        "tactical_oversight": (50, 62),
        "missed_tactic": (55, 68),
        "opening_inaccuracy": (45, 58),
    },
    "1000_1199": {
        "tactical_oversight": (42, 52),
        "missed_tactic": (48, 58),
        "opening_inaccuracy": (38, 48),
    },
    "1200_1399": {
        "tactical_oversight": (35, 45),
        "missed_tactic": (40, 50),
        "opening_inaccuracy": (32, 42),
    },
    "1400_1599": {
        "tactical_oversight": (28, 38),
        "missed_tactic": (32, 42),
        "opening_inaccuracy": (24, 34),
    },
    "1600_1799": {
        "tactical_oversight": (22, 32),
        "missed_tactic": (26, 36),
        "opening_inaccuracy": (18, 28),
    },
    "1800_1999": {
        "tactical_oversight": (16, 26),
        "missed_tactic": (20, 30),
        "opening_inaccuracy": (14, 22),
    },
    "2000_plus": {
        "tactical_oversight": (12, 20),
        "missed_tactic": (15, 24),
        "opening_inaccuracy": (10, 18),
    },
}

_MOMENT_THEME_LABELS = {
    "tactical_oversight": "this tactic",
    "missed_tactic": "a winning tactic",
    "opening_inaccuracy": "this opening inaccuracy",
    "positional_slip": "this positional slip",
}


def resolve_rating_band(player_rating: Optional[int]) -> Optional[Dict[str, Any]]:
    """Map a player rating to a band key, label, and rounded anchor for copy."""
    if player_rating is None:
        return None
    try:
        rating = int(player_rating)
    except (TypeError, ValueError):
        return None
    if rating <= 0:
        return None

    if rating < 1000:
        return {"key": "under_1000", "label": "under 1000", "near_rating": 900}
    if rating < 1200:
        return {"key": "1000_1199", "label": "1000-1199", "near_rating": 1100}
    if rating < 1400:
        return {"key": "1200_1399", "label": "1200-1399", "near_rating": 1300}
    if rating < 1600:
        return {"key": "1400_1599", "label": "1400-1599", "near_rating": 1500}
    if rating < 1800:
        return {"key": "1600_1799", "label": "1600-1799", "near_rating": 1700}
    if rating < 2000:
        return {"key": "1800_1999", "label": "1800-1999", "near_rating": 1900}
    return {"key": "2000_plus", "label": "2000+", "near_rating": 2100}


def normalize_moment_benchmark_theme(moment_type: Optional[str]) -> Optional[str]:
    """Map single-game / batch moment labels to benchmark theme keys."""
    if not moment_type:
        return None
    normalized = str(moment_type).lower().replace(" ", "_").strip()
    aliases = {
        "blunder": "tactical_oversight",
        "mistake": "tactical_oversight",
        "missed_win": "missed_tactic",
        "inaccuracy": "opening_inaccuracy",
        "opening_inaccuracy": "opening_inaccuracy",
        "tactical_oversight": "tactical_oversight",
        "missed_tactic": "missed_tactic",
        "positional_slip": "positional_slip",
    }
    return aliases.get(normalized)


def single_game_moment_benchmark(
    player_rating: Optional[int],
    moment_type: Optional[str],
) -> Optional[Dict[str, Any]]:
    """
    Build honest benchmark copy for a critical moment at the player's rating band.
    Returns None when rating or moment theme is unknown.
    """
    band = resolve_rating_band(player_rating)
    theme = normalize_moment_benchmark_theme(moment_type)
    if not band or not theme:
        return None

    rates = _MOMENT_MISS_RATES.get(band["key"], {}).get(theme)
    if not rates:
        return None

    low, high = rates
    theme_label = _MOMENT_THEME_LABELS.get(theme, "this mistake")
    copy = (
        f"ChessMate benchmark: players near {band['near_rating']} "
        f"miss {theme_label} about {low}-{high}% of the time in similar positions."
    )
    return {
        "band_label": band["label"],
        "near_rating": band["near_rating"],
        "moment_theme": theme,
        "miss_rate_low": low,
        "miss_rate_high": high,
        "copy": copy,
        "source": "static_benchmark",
    }


def attach_moment_benchmarks(
    moments: Optional[List[Dict[str, Any]]],
    player_rating: Optional[int],
) -> List[Dict[str, Any]]:
    """Attach rating_benchmark payloads to critical moment dicts."""
    if not isinstance(moments, list):
        return []
    enriched: List[Dict[str, Any]] = []
    for moment in moments:
        if not isinstance(moment, dict):
            continue
        item = dict(moment)
        benchmark = single_game_moment_benchmark(
            player_rating,
            moment.get("type") or moment.get("classification"),
        )
        if benchmark:
            item["rating_benchmark"] = benchmark
        enriched.append(item)
    return enriched


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
