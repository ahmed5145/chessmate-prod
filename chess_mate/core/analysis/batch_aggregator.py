"""
Batch Aggregator: Cross-game pattern detection and synthesis (PRD section 11).
Pure Python — no Stockfish, no AI. Takes per-game results and produces batch_summary.
"""

import logging
import re
import statistics
from collections import Counter
from typing import Any, Dict, List, Optional

from ..rating_band_coaching import rating_band_coaching
from .batch_metrics import compute_batch_accuracy, compute_batch_acpl
from .moment_insights import ENDGAME_LICHESS_URLS, ENDGAME_STUDY_HINTS

logger = logging.getLogger(__name__)


class BatchAggregationError(Exception):
    """Raised when batch aggregation fails due to insufficient or invalid data."""

    pass


def aggregate_batch(
    per_game_results: List[Dict[str, Any]], pgn_list: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Aggregate per-game Stockfish results into cross-game patterns.

    Args:
        per_game_results: List of per-game result dicts from stockfish_game_result.build_game_result()
        pgn_list: Optional list of PGN strings (for date extraction if needed)

    Returns:
        Dict matching batch_summary schema from PRD section 11

    Raises:
        BatchAggregationError: If fewer than 5 valid results after filtering
    """
    if not per_game_results:
        return {}

    # Defensive validation: filter out malformed results
    required_fields = ["game_id", "phase_breakdown", "move_quality"]
    valid_results = []

    for idx, result in enumerate(per_game_results):
        missing_fields = [
            f for f in required_fields if f not in result or result[f] is None
        ]
        if missing_fields:
            logger.warning(
                f"Filtering out malformed per-game result at index {idx}: missing fields {missing_fields}"
            )
            continue

        # Skip games marked as analysis failures
        if result.get("analysis_failed", False):
            logger.warning(
                f"Filtering out failed analysis for game {result.get('game_id', 'unknown')}"
            )
            continue

        valid_results.append(result)

    # Check we have minimum viable data
    if len(valid_results) < 5:
        raise BatchAggregationError(
            f"Insufficient valid game results for aggregation: {len(valid_results)} valid out of {len(per_game_results)} total. "
            f"Minimum 5 required."
        )

    per_game_results = valid_results

    # Derive player_rating from game ELO ratings
    # For each game, extract the ELO of the player's color, collect non-null values,
    # take median, and round to nearest integer
    player_elos = []
    for game_result in per_game_results:
        player_color = game_result.get("player_color", "white")
        if player_color == "white":
            white_elo = game_result.get("white_elo")
            if white_elo is not None:
                player_elos.append(white_elo)
        else:
            black_elo = game_result.get("black_elo")
            if black_elo is not None:
                player_elos.append(black_elo)

    # Compute median; if no ELO values, set to None
    if player_elos:
        player_rating = round(statistics.median(player_elos))
    else:
        player_rating = None

    # Extract basic counts
    games_analyzed = len(per_game_results)

    # Extract date range from PGN headers if available
    date_range = _extract_date_range(pgn_list)

    # Extract win/loss/draw
    win_loss_draw = _count_results(per_game_results)

    overall_eval_stability = _compute_overall_eval_stability(per_game_results)
    overall_accuracy_pct = compute_batch_accuracy(per_game_results)
    overall_acpl = compute_batch_acpl(per_game_results)

    # Phase performance: score, trend, primary_openings/worst_aspect
    phase_performance = _compute_phase_performance(per_game_results)

    # Recurring weaknesses: patterns in ≥30% of games
    recurring_weaknesses = _find_recurring_weaknesses(per_game_results)

    # Strength patterns: ≥60% of games
    strength_patterns = _find_strength_patterns(per_game_results)

    # Most common blunder type
    most_common_blunder_type = _find_most_common_blunder_type(per_game_results)

    # Opening / endgame insights (specific, engine-derived — not generic tactic labels)
    opening_insights = _compute_opening_insights(per_game_results)
    repertoire_gaps = _compute_repertoire_gaps(opening_insights)
    endgame_insights = _compute_endgame_insights(per_game_results)

    # Best and worst phases with solid-phases sentinel
    worst_phase, best_phase, all_phases_solid = _find_phase_extremes(phase_performance)

    # Drop opening praise when batch-level signals say opening needs work (avoids contradicting rating-band copy).
    if worst_phase == "opening" or repertoire_gaps:
        strength_patterns = [
            pattern
            for pattern in strength_patterns
            if pattern.get("pattern") != "opening_preparation"
        ]

    top_critical_moments = _top_critical_moments(per_game_results, limit=3)
    time_management_summary = _compute_time_management_summary(per_game_results)

    result = {
        "games_analyzed": games_analyzed,
        "player_rating": player_rating,
        "date_range": date_range,
        "overall_eval_stability": overall_eval_stability,
        "overall_accuracy_pct": overall_accuracy_pct,
        "overall_acpl": overall_acpl,
        "overall_accuracy": overall_eval_stability,  # deprecated alias (eval stability 0–1)
        "win_loss_draw": win_loss_draw,
        "phase_performance": phase_performance,
        "recurring_weaknesses": recurring_weaknesses,
        "opening_insights": opening_insights,
        "repertoire_gaps": repertoire_gaps,
        "endgame_insights": endgame_insights,
        "strength_patterns": strength_patterns,
        "most_common_blunder_type": most_common_blunder_type,
        "worst_phase": worst_phase,
        "best_phase": best_phase,
        "all_phases_solid": all_phases_solid,
        "top_critical_moments": top_critical_moments,
        "time_management_summary": time_management_summary,
        "rating_band_coaching": rating_band_coaching(
            player_rating,
            worst_phase=worst_phase,
            best_phase=best_phase,
            recurring_weaknesses=recurring_weaknesses,
            repertoire_gaps=repertoire_gaps,
            endgame_insights=endgame_insights,
        ),
    }

    return result


def _compute_time_management_summary(
    per_game_results: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Batch-level clock pattern when enough games include PGN clock data."""
    if not per_game_results:
        return None

    timed_games = [
        result
        for result in per_game_results
        if isinstance(result.get("time_management"), dict)
        and result["time_management"].get("has_clock_data")
    ]
    if len(timed_games) < max(2, int(len(per_game_results) * 0.3)):
        return None

    avg_per_move_values = [
        float(result["time_management"]["avg_seconds_per_move"])
        for result in timed_games
        if result["time_management"].get("avg_seconds_per_move") is not None
    ]
    rushed_critical_total = sum(
        int(result["time_management"].get("rushed_critical_count") or 0)
        for result in timed_games
    )
    low_endgame_games = sum(
        1
        for result in timed_games
        if result["time_management"].get("pattern") == "low_endgame_time"
    )

    pattern = None
    insight = None
    if rushed_critical_total >= max(2, len(timed_games) // 2):
        pattern = "rushed_critical_moments"
        insight = (
            "You often used very little time right before big eval swings. "
            "Pause on candidate moves when the position is tactically sharp."
        )
    elif low_endgame_games >= max(2, len(timed_games) // 3):
        pattern = "low_endgame_time"
        insight = (
            "Endgame phases show much less time per move than the opening. "
            "Budget clock for conversion and defensive resources in the endgame."
        )
    elif avg_per_move_values:
        batch_avg = sum(avg_per_move_values) / len(avg_per_move_values)
        pattern = "clock_data_available"
        insight = f"Average think time across timed games: {batch_avg:.1f}s per move."

    return {
        "games_with_clock_data": len(timed_games),
        "games_analyzed": len(per_game_results),
        "rushed_critical_total": rushed_critical_total,
        "pattern": pattern,
        "insight": insight,
    }


def _top_critical_moments(
    per_game_results: List[Dict[str, Any]], limit: int = 3
) -> List[Dict[str, Any]]:
    """Batch-wide worst moments by eval swing (for FEN boards and quick review)."""
    ranked: List[Dict[str, Any]] = []
    for game_result in per_game_results:
        game_id = game_result.get("game_id")
        saved_game_id = game_result.get("saved_game_id")
        player_color = game_result.get("player_color")
        for moment in game_result.get("critical_moments") or []:
            if not isinstance(moment, dict):
                continue
            if (
                player_color
                and moment.get("mover")
                and moment.get("mover") != player_color
            ):
                continue
            ranked.append(
                {
                    **moment,
                    "game_id": game_id,
                    "saved_game_id": saved_game_id,
                    "player_color": player_color,
                }
            )
    ranked.sort(key=lambda item: float(item.get("eval_swing") or 0), reverse=True)
    return ranked[:limit]


def _extract_date_range(pgn_list: Optional[List[str]]) -> str:
    """Extract date range from PGN Date headers."""
    if not pgn_list:
        return "Unknown"

    dates = []
    for pgn in pgn_list:
        try:
            match = re.search(r'\[Date\s+"(\d{4})\.(\d{2})\.(\d{2})"\]', pgn)
            if match:
                dates.append(f"{match.group(1)}-{match.group(2)}-{match.group(3)}")
        except Exception:
            continue

    if not dates:
        return "Unknown"

    dates_sorted = sorted(set(dates))
    if len(dates_sorted) == 1:
        return dates_sorted[0]
    return f"{dates_sorted[0]} to {dates_sorted[-1]}"


def _player_outcome(result: Dict[str, Any]) -> str:
    """win | loss | draw from the analyzed player's perspective."""
    raw = (result.get("result") or "").strip()
    color = result.get("player_color", "white")
    if raw in ("1/2-1/2", "*"):
        return "draw"
    if raw == "1-0":
        return "win" if color == "white" else "loss"
    if raw == "0-1":
        return "win" if color == "black" else "loss"
    return "unknown"


def _phase_score(phase_data: Dict[str, Any]) -> float:
    avg_eval_drop = float(phase_data.get("avg_eval_drop", 0.0) or 0.0)
    return max(0.0, min(1.0, 1.0 - avg_eval_drop))


def _count_results(per_game_results: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count wins, losses, draws from the analyzed player's perspective (M3)."""
    wins = 0
    losses = 0
    draws = 0

    for result in per_game_results:
        outcome = _player_outcome(result)
        if outcome == "win":
            wins += 1
        elif outcome == "loss":
            losses += 1
        elif outcome == "draw":
            draws += 1

    return {
        "wins": wins,
        "losses": losses,
        "draws": draws,
    }


def _compute_overall_eval_stability(per_game_results: List[Dict[str, Any]]) -> float:
    """Weighted average of phase eval stability scores (1 - avg_eval_drop)."""
    if not per_game_results:
        return 0.0

    total_weight = 0.0
    weighted_sum = 0.0

    for result in per_game_results:
        phase_breakdown = result.get("phase_breakdown", {})
        for phase_key in ["opening", "middlegame", "endgame"]:
            phase = phase_breakdown.get(phase_key, {})
            moves_count = phase.get("moves", 0)
            if moves_count > 0:
                # Compute phase score as inverse of avg_eval_drop
                avg_eval_drop = phase.get("avg_eval_drop", 0.0)
                # Score: 1.0 - normalized_drop (capped at 0 and 1)
                phase_score = max(0.0, min(1.0, 1.0 - avg_eval_drop))
                weighted_sum += phase_score * moves_count
                total_weight += moves_count

    if total_weight == 0:
        return 0.0

    overall = weighted_sum / total_weight
    return round(overall, 2)


def _compute_phase_performance(
    per_game_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compute score, trend, and worst_aspect for each phase.
    worst_aspect uses enum: tactical_oversight | time_pressure | positional | technique
    Derived from most common tactical_theme in critical moments.
    """
    phases = {}

    for phase_name in ["opening", "middlegame", "endgame"]:
        phase_scores = []
        phase_accuracy_scores = []
        phase_openings = []
        tactical_themes_for_phase = []

        for result in per_game_results:
            phase_breakdown = result.get("phase_breakdown", {})
            phase_data = phase_breakdown.get(phase_name, {})
            moves_count = phase_data.get("moves", 0)

            if moves_count > 0:
                avg_eval_drop = phase_data.get("avg_eval_drop", 0.0)
                phase_score = max(0.0, min(1.0, 1.0 - avg_eval_drop))
                phase_scores.append(phase_score)
                phase_acc = phase_data.get("accuracy")
                if phase_acc is not None:
                    phase_accuracy_scores.append(float(phase_acc))

            # Collect opening names for opening phase
            if phase_name == "opening":
                opening = result.get("opening_name", "Unknown")
                if opening and opening != "Unknown":
                    phase_openings.append(opening)

            # Collect tactical themes from critical moments in this phase
            critical_moments = result.get("critical_moments", [])
            for moment in critical_moments:
                if moment.get("phase") == phase_name:
                    theme = moment.get("tactical_theme")
                    if theme:
                        tactical_themes_for_phase.append(theme)

        # Compute score for this phase
        if phase_scores:
            avg_score = sum(phase_scores) / len(phase_scores)
            # Compute standard deviation for trend
            if len(phase_scores) > 1:
                std_dev = statistics.stdev(phase_scores)
            else:
                std_dev = 0.0

            # Determine trend
            if avg_score >= 0.75:
                trend = "strong"
            elif avg_score < 0.5:
                trend = "weak"
            elif std_dev > 0.2:
                trend = "inconsistent"
            else:
                trend = "average"
        else:
            # Sentinel for missing phase data so downstream coaching can stay schema-safe.
            avg_score = 0.5
            trend = "no_data"

        phase_info = {
            "score": round(avg_score, 2) if avg_score is not None else None,
            "trend": trend,
        }
        if phase_accuracy_scores:
            phase_info["accuracy_pct"] = round(
                sum(phase_accuracy_scores) / len(phase_accuracy_scores),
                1,
            )

        # Opening always includes primary_openings key
        if phase_name == "opening":
            if phase_openings:
                opening_counts = Counter(phase_openings)
                top_openings = [name for name, _ in opening_counts.most_common(3)]
                phase_info["primary_openings"] = top_openings
            else:
                phase_info["primary_openings"] = ["Unknown"]

        # Middlegame/endgame always include worst_aspect key from enum
        if phase_name in ["middlegame", "endgame"]:
            if tactical_themes_for_phase:
                most_common_theme = Counter(tactical_themes_for_phase).most_common(1)[
                    0
                ][0]
                phase_info["worst_aspect"] = _map_theme_to_aspect(most_common_theme)
            else:
                phase_info["worst_aspect"] = "technique"

        phases[phase_name] = phase_info

    return phases


def _map_theme_to_aspect(tactical_theme: str) -> str:
    """Map tactical_theme to worst_aspect enum."""
    enum_values = {
        "fork": "tactical_oversight",
        "pin": "tactical_oversight",
        "skewer": "tactical_oversight",
        "hanging_piece": "tactical_oversight",
        "missed_tactic": "tactical_oversight",
    }
    return enum_values.get(tactical_theme, "tactical_oversight")


def _find_recurring_weaknesses(
    per_game_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Find patterns (tactical themes) appearing in ≥30% of games.
    """
    if not per_game_results:
        return []

    threshold = 0.3 * len(per_game_results)

    # Count games containing each tactical_theme
    theme_game_counts = {}  # theme -> count of games with this theme
    theme_swings = {}  # theme -> list of eval_swings
    theme_games = {}  # theme -> list of game_ids

    generic_themes = {"missed_tactic", "tactical_oversight"}
    min_swing = 0.5

    for result in per_game_results:
        game_id = result.get("game_id", "unknown")
        critical_moments = result.get("critical_moments", [])

        themes_in_game = set()
        for moment in critical_moments:
            if moment.get("type") not in ("blunder", "mistake"):
                continue
            swing = float(moment.get("eval_swing", 0.0) or 0.0)
            if swing < min_swing:
                continue
            theme = moment.get("tactical_theme")
            if theme:
                themes_in_game.add(theme)
                if theme not in theme_swings:
                    theme_swings[theme] = []
                theme_swings[theme].append(swing)

        if themes_in_game - generic_themes:
            themes_in_game -= generic_themes

        for theme in themes_in_game:
            theme_game_counts[theme] = theme_game_counts.get(theme, 0) + 1
            if theme not in theme_games:
                theme_games[theme] = []
            theme_games[theme].append(game_id)

    # Filter by threshold (≥30%) and build result (cap tactical themes — opening/endgame insights are separate)
    recurring = []
    for theme, game_count in sorted(
        theme_game_counts.items(), key=lambda x: x[1], reverse=True
    ):
        if game_count >= threshold:
            # Compute average eval swing
            swings = theme_swings.get(theme, [])
            avg_swing = sum(swings) / len(swings) if swings else 0.0

            # Determine impact
            if avg_swing >= 1.5:
                impact = "critical"
            elif avg_swing >= 0.5:
                impact = "high"
            else:
                impact = "medium"

            # Get up to 3 example game IDs
            example_ids = theme_games.get(theme, [])[:3]

            frequency_str = f"{game_count}/{len(per_game_results)} games"

            recurring.append(
                {
                    "pattern": theme,
                    "frequency": frequency_str,
                    "avg_eval_swing": round(avg_swing, 2),
                    "impact": impact,
                    "example_game_ids": example_ids,
                    "detail": f"Tactical theme '{theme.replace('_', ' ')}' appeared in critical moments.",
                }
            )

    return recurring[:2]


def _find_strength_patterns(
    per_game_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Find patterns where player performed well in ≥60% of games.
    This is currently a placeholder; in full implementation would track
    successful opening moves, positional ideas, etc.
    """
    if not per_game_results:
        return []

    # Count games with strong opening phase performance and collect opening stats
    strong_opening_count = 0
    opening_scores: List[float] = []
    opening_games_with_data = 0
    opening_move_total = 0

    for result in per_game_results:
        opening_phase = result.get("phase_breakdown", {}).get("opening", {})
        opening_moves = int(opening_phase.get("moves", 0) or 0)
        if opening_moves > 0:
            opening_games_with_data += 1
            opening_move_total += opening_moves
            avg_eval_drop = float(opening_phase.get("avg_eval_drop", 0.0) or 0.0)
            opening_score = max(0.0, min(1.0, 1.0 - avg_eval_drop))
            opening_scores.append(opening_score)
            if opening_score >= 0.75:
                strong_opening_count += 1

    threshold = 0.6 * len(per_game_results)
    patterns = []

    if strong_opening_count >= threshold:
        if opening_scores:
            avg_opening_score = sum(opening_scores) / len(opening_scores)
            avg_opening_pct = round(avg_opening_score * 100)
            games_phrase = (
                opening_games_with_data
                if opening_games_with_data > 0
                else len(per_game_results)
            )
            detail = f"Opening phase averaged {avg_opening_pct}% accuracy across {games_phrase} games."
        else:
            detail = "Opening phase performance was consistently strong across the analyzed games."

        patterns.append(
            {
                "pattern": "opening_preparation",
                "frequency": f"{strong_opening_count}/{len(per_game_results)} games",
                "detail": detail,
            }
        )

    return patterns


def _find_most_common_blunder_type(
    per_game_results: List[Dict[str, Any]]
) -> Optional[str]:
    """Most frequent tactical theme in critical blunders/mistakes, or None if no signal."""
    theme_counts: Counter = Counter()
    for result in per_game_results:
        for moment in result.get("critical_moments", []):
            if moment.get("type") not in ("blunder", "mistake"):
                continue
            theme = (moment.get("tactical_theme") or "").strip()
            if not theme or theme == "missed_tactic":
                theme_counts["tactical errors"] += 1
            else:
                theme_counts[theme.replace("_", " ")] += 1

    if theme_counts:
        return theme_counts.most_common(1)[0][0]

    blunder_games = sum(
        1
        for result in per_game_results
        if int(result.get("move_quality", {}).get("blunder", 0) or 0) > 0
    )
    if blunder_games:
        return "tactical errors"

    mistake_games = sum(
        1
        for result in per_game_results
        if int(result.get("move_quality", {}).get("mistake", 0) or 0) > 0
    )
    if mistake_games:
        return "inaccurate play"

    return None


def _opening_group_key(result: Dict[str, Any]) -> str:
    """Group ECO variants (e.g. Queen's Pawn + London System) for batch-level stats."""
    eco = (result.get("eco_code") or "").strip()
    if eco:
        return f"eco:{eco}"
    name = (result.get("opening_name") or "").strip()
    if ":" in name:
        return name.split(":", 1)[0].strip()
    return name


def _opening_display_name(games: List[Dict[str, Any]]) -> str:
    from ..eco_codes import get_opening_name
    from ..opening_name_utils import compact_opening_name

    names = [
        compact_opening_name(g.get("opening_name"))
        for g in games
        if g.get("opening_name")
    ]
    known_names = [
        n
        for n in names
        if n and str(n).strip().lower() not in ("unknown", "unknown opening", "?")
    ]
    if known_names:
        with_variation = [n for n in known_names if ":" in n]
        if with_variation:
            return max(with_variation, key=len)
        return max(known_names, key=len)

    eco_codes = sorted({g.get("eco_code") for g in games if g.get("eco_code")})
    if len(eco_codes) == 1:
        specific = get_opening_name(eco_codes[0])
        if specific and specific != "Unknown Opening":
            return specific

    return "Unknown"


def _compute_opening_insights(
    per_game_results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Per-opening performance so coaching can name lines the player struggles in.
    """
    by_opening: Dict[str, List[Dict[str, Any]]] = {}
    for result in per_game_results:
        name = (result.get("opening_name") or "").strip()
        eco = (result.get("eco_code") or "").strip()
        if (not name or name.lower() in ("unknown", "unknown opening")) and not eco:
            continue
        group_key = _opening_group_key(result)
        by_opening.setdefault(group_key, []).append(result)

    insights: List[Dict[str, Any]] = []
    for _group_key, games in by_opening.items():
        opening_name = _opening_display_name(games)
        outcomes = [_player_outcome(g) for g in games]
        wins = outcomes.count("win")
        losses = outcomes.count("loss")
        draws = outcomes.count("draw")
        opening_scores = [
            _phase_score(g.get("phase_breakdown", {}).get("opening", {}))
            for g in games
            if int(g.get("phase_breakdown", {}).get("opening", {}).get("moves", 0) or 0)
            > 0
        ]
        avg_opening_score = (
            round(sum(opening_scores) / len(opening_scores), 2)
            if opening_scores
            else None
        )
        colors = [g.get("player_color", "white") for g in games]
        player_color = (
            "black" if colors.count("black") > colors.count("white") else "white"
        )
        eco_codes = sorted({g.get("eco_code") for g in games if g.get("eco_code")})

        status = "neutral"
        recommendation = None
        if losses >= 2 or (len(games) >= 2 and losses > wins):
            status = "struggling"
            recommendation = (
                f"You lost {losses} of {len(games)} games as {opening_name}. "
                f"Review mainline theory and typical plans for this opening — "
                f"consider a simpler repertoire alternative if scores stay low."
            )
        elif wins >= 2 and losses == 0:
            status = "strong"
            recommendation = (
                f"{opening_name} is working well ({wins}W-{losses}L in this batch). "
                f"Deepen theory on the lines you already play rather than switching openings."
            )
        elif avg_opening_score is not None and avg_opening_score < 0.65:
            status = "needs_work"
            recommendation = (
                f"Opening phase accuracy in {opening_name} averaged {int(avg_opening_score * 100)}%. "
                f"Study model games and common middlegame plans from this opening."
            )
        else:
            eco_label = (
                f" ({eco_codes[0]})" if len(eco_codes) == 1 and eco_codes else ""
            )
            score_text = ""
            if avg_opening_score is not None:
                score_text = f" Opening phase: {int(avg_opening_score * 100)}%."
            recommendation = (
                f"As {player_color} in {opening_name}{eco_label}: {wins}W-{losses}L-{draws}D "
                f"across {len(games)} game(s).{score_text}"
            )

        insights.append(
            {
                "opening_name": opening_name,
                "eco_code": eco_codes[0] if len(eco_codes) == 1 else None,
                "eco_codes": eco_codes[:3],
                "games": len(games),
                "record": f"{wins}W-{losses}L-{draws}D",
                "avg_opening_score": avg_opening_score,
                "status": status,
                "player_color": player_color,
                "recommendation": recommendation,
                "example_game_ids": [
                    g.get("game_id") for g in games[:3] if g.get("game_id")
                ],
            }
        )

    insights.sort(
        key=lambda x: (
            (
                0
                if x["status"] == "struggling"
                else 1 if x["status"] == "needs_work" else 2
            ),
            -x["games"],
        )
    )
    return insights


def _compute_repertoire_gaps(
    opening_insights: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Openings where the player is losing or underperforming — repertoire review targets."""
    gaps = []
    for item in opening_insights:
        if item.get("status") not in ("struggling", "needs_work"):
            continue
        opening_name = (item.get("opening_name") or "").strip()
        if not opening_name or opening_name.lower() in ("unknown", "unknown opening"):
            continue
        color = item.get("player_color", "white")
        gaps.append(
            {
                "opening_name": item.get("opening_name"),
                "eco_code": item.get("eco_code"),
                "eco_codes": item.get("eco_codes") or [],
                "record": item.get("record"),
                "player_color": color,
                "status": item.get("status"),
                "avg_opening_score": item.get("avg_opening_score"),
                "recommendation": item.get("recommendation"),
                "summary": (
                    f"As {color}, {item.get('opening_name')} ({item.get('record')}) "
                    f"is a repertoire gap in this batch."
                ),
            }
        )
    return gaps[:3]


def _compute_endgame_insights(
    per_game_results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Endgame types where the player lost evaluation (from FEN at critical moments).
    """
    type_games: Dict[str, set] = {}
    type_swings: Dict[str, List[float]] = {}
    type_examples: Dict[str, List[Dict[str, Any]]] = {}

    for result in per_game_results:
        game_id = result.get("game_id", "unknown")
        endgame_phase = result.get("phase_breakdown", {}).get("endgame", {})
        if int(endgame_phase.get("moves", 0) or 0) < 4:
            continue

        for moment in result.get("critical_moments", []):
            if moment.get("phase") != "endgame":
                continue
            if moment.get("type") not in ("blunder", "mistake"):
                continue
            eg_type = moment.get("endgame_material") or "general_endgame"
            type_games.setdefault(eg_type, set()).add(game_id)
            type_swings.setdefault(eg_type, []).append(
                float(moment.get("eval_swing", 0.0) or 0.0)
            )
            examples = type_examples.setdefault(eg_type, [])
            if len(examples) < 3:
                examples.append(
                    {
                        "game_id": game_id,
                        "move_number": moment.get("move_number"),
                        "played_move": moment.get("played_move"),
                        "best_move": moment.get("best_move"),
                    }
                )

    total_games = len(per_game_results)
    has_specific_endgame = any(eg_type != "general_endgame" for eg_type in type_games)
    insights: List[Dict[str, Any]] = []
    for eg_type, game_ids in sorted(
        type_games.items(), key=lambda kv: len(kv[1]), reverse=True
    ):
        if eg_type == "general_endgame" and has_specific_endgame:
            continue
        count = len(game_ids)
        if count < 2 and total_games >= 5:
            continue
        swings = type_swings.get(eg_type, [])
        avg_swing = round(sum(swings) / len(swings), 2) if swings else 0.0
        label = eg_type.replace("_", " ")
        insights.append(
            {
                "endgame_type": eg_type,
                "label": label,
                "frequency": f"{count}/{total_games} games",
                "avg_eval_swing": avg_swing,
                "study_focus": ENDGAME_STUDY_HINTS.get(
                    eg_type, ENDGAME_STUDY_HINTS["general_endgame"]
                ),
                "study_url": ENDGAME_LICHESS_URLS.get(
                    eg_type, ENDGAME_LICHESS_URLS["general_endgame"]
                ),
                "example_moments": type_examples.get(eg_type, []),
            }
        )

    return insights[:4]


def _find_phase_extremes(phase_performance: Dict[str, Any]) -> tuple:
    """Find worst and best phases by score and whether all phases are solid."""
    phases_with_scores = [
        (phase_name, data.get("score"))
        for phase_name, data in phase_performance.items()
        if data.get("score") is not None
    ]

    if not phases_with_scores:
        return "Unknown", "Unknown", False

    worst_phase = min(phases_with_scores, key=lambda x: x[1])[0]
    best_phase = max(phases_with_scores, key=lambda x: x[1])[0]
    lowest_score = min(score for _, score in phases_with_scores)
    all_phases_solid = lowest_score >= 0.65

    return worst_phase, best_phase, all_phases_solid
