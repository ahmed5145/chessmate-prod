"""
Batch Aggregator: Cross-game pattern detection and synthesis (PRD section 11).
Pure Python — no Stockfish, no AI. Takes per-game results and produces batch_summary.
"""

import logging
import re
import statistics
from collections import Counter
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BatchAggregationError(Exception):
    """Raised when batch aggregation fails due to insufficient or invalid data."""

    pass


def aggregate_batch(per_game_results: List[Dict[str, Any]], pgn_list: Optional[List[str]] = None) -> Dict[str, Any]:
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
        missing_fields = [f for f in required_fields if f not in result or result[f] is None]
        if missing_fields:
            logger.warning(f"Filtering out malformed per-game result at index {idx}: missing fields {missing_fields}")
            continue

        # Skip games marked as analysis failures
        if result.get("analysis_failed", False):
            logger.warning(f"Filtering out failed analysis for game {result.get('game_id', 'unknown')}")
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

    # Compute overall_accuracy: weighted average of phase scores across all games
    overall_accuracy = _compute_overall_accuracy(per_game_results)

    # Phase performance: score, trend, primary_openings/worst_aspect
    phase_performance = _compute_phase_performance(per_game_results)

    # Recurring weaknesses: patterns in ≥30% of games
    recurring_weaknesses = _find_recurring_weaknesses(per_game_results)

    # Strength patterns: ≥60% of games
    strength_patterns = _find_strength_patterns(per_game_results)

    # Most common blunder type
    most_common_blunder_type = _find_most_common_blunder_type(per_game_results)

    # Best and worst phases with solid-phases sentinel
    worst_phase, best_phase, all_phases_solid = _find_phase_extremes(phase_performance)

    result = {
        "games_analyzed": games_analyzed,
        "player_rating": player_rating,
        "date_range": date_range,
        "overall_accuracy": overall_accuracy,
        "win_loss_draw": win_loss_draw,
        "phase_performance": phase_performance,
        "recurring_weaknesses": recurring_weaknesses,
        "strength_patterns": strength_patterns,
        "most_common_blunder_type": most_common_blunder_type,
        "worst_phase": worst_phase,
        "best_phase": best_phase,
        "all_phases_solid": all_phases_solid,
    }

    return result


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


def _count_results(per_game_results: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count wins, losses, draws from game results."""
    wins = 0
    losses = 0
    draws = 0

    for result in per_game_results:
        result_str = result.get("result", "").strip()
        if result_str == "1-0":
            wins += 1
        elif result_str == "0-1":
            losses += 1
        elif result_str == "1/2-1/2":
            draws += 1

    return {
        "wins": wins,
        "losses": losses,
        "draws": draws,
    }


def _compute_overall_accuracy(per_game_results: List[Dict[str, Any]]) -> float:
    """Weighted average of phase scores."""
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
                most_common_theme = Counter(tactical_themes_for_phase).most_common(1)[0][0]
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

    for result in per_game_results:
        game_id = result.get("game_id", "unknown")
        critical_moments = result.get("critical_moments", [])

        themes_in_game = set()
        for moment in critical_moments:
            theme = moment.get("tactical_theme")
            if theme:
                themes_in_game.add(theme)
                swing = moment.get("eval_swing", 0.0)
                if theme not in theme_swings:
                    theme_swings[theme] = []
                theme_swings[theme].append(swing)

        for theme in themes_in_game:
            theme_game_counts[theme] = theme_game_counts.get(theme, 0) + 1
            if theme not in theme_games:
                theme_games[theme] = []
            theme_games[theme].append(game_id)

    # Filter by threshold (≥30%) and build result
    recurring = []
    for theme, game_count in sorted(theme_game_counts.items(), key=lambda x: x[1], reverse=True):
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
                }
            )

    return recurring


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
            games_phrase = opening_games_with_data if opening_games_with_data > 0 else len(per_game_results)
            detail = (
                f"Opening phase averaged {avg_opening_pct}% accuracy across {games_phrase} games "
                f"({opening_move_total} opening moves analyzed)."
            )
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


def _find_most_common_blunder_type(per_game_results: List[Dict[str, Any]]) -> str:
    """Find most common blunder classification."""
    blunder_types = []

    for result in per_game_results:
        move_quality = result.get("move_quality", {})
        blunders_count = move_quality.get("blunder", 0)
        if blunders_count > 0:
            blunder_types.append("tactical_oversight")

    if blunder_types:
        # All blunders mapped to tactical_oversight for now
        return "tactical_oversight"

    return "Unknown"


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
