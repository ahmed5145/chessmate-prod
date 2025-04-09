"""
Metrics calculator for chess games.
Handles calculation of various game metrics and statistics.
"""

import logging
import math
import statistics
from typing import Any, Dict, List, Optional, TypedDict, Union, cast
import numpy as np
from collections import Counter

from ..error_handling import ValidationError, MetricsError

# Configure logging
logger = logging.getLogger(__name__)


class TacticalPosition(TypedDict):
    move: Dict[str, Any]
    features: List[str]
    evaluation: float


class MetricsCalculator:
    """Enhanced metrics calculator with proper validation and aggregation."""

    @staticmethod
    def _get_default_time_metrics() -> Dict[str, Any]:
        """Return default time management metrics."""
        return {
            "time_usage": 0.0,
            "time_consistency": 0.0,
            "time_pressure": 0.0,
            "critical_time_usage": 0.0,
        }

    @staticmethod
    def calculate_game_metrics(moves: List[Dict[str, Any]], time_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate comprehensive game metrics.
        
        Args:
            moves: List of analyzed moves with their evaluations
            time_data: List of time data for each move
            
        Returns:
            Dictionary containing all calculated metrics with consistent structure
        """
        try:
            # Check if we have any moves to analyze
            if not moves:
                return MetricsCalculator._get_default_metrics()
                
            # Identify the player (white or black)
            is_white = moves[0].get("is_white", True)
            
            # Calculate move quality metrics
            move_quality = MetricsCalculator._calculate_move_quality(moves)
            
            # Calculate time management metrics
            time_management = MetricsCalculator._calculate_time_management(time_data)
            
            # Calculate consistency metrics
            consistency = MetricsCalculator._calculate_consistency(moves)
            
            # Detect phase transitions
            phases = MetricsCalculator._detect_phase_transitions(moves)
            opening_end = phases.get("opening", 0)
            middlegame_end = phases.get("middlegame", len(moves))
            
            # Split moves by game phase
            opening_moves = moves[:opening_end] if opening_end > 0 else []
            middlegame_moves = moves[opening_end:middlegame_end] if middlegame_end > opening_end else []
            endgame_moves = moves[middlegame_end:] if middlegame_end < len(moves) else []
            
            # Calculate phase-specific metrics
            opening_metrics = MetricsCalculator._calculate_phase_metrics(opening_moves, is_white)
            middlegame_metrics = MetricsCalculator._calculate_phase_metrics(middlegame_moves, is_white)
            endgame_metrics = MetricsCalculator._calculate_phase_metrics(endgame_moves, is_white)
            
            # Compile phase metrics
            phase_metrics = {
                "opening": opening_metrics,
                "middlegame": middlegame_metrics,
                "endgame": endgame_metrics
            }
            
            # Calculate tactical metrics
            tactical_metrics = MetricsCalculator._calculate_tactical_metrics(moves, is_white)
            
            # Calculate advantage metrics
            advantage_metrics = MetricsCalculator._calculate_advantage_metrics(moves, is_white)
            
            # Calculate resourcefulness metrics
            resourcefulness_metrics = MetricsCalculator._calculate_resourcefulness_metrics(moves, is_white)
            
            # Calculate overall metrics
            overall_metrics = MetricsCalculator._calculate_overall_metrics(moves, is_white)
            
            # Compile all metrics with consistent structure
            metrics = {
                "overall": overall_metrics,
                "move_quality": move_quality,
                "time_management": time_management,
                "consistency": consistency,
                "phases": phase_metrics,
                "tactics": tactical_metrics,
                "advantage": advantage_metrics,
                "resourcefulness": resourcefulness_metrics,
                "metadata": {
                    "is_white": is_white,
                    "total_moves": len(moves),
                    "opening_length": opening_end,
                    "middlegame_length": middlegame_end - opening_end,
                    "endgame_length": len(moves) - middlegame_end
                }
            }
            
            # Validate and normalize metrics
            validated_metrics = MetricsCalculator._validate_metrics(metrics)
            
            # Ensure all required sections are present and properly typed
            required_sections = [
                "overall", "move_quality", "time_management", "consistency",
                "phases", "tactics", "advantage", "resourcefulness"
            ]
            
            for section in required_sections:
                if section not in validated_metrics:
                    logger.warning(f"Missing required metrics section: {section}")
                    validated_metrics[section] = MetricsCalculator._get_default_metrics().get(section, {})
            
                # Ensure all numeric values are floats
                if isinstance(validated_metrics[section], dict):
                    for key, value in validated_metrics[section].items():
                        if isinstance(value, (int, float)):
                            validated_metrics[section][key] = float(value)
            
            return validated_metrics
            
        except Exception as e:
            logger.error(f"Error calculating game metrics: {str(e)}")
            # Return default metrics with error information
            default_metrics = MetricsCalculator._get_default_metrics()
            default_metrics["error"] = str(e)
            return default_metrics

    @staticmethod
    def _detect_phase_transitions(moves: List[Dict[str, Any]]) -> Dict[str, int]:
        """Enhanced phase detection using multiple indicators."""
        try:
            total_moves = len(moves)
            if total_moves == 0:
                return {"opening": 0, "middlegame": 0}

            # Initialize phase transition points
            opening_end = min(10, total_moves)  # Default opening length
            middlegame_start = opening_end
            endgame_start = total_moves * 2 // 3

            # Track material count
            material_count: float = 32.0  # Starting position as float
            for i, move in enumerate(moves):
                # Update material count if available
                if "material_count" in move:
                    material_count = float(str(move["material_count"]))

                # Detect opening end based on multiple factors
                if i < total_moves // 3:
                    if (
                        material_count < 28.0  # Significant material exchange
                        or bool(move.get("is_tactical", False))  # Tactical play started
                        or i >= 10
                    ):  # Hard limit on opening
                        opening_end = i
                        middlegame_start = i
                        break

                # Detect endgame start
                if i > total_moves // 2:
                    if material_count < 20.0:  # Clear endgame material situation
                        endgame_start = i
                        break

            return {"opening": opening_end, "middlegame": endgame_start}
        except Exception as e:
            logger.error(f"Error detecting phase transitions: {str(e)}")
            # Fallback to simple division
            third = total_moves // 3
            return {"opening": third, "middlegame": third * 2}

    @staticmethod
    def _validate_evaluation(eval_value: float, move_number: int, phase: str) -> float:
        """Validate evaluation values with context awareness."""
        try:
            # Check for suspicious values
            if abs(eval_value) > 2000:  # Unrealistic evaluation
                return 0.0

            # Validate based on game phase
            if phase == "opening" and abs(eval_value) > 300:
                return math.copysign(300, eval_value)

            if phase == "endgame" and abs(eval_value) > 1000:
                return math.copysign(1000, eval_value)

            return float(eval_value)
        except Exception:
            return 0.0

    @staticmethod
    def _validate_time_metrics(time_spent: List[float], total_time: float, increment: float = 0) -> Dict[str, Any]:
        """
        Validate and normalize time management metrics with enhanced pressure detection.

        Args:
            time_spent: List of time spent on each move in seconds
            total_time: Total time allocated for the game in seconds
            increment: Time increment per move in seconds

        Returns:
            Dictionary containing validated time metrics
        """
        if not time_spent:
            return {
                "average_time": 0.0,
                "time_pressure_moves": 0,
                "time_pressure_percentage": 0.0,
                "time_variance": 0.0,
                "time_management_score": 0.0,
                "normalized_times": [],
                "remaining_time": 0.0,
            }

        # Validate input parameters
        total_time = max(1.0, float(total_time))  # Ensure minimum total time
        increment = max(0.0, float(increment))  # No negative increments

        # Clean and validate time values
        cleaned_times = []
        remaining_time = total_time

        for time in time_spent:
            # Ensure time is non-negative and not exceeding remaining time
            valid_time = max(0.0, min(float(time), remaining_time))
            cleaned_times.append(valid_time)

            # Update remaining time with increment
            remaining_time = max(0.0, remaining_time - valid_time + increment)

        # Calculate basic metrics
        avg_time = statistics.mean(cleaned_times) if cleaned_times else 0.0
        variance = statistics.variance(cleaned_times) if len(cleaned_times) > 1 else 0.0

        # Enhanced time pressure detection
        expected_time_per_move = total_time / (len(cleaned_times) * 2)  # Base expected time
        base_pressure_threshold = expected_time_per_move * 0.3

        # Dynamic pressure threshold based on game progress
        pressure_thresholds = []
        for i, time in enumerate(cleaned_times):
            # Early game: More lenient threshold
            if i < len(cleaned_times) * 0.2:
                threshold = base_pressure_threshold * 1.2
            # Late game: Stricter threshold due to time importance
            elif i > len(cleaned_times) * 0.8:
                threshold = base_pressure_threshold * 0.8
            else:
                threshold = base_pressure_threshold

            # Adjust for increment
            if increment > 0:
                threshold = max(increment * 0.5, threshold)

            pressure_thresholds.append(threshold)

        # Calculate pressure moves with dynamic thresholds
        pressure_moves = sum(1 for t, thresh in zip(cleaned_times, pressure_thresholds) if t <= thresh)
        pressure_percentage = (pressure_moves / len(cleaned_times)) * 100

        # Enhanced time management score calculation
        time_management_score = 0.0

        # Factor 1: Time usage consistency (35%)
        normalized_variance = min(1.0, variance / (expected_time_per_move**2))
        consistency_score = 1.0 - normalized_variance

        # Factor 2: Appropriate time usage (35%)
        time_usage_ratio = sum(cleaned_times) / total_time
        appropriate_usage = 1.0 - abs(0.5 - time_usage_ratio)  # Optimal ratio around 0.5

        # Factor 3: Time pressure handling (30%)
        pressure_handling = 1.0 - (pressure_percentage / 100)

        # Calculate final score with increment bonus
        increment_bonus = 0.1 if increment > 0 else 0.0  # Small bonus for increment time control

        time_management_score = (
            (consistency_score * 0.35) + (appropriate_usage * 0.35) + (pressure_handling * 0.30) + increment_bonus
        )

        # Normalize final score to 0-1 range
        time_management_score = min(1.0, max(0.0, time_management_score))

        return {
            "average_time": round(avg_time, 2),
            "time_pressure_moves": pressure_moves,
            "time_pressure_percentage": round(pressure_percentage, 2),
            "time_variance": round(variance, 2),
            "time_management_score": round(time_management_score, 3),
            "normalized_times": cleaned_times,
            "remaining_time": round(remaining_time, 2),
        }

    @staticmethod
    def _calculate_time_metrics(moves: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comprehensive time management metrics."""
        if not moves:
            return {
                "average_time": 0.0,
                "time_variance": 0.0,
                "time_consistency": 0.0,
                "time_pressure_moves": 0,
                "time_management_score": 0.0,
                "time_pressure_percentage": 0.0,
            }

        try:
            # Extract time data
            time_spent = []
            total_time = 0.0

            for move in moves:
                spent = move.get("time_spent", 0)
                if isinstance(spent, (int, float)) and spent >= 0:
                    time_spent.append(float(spent))
                    total_time += float(spent)

            if not time_spent:
                return MetricsCalculator._get_default_time_metrics()

            # Calculate basic metrics
            avg_time = statistics.mean(time_spent)
            time_variance = statistics.variance(time_spent) if len(time_spent) > 1 else 0.0

            # Calculate time pressure metrics
            expected_time = total_time / len(moves)
            pressure_threshold = expected_time * 0.3
            time_pressure_moves = sum(1 for t in time_spent if t <= pressure_threshold)
            time_pressure_percentage = (time_pressure_moves / len(moves) * 100) if moves else 0

            # Calculate time consistency
            time_variations = [abs(t - avg_time) / max(0.0001, avg_time) for t in time_spent]
            sum_variations = sum(time_variations)
            moves_len = max(1.0, float(len(moves)))
            time_consistency = 10.0 * (1.0 - min(1.0, sum_variations / moves_len))

            # Calculate time management score
            base_score = 100.0

            # Deduct for time pressure
            pressure_penalty = (time_pressure_percentage / 100) * 30  # Up to 30 points

            # Deduct for inconsistency
            consistency_penalty = (1 - (time_consistency / 100)) * 40  # Up to 40 points

            # Deduct for extreme variance
            variance_penalty = min(30, (time_variance / (avg_time**2)) * 30)  # Up to 30 points

            time_management_score = max(
                0, min(100, base_score - pressure_penalty - consistency_penalty - variance_penalty)
            )

            return {
                "average_time": round(avg_time, 1),
                "time_variance": round(time_variance, 1),
                "time_consistency": round(time_consistency, 1),
                "time_pressure_moves": time_pressure_moves,
                "time_management_score": round(time_management_score, 1),
                "time_pressure_percentage": round(time_pressure_percentage, 1),
            }

        except Exception as e:
            logger.error(f"Error calculating time metrics: {str(e)}")
            return MetricsCalculator._get_default_time_metrics()

    @staticmethod
    def _calculate_phase_time_metrics(moves: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate time metrics for a specific game phase."""
        if not moves:
            return {"average_time": 0.0, "time_pressure_percentage": 0.0, "time_consistency": 0.0}

        try:
            # Extract time spent values with proper conversion
            time_spent = []
            for m in moves:
                try:
                    time_val = m.get("time_spent", 0)
                    time_spent.append(float(time_val) if time_val is not None else 0.0)
                except (ValueError, TypeError):
                    time_spent.append(0.0)
            
            # If we have no valid time data, return defaults
            if not time_spent or all(t == 0 for t in time_spent):
                return {"average_time": 0.0, "time_pressure_percentage": 0.0, "time_consistency": 0.0}
                
            avg_time = statistics.mean(time_spent)

            # Calculate time pressure
            pressure_threshold = avg_time * 0.3
            pressure_moves = sum(1 for t in time_spent if t < pressure_threshold)
            pressure_percentage = (pressure_moves / len(moves) * 100.0) if len(moves) > 0 else 0.0

            # Calculate consistency with zero-division protection
            if avg_time > 0:
                variations = [abs(t - avg_time) / max(1.0, avg_time) for t in time_spent]
                consistency = 100.0 * (1.0 - min(1.0, sum(variations) / max(1, len(moves))))
            else:
                consistency = 0.0

            return {
                "average_time": round(avg_time, 2),
                "time_pressure_percentage": round(pressure_percentage, 1),
                "time_consistency": round(consistency, 1),
            }

        except Exception as e:
            logger.error(f"Error calculating phase time metrics: {str(e)}")
            return {"average_time": 0.0, "time_pressure_percentage": 0.0, "time_consistency": 0.0}

    @staticmethod
    def _calculate_time_management_score(
        time_spent: List[float],
        time_pressure_percentage: float,
        time_consistency: float,
        critical_time_ratio: float,
        phase_times: Dict[str, Dict[str, float]],
    ) -> float:
        """Calculate overall time management score."""
        try:
            # Base score starts at 100
            score = 100.0

            # Penalize for time pressure
            pressure_penalty = time_pressure_percentage * 0.3
            score -= pressure_penalty

            # Reward for consistency
            consistency_bonus = time_consistency * 0.3
            score += consistency_bonus

            # Evaluate critical time usage
            if critical_time_ratio > 0:
                if critical_time_ratio < 0.5:  # Too quick on critical moves
                    score -= 20.0
                elif critical_time_ratio > 2.0:  # Too slow on critical moves
                    score -= 10.0
                else:  # Good time usage on critical moves
                    score += 10.0

            # Evaluate phase time distribution
            opening_data = phase_times.get("opening", {})
            endgame_data = phase_times.get("endgame", {})
            
            opening_time = float(opening_data.get("average_time", 0))
            endgame_time = float(endgame_data.get("average_time", 0))
            
            if opening_time > 0 and endgame_time > 0:
                ratio = endgame_time / opening_time
                if ratio < 0.2:  # Too little time in endgame
                    score -= 15.0
                elif ratio > 2.0:  # Too much time in endgame
                    score -= 10.0

            return max(0.0, min(100.0, score))

        except Exception as e:
            logger.error(f"Error calculating time management score: {str(e)}")
            return 50.0  # Default to medium score on error

    @staticmethod
    def _calculate_accuracy(moves: List[Dict[str, Any]]) -> float:
        """Calculate move accuracy based on evaluation changes and position complexity."""
        try:
            total_weighted_score = 0.0
            total_weight = 0.0

            for move in moves:
                try:
                    # Get evaluation improvement
                    eval_improvement_val = move.get("evaluation_improvement")
                    if eval_improvement_val is None:
                        continue

                    try:
                        eval_improvement = float(str(eval_improvement_val))
                    except (ValueError, TypeError):
                        continue

                    # Get position metrics if available
                    position_metrics = cast(Dict[str, Any], move.get("position_metrics", {}))
                    position_quality = float(str(position_metrics.get("position_quality", "50.0")))
                    piece_activity = float(str(position_metrics.get("piece_activity", "50.0")))

                    # Calculate complexity based on position metrics
                    complexity_factors = [
                        position_quality,
                        piece_activity,
                        float(str(position_metrics.get("king_safety", "50.0"))),
                        float(str(position_metrics.get("pawn_structure", "50.0"))),
                    ]
                    position_complexity = sum(complexity_factors) / len(complexity_factors)

                    is_critical = bool(move.get("is_critical", False))

                    # Weight based on position complexity and critical moments
                    weight = 1.0
                    if is_critical:
                        weight *= 1.5  # Critical positions have higher weight
                    weight *= 0.5 + position_complexity / 100.0  # More complex positions have higher weight

                    # Calculate move score
                    if eval_improvement > 0:
                        # Reward for finding improvements
                        move_score = 100.0 + min(eval_improvement / 5.0, 20.0)  # Bonus up to 20 points
                    else:
                        # Penalize for mistakes, using a non-linear scale
                        capped_loss = min(abs(eval_improvement), 400.0)  # Cap at 4 pawns worth
                        move_score = 100.0 * (1.0 - (capped_loss / 400.0) ** 0.6)  # Less punishing for small mistakes

                    total_weighted_score += move_score * weight
                    total_weight += weight

                except Exception as e:
                    logger.error(f"Error processing move for accuracy: {str(e)}")
                    continue

            # Calculate final accuracy
            return total_weighted_score / max(1.0, total_weight) if total_weight > 0 else 0.0

        except Exception as e:
            logger.error(f"Error calculating accuracy: {str(e)}")
            return 0.0

    @staticmethod
    def _calculate_consistency(moves: List[Dict[str, Any]]) -> float:
        """Calculate consistency score based on move quality streaks and error patterns."""
        if not moves:
            return 100.0  # Perfect consistency for empty game
            
        # Calculate move quality streaks
        quality_streaks = []
        current_streak = 0
        for move in moves:
            if move['classification'] in ['good', 'excellent']:
                current_streak += 1
            else:
                if current_streak > 0:
                    quality_streaks.append(current_streak)
                current_streak = 0
        if current_streak > 0:
            quality_streaks.append(current_streak)
            
        # Calculate error patterns
        mistakes_in_window = 0.0
        mistake_clusters = 0.0
        window_size = 5
        for i in range(len(moves)):
            window = moves[i:i+window_size]
            window_mistakes = sum(1 for m in window if m['classification'] in ['mistake', 'blunder'])
            if window_mistakes > 1:
                mistake_clusters += 1.0
            mistakes_in_window += float(window_mistakes)
            
        # Calculate time consistency
        times = [move.get('time_spent', 0) for move in moves if move.get('time_spent') is not None]
        if not times:
            time_consistency = 100.0
        else:
            avg_time = sum(times) / max(1.0, float(len(times)))
            time_variations = [abs(t - avg_time) for t in times]
            avg_variation = sum(time_variations) / max(1.0, float(len(time_variations)))
            time_consistency = max(0.0, 100.0 - (avg_variation / max(1.0, avg_time) * 100.0))
            
        # Calculate final score
        streak_score = (sum(quality_streaks) / max(1.0, float(len(moves)))) * 100.0 if quality_streaks else 0.0
        error_score = max(0.0, 100.0 - (mistakes_in_window / max(1.0, float(len(moves))) * 100.0))
        cluster_score = max(0.0, 100.0 - (mistake_clusters / max(1.0, float(len(moves))) * 100.0))
        
        final_score = (streak_score * 0.4 + error_score * 0.3 + cluster_score * 0.2 + time_consistency * 0.1)
        return max(0.0, min(100.0, final_score))

    @staticmethod
    def _calculate_phase_metrics(moves: List[Dict[str, Any]], is_white: bool) -> Dict[str, Any]:
        """Calculate enhanced metrics for a specific game phase."""
        try:
            # Initialize metrics
            total_positions = 0
            successful = 0.0
            missed = 0
            brilliant_moves = 0
            pattern_scores: List[float] = []

            # First pass: identify tactical positions
            tactical_positions: List[TacticalPosition] = []

            for move in moves:
                if move.get("is_tactical", False):
                    tactical_positions.append(
                        {
                            "move": move,
                            "features": move.get("tactical_features", []),
                            "evaluation": float(str(move.get("evaluation", "0.0"))),
                        }
                    )
                    total_positions += 1

            # Second pass: analyze tactical positions
            for i, tpos in enumerate(tactical_positions):
                move = cast(Dict[str, Any], tpos["move"])
                try:
                    improvement_val = move.get("evaluation_improvement")
                    eval_improvement = float(str(improvement_val)) if improvement_val is not None else 0.0
                except (ValueError, TypeError):
                    eval_improvement = 0.0

                # Success calculation with normalized scoring
                if eval_improvement > 0 if is_white else eval_improvement < 0:
                    success_weight = 1.0

                    # Weight based on features with normalized values
                    features = cast(List[str], tpos["features"])
                    if "check" in features:
                        success_weight *= 1.1  # Reduced from 1.2
                    if "material" in features:
                        success_weight *= 1.05  # Reduced from 1.1
                    if "complex_position" in features:
                        success_weight *= 1.15  # Reduced from 1.3

                    successful += success_weight

                    # Identify brilliant moves with normalized threshold
                    if abs(eval_improvement) > 200 and len(features) >= 2:  # Reduced from 300
                        brilliant_moves += 1

                # Pattern recognition with normalized scoring
                if i > 0:
                    prev_pos = tactical_positions[i - 1]
                    try:
                        prev_improvement_val = prev_pos["move"].get("evaluation_improvement")
                        prev_eval = float(str(prev_improvement_val)) if prev_improvement_val is not None else 0.0

                        # Calculate normalized pattern score
                        pattern_strength = min(1.0, (abs(eval_improvement) + abs(prev_eval)) / 400.0)
                        pattern_scores.append(pattern_strength * 100.0)

                    except (ValueError, TypeError):
                        continue

            # Calculate final metrics with proper normalization
            success_rate = successful / max(1, total_positions)
            pattern_recognition = statistics.mean(pattern_scores) if pattern_scores else 0.0

            return {
                "total_positions": total_positions,
                "success_rate": float(success_rate),
                "pattern_recognition": float(pattern_recognition),
                "brilliant_moves": brilliant_moves,
                "normalized_score": float((success_rate + pattern_recognition) / 2.0),
            }

        except Exception as e:
            logger.error(f"Error calculating phase metrics: {str(e)}")
            return {
                "total_positions": 0,
                "success_rate": 0.0,
                "pattern_recognition": 0.0,
                "brilliant_moves": 0,
                "normalized_score": 0.0,
            }

    @staticmethod
    def _calculate_tactical_metrics(moves: List[Dict[str, Any]], is_white: bool) -> Dict[str, Any]:
        """Calculate enhanced tactical performance metrics."""
        if not moves:
            return MetricsCalculator._get_default_tactical_metrics()

        try:
            # Enhanced tactical opportunity detection
            tactical_positions: List[Dict[str, Any]] = []
            opportunities: int = 0
            successful: float = 0.0
            brilliant_moves: int = 0
            pattern_scores: List[float] = []

            # First pass: identify tactical positions
            for move in moves:
                is_tactical = False
                tactical_features: List[str] = []

                # Check for material gain/loss
                try:
                    material_val = move.get("material_change")
                    material_change = float(str(material_val)) if material_val is not None else 0.0
                    if abs(material_change) >= 1:  # At least a pawn worth
                        is_tactical = True
                        tactical_features.append("material")
                except (ValueError, TypeError):
                    material_change = 0.0

                # Check for check/checkmate
                if move.get("is_check", False):
                    is_tactical = True
                    tactical_features.append("check")

                # Check for significant position improvement
                try:
                    improvement_val = move.get("evaluation_improvement")
                    eval_improvement = float(str(improvement_val)) if improvement_val is not None else 0.0
                    if abs(eval_improvement) > 200:  # 2 pawns worth
                        is_tactical = True
                        tactical_features.append("position_improvement")
                except (ValueError, TypeError):
                    eval_improvement = 0.0

                # Check for piece activity increase
                try:
                    activity_val = move.get("piece_activity_change")
                    activity_change = float(str(activity_val)) if activity_val is not None else 0.0
                    if activity_change > 0.3:
                        is_tactical = True
                        tactical_features.append("piece_activity")
                except (ValueError, TypeError):
                    activity_change = 0.0

                # Consider position complexity
                try:
                    complexity_val = move.get("position_complexity")
                    complexity = float(str(complexity_val)) if complexity_val is not None else 0.5
                    if complexity > 0.7:  # High complexity positions more likely tactical
                        is_tactical = True
                        tactical_features.append("complex_position")
                except (ValueError, TypeError):
                    complexity = 0.5

                if is_tactical:
                    tactical_positions.append(
                        {
                            "move": move,
                            "features": tactical_features,
                            "complexity": complexity,
                            "eval_improvement": eval_improvement,
                        }
                    )

            opportunities = len(tactical_positions)

            # Second pass: analyze tactical positions
            for i, tpos in enumerate(tactical_positions):
                move = tpos["move"]
                try:
                    improvement_val = move.get("evaluation_improvement")
                    eval_improvement = float(str(improvement_val)) if improvement_val is not None else 0.0
                except (ValueError, TypeError):
                    eval_improvement = 0.0

                # Success calculation
                if eval_improvement > 0 if is_white else eval_improvement < 0:
                    success_weight = 1.0

                    # Weight based on features
                    if "check" in tpos["features"]:
                        success_weight *= 1.2
                    if "material" in tpos["features"]:
                        success_weight *= 1.1
                    if "complex_position" in tpos["features"]:
                        success_weight *= 1.3

                    successful += success_weight

                    # Identify brilliant moves
                    if abs(eval_improvement) > 300 and len(tpos["features"]) >= 2:
                        brilliant_moves += 1

                # Pattern recognition
                if i > 0:
                    prev_pos = tactical_positions[i - 1]
                    try:
                        prev_improvement_val = prev_pos["move"].get("evaluation_improvement")
                        prev_eval = float(str(prev_improvement_val)) if prev_improvement_val is not None else 0.0
                        if abs(prev_eval) > 100 and abs(eval_improvement) > 100:
                            pattern_scores.append(100.0)
                        elif abs(prev_eval) > 50 and abs(eval_improvement) > 50:
                            pattern_scores.append(50.0)
                    except (ValueError, TypeError):
                        continue

            # Calculate metrics
            success_rate = successful / max(1, opportunities) * 100.0
            pattern_recognition = statistics.mean(pattern_scores) if pattern_scores else 0.0

            # Calculate tactical score
            tactical_score = 0.0
            if opportunities > 0:
                # Base score from success rate
                tactical_score = success_rate * 0.4

                # Bonus for brilliant moves
                brilliant_bonus = (brilliant_moves / max(1, opportunities)) * 20.0
                tactical_score += brilliant_bonus * 0.2

                # Pattern recognition bonus
                tactical_score += pattern_recognition * 0.2

                # Opportunity rate bonus
                opportunity_rate = (opportunities / len(moves)) * 100.0
                tactical_score += min(opportunity_rate * 0.2, 20.0)

            missed_opportunities = opportunities - int(successful)

            return {
                "opportunities": opportunities,
                "successful": round(successful, 1),
                "brilliant_moves": brilliant_moves,
                "missed": missed_opportunities,
                "success_rate": round(success_rate, 1),
                "pattern_recognition": round(pattern_recognition, 1),
                "tactical_score": round(tactical_score, 1),
            }

        except Exception as e:
            logger.error(f"Error calculating tactical metrics: {str(e)}")
            return MetricsCalculator._get_default_tactical_metrics()

    @staticmethod
    def _get_default_tactical_metrics() -> Dict[str, Any]:
        """Return default tactical metrics."""
        return {
            "opportunities": 0,
            "successful": 0,
            "brilliant_moves": 0,
            "missed": 0,
            "success_rate": 0.0,
            "pattern_recognition": 0.0,
            "tactical_score": 0.0,
        }

    @staticmethod
    def _calculate_advantage_metrics(moves: List[Dict[str, Any]], is_white: bool) -> Dict[str, Any]:
        """Calculate metrics related to advantage maintenance and conversion."""
        if not moves:
            return {
                "max_advantage": 0.0,
                "min_advantage": 0.0,
                "average_advantage": 0.0,
                "advantage_conversion": 0.0,
                "pressure_handling": 0.0,
                "advantage_duration": 0,
                "winning_positions": 0,
                "advantage_retention": 0.0,
                "advantage_trend": 0.0,
            }

        try:
            # Track advantage throughout the game
            advantages: List[float] = []
            winning_positions = 0
            advantage_retention = 0

            for i, move in enumerate(moves):
                try:
                    eval_after = float(str(move.get("eval_after", "0.0")))
                except (ValueError, TypeError):
                    eval_after = 0.0
                # Adjust evaluation based on color
                eval_after = eval_after if is_white else -eval_after
                advantages.append(eval_after)

                # Track winning positions (advantage > 2 pawns)
                if eval_after > 200.0:
                    winning_positions += 1
                    # Check if advantage is maintained
                    if i < len(moves) - 1:
                        try:
                            next_eval = float(str(moves[i + 1].get("eval_after", "0.0")))
                            next_eval = next_eval if is_white else -next_eval
                            if next_eval > 150.0:  # Still maintaining significant advantage
                                advantage_retention += 1
                        except (ValueError, TypeError):
                            continue

            # Calculate advantage metrics with proper validation
            max_advantage = max(advantages) if advantages else 0.0
            min_advantage = min(advantages) if advantages else 0.0
            avg_advantage = statistics.mean(advantages) if advantages else 0.0

            # Calculate advantage conversion with validation
            advantage_positions = sum(1 for a in advantages if a > 200.0)
            converted_positions = sum(
                1 for i in range(len(advantages) - 1) if advantages[i] > 200.0 and advantages[i + 1] >= advantages[i]
            )

            conversion_rate = converted_positions / max(1, advantage_positions) * 100.0
            retention_rate = advantage_retention / max(1, winning_positions) * 100.0

            # Calculate pressure handling with validation
            pressure_positions = sum(1 for a in advantages if a < -150.0)
            good_defenses = sum(
                1 for i in range(len(advantages) - 1) if advantages[i] < -150.0 and advantages[i + 1] > advantages[i]
            )

            pressure_score = good_defenses / max(1, pressure_positions) * 100.0

            # Calculate advantage trend with validation
            advantage_trend: float = 0.0
            if len(advantages) > 5:
                early_avg = statistics.mean(advantages[: len(advantages) // 3])
                late_avg = statistics.mean(advantages[-len(advantages) // 3 :])
                advantage_trend = late_avg - early_avg

            return {
                "max_advantage": round(max_advantage / 100.0, 2),  # Convert to pawn units
                "min_advantage": round(min_advantage / 100.0, 2),
                "average_advantage": round(avg_advantage / 100.0, 2),
                "advantage_conversion": round(conversion_rate, 1),
                "pressure_handling": round(pressure_score, 1),
                "advantage_duration": advantage_positions,
                "winning_positions": winning_positions,
                "advantage_retention": round(retention_rate, 1),
                "advantage_trend": round(advantage_trend / 100.0, 2),
            }

        except Exception as e:
            logger.error(f"Error calculating advantage metrics: {str(e)}")
            return {
                "max_advantage": 0.0,
                "min_advantage": 0.0,
                "average_advantage": 0.0,
                "advantage_conversion": 0.0,
                "pressure_handling": 0.0,
                "advantage_duration": 0,
                "winning_positions": 0,
                "advantage_retention": 0.0,
                "advantage_trend": 0.0,
            }

    @staticmethod
    def _calculate_resourcefulness_metrics(moves: List[Dict[str, Any]], is_white: bool) -> Dict[str, Any]:
        """Calculate metrics related to resourcefulness and finding best moves under pressure."""
        if not moves:
            return {
                "recovery_rate": 0.0,
                "defensive_score": 0.0,
                "critical_defense": 0.0,
                "tactical_defense": 0.0,
                "best_move_finding": 0.0,
                "position_recovery": 0.0,
                "comeback_potential": 0.0,
                "critical_defense_score": 0.0,
                "defensive_resourcefulness": 0.0,
            }

        try:
            # Track critical positions and responses
            critical_positions: List[Dict[str, Any]] = []
            defensive_scores: List[float] = []
            recovery_positions: List[float] = []
            tactical_defenses: List[float] = []

            for i, move in enumerate(moves):
                try:
                    eval_before = float(str(move.get("eval_before", "0.0")))
                    eval_after = float(str(move.get("eval_after", "0.0")))
                except (ValueError, TypeError):
                    eval_before = 0.0
                    eval_after = 0.0

                # Adjust evaluations based on color
                eval_before = eval_before if is_white else -eval_before
                eval_after = eval_after if is_white else -eval_after

                # Identify critical positions
                is_critical = (
                    bool(move.get("is_critical", False))
                    or eval_before < -150.0  # Bad position
                    or bool(move.get("in_check", False))  # Under check
                    or bool(move.get("under_attack", False))  # Piece under attack
                )

                if is_critical:
                    critical_positions.append(
                        {
                            "position": move,
                            "eval_before": eval_before,
                            "eval_after": eval_after,
                            "improvement": float(eval_after - eval_before),
                        }
                    )

                    # Calculate defensive score
                    if eval_after > eval_before:
                        defensive_scores.append(min(100.0, (eval_after - eval_before) / 2.0))
                    elif eval_after >= eval_before - 50.0:  # Minimal loss in bad position
                        defensive_scores.append(50.0)
                    else:
                        defensive_scores.append(0.0)

                # Track position recovery
                if eval_before < -200.0 and eval_after > eval_before:
                    recovery_score = min(100.0, (eval_after - eval_before) / 4.0)
                    recovery_positions.append(recovery_score)

                # Track tactical defense
                if bool(move.get("is_tactical", False)) and eval_before < -100.0:
                    if eval_after > eval_before:
                        tactical_defenses.append(100.0)
                    elif eval_after >= eval_before - 50.0:
                        tactical_defenses.append(50.0)

            # Calculate metrics
            total_critical = max(1, len(critical_positions))
            total_moves = len(moves)

            # Calculate recovery rate
            recovery_rate = (len(recovery_positions) / total_moves * 100.0) if total_moves > 0 else 0.0

            # Calculate defensive score
            defensive_score = statistics.mean(defensive_scores) if defensive_scores else 0.0

            # Calculate critical defense
            critical_defense = sum(1 for pos in critical_positions if float(pos["improvement"]) > 0.0)
            critical_defense_rate = (critical_defense / total_critical * 100.0) if total_critical > 0 else 0.0

            # Calculate tactical defense
            tactical_defense_score = statistics.mean(tactical_defenses) if tactical_defenses else 0.0

            # Calculate best move finding
            best_moves = sum(1 for m in moves if bool(m.get("is_critical", False)) and bool(m.get("is_best", False)))
            best_move_rate = (best_moves / total_critical * 100.0) if total_critical > 0 else 0.0

            # Calculate position recovery
            position_recovery = statistics.mean(recovery_positions) if recovery_positions else 0.0

            # Calculate comeback potential
            worst_eval = min((float(pos["eval_before"]) for pos in critical_positions), default=0.0)
            final_eval = float(str(moves[-1].get("eval_after", "0.0"))) if moves else 0.0
            comeback_potential = min(100.0, max(0.0, (final_eval - worst_eval) / 4.0)) if worst_eval < -200.0 else 0.0

            return {
                "recovery_rate": round(recovery_rate, 1),
                "defensive_score": round(defensive_score, 1),
                "critical_defense": round(critical_defense_rate, 1),
                "tactical_defense": round(tactical_defense_score, 1),
                "best_move_finding": round(best_move_rate, 1),
                "position_recovery": round(position_recovery, 1),
                "comeback_potential": round(comeback_potential, 1),
                "critical_defense_score": round(critical_defense_rate, 1),
                "defensive_resourcefulness": round((defensive_score + critical_defense_rate) / 2.0, 1),
            }

        except Exception as e:
            logger.error(f"Error calculating resourcefulness metrics: {str(e)}")
            return {
                "recovery_rate": 0.0,
                "defensive_score": 0.0,
                "critical_defense": 0.0,
                "tactical_defense": 0.0,
                "best_move_finding": 0.0,
                "position_recovery": 0.0,
                "comeback_potential": 0.0,
                "critical_defense_score": 0.0,
                "defensive_resourcefulness": 0.0,
            }

    @staticmethod
    def _calculate_overall_metrics(moves: List[Dict[str, Any]], is_white: bool) -> Dict[str, Any]:
        """Calculate overall game metrics with enhanced validation."""
        try:
            total_moves = len(moves)
            mistakes = sum(1 for m in moves if m.get("is_mistake", False))
            blunders = sum(1 for m in moves if m.get("is_blunder", False))
            inaccuracies = sum(1 for m in moves if m.get("evaluation_drop", 0) > 100)
            quality_moves = sum(1 for m in moves if m.get("evaluation_improvement", 0) > 50)

            # Calculate overall accuracy with perspective
            accuracy = MetricsCalculator._calculate_accuracy(moves)
            consistency = MetricsCalculator._calculate_consistency(moves)

            # Calculate critical positions
            critical_positions = sum(1 for m in moves if m.get("is_critical", False))

            # Calculate average position quality
            position_quality = (
                statistics.mean(
                    [
                        m.get("position_complexity", 0.5)
                        * (1 - abs(m.get("eval_after", 0)) / 1000)  # Normalize evaluation
                        for m in moves
                    ]
                )
                if moves
                else 0.0
            )

            return {
                "total_moves": total_moves,
                "accuracy": round(accuracy, 1),
                "consistency_score": round(consistency, 1),
                "mistakes": mistakes,
                "blunders": blunders,
                "inaccuracies": inaccuracies,
                "quality_moves": quality_moves,
                "critical_positions": critical_positions,
                "position_quality": round(position_quality * 100, 1),  # Convert to percentage
            }
        except Exception as e:
            logger.error(f"Error calculating overall metrics: {str(e)}")
            return MetricsCalculator._get_default_overall_metrics()

    @staticmethod
    def _get_default_overall_metrics() -> Dict[str, Any]:
        """Return default overall metrics."""
        return {
            "total_moves": 0,
            "accuracy": 0.0,
            "consistency_score": 0.0,
            "mistakes": 0,
            "blunders": 0,
            "inaccuracies": 0,
            "quality_moves": 0,
            "critical_positions": 0,
            "position_quality": 0.0,
        }

    @staticmethod
    def _validate_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize all metrics to ensure they are within reasonable ranges."""
        try:
            # Validate overall metrics
            if "overall" in metrics:
                overall = metrics["overall"]
                overall["accuracy"] = max(0, min(100, overall.get("accuracy", 0)))
                overall["consistency_score"] = max(0, min(100, overall.get("consistency_score", 0)))
                overall["mistakes"] = max(0, overall.get("mistakes", 0))
                overall["blunders"] = max(0, overall.get("blunders", 0))
                overall["inaccuracies"] = max(0, overall.get("inaccuracies", 0))
                overall["quality_moves"] = max(0, overall.get("quality_moves", 0))
                overall["critical_positions"] = max(0, overall.get("critical_positions", 0))
                overall["position_quality"] = max(0, min(100, overall.get("position_quality", 0)))

            # Validate phase metrics
            if "phases" in metrics:
                for phase in ["opening", "middlegame", "endgame"]:
                    if phase in metrics["phases"]:
                        phase_data = metrics["phases"][phase]
                        phase_data["accuracy"] = max(0, min(100, phase_data.get("accuracy", 0)))
                        phase_data["moves_count"] = max(0, phase_data.get("moves_count", 0))
                        phase_data["mistakes"] = max(0, phase_data.get("mistakes", 0))
                        phase_data["blunders"] = max(0, phase_data.get("blunders", 0))
                        phase_data["critical_moves"] = max(0, phase_data.get("critical_moves", 0))

                        # Validate time management for phase
                        if "time_management" in phase_data:
                            time_mgmt = phase_data["time_management"]
                            time_mgmt["average_time"] = max(0, min(3600, time_mgmt.get("average_time", 0)))
                            time_mgmt["time_pressure_percentage"] = max(
                                0, min(100, time_mgmt.get("time_pressure_percentage", 0))
                            )
                            time_mgmt["time_consistency"] = max(0, min(100, time_mgmt.get("time_consistency", 0)))

            # Validate tactical metrics
            if "tactics" in metrics:
                tactics = metrics["tactics"]
                tactics["opportunities"] = max(0, tactics.get("opportunities", 0))
                tactics["successful"] = max(0, min(tactics.get("successful", 0), tactics.get("opportunities", 0)))
                tactics["brilliant_moves"] = max(0, tactics.get("brilliant_moves", 0))
                tactics["missed"] = max(0, tactics.get("missed", 0))
                tactics["success_rate"] = max(0, min(100, tactics.get("success_rate", 0)))
                tactics["pattern_recognition"] = max(0, min(100, tactics.get("pattern_recognition", 0)))
                tactics["tactical_score"] = max(0, min(100, tactics.get("tactical_score", 0)))

            # Validate time management metrics
            if "time_management" in metrics:
                time_mgmt = metrics["time_management"]
                time_mgmt["average_time"] = max(0, min(3600, time_mgmt.get("average_time", 0)))
                time_mgmt["time_variance"] = max(0, time_mgmt.get("time_variance", 0))
                time_mgmt["time_consistency"] = max(0, min(100, time_mgmt.get("time_consistency", 0)))
                time_mgmt["time_pressure_moves"] = max(0, time_mgmt.get("time_pressure_moves", 0))
                time_mgmt["time_management_score"] = max(0, min(100, time_mgmt.get("time_management_score", 0)))
                time_mgmt["time_pressure_percentage"] = max(0, min(100, time_mgmt.get("time_pressure_percentage", 0)))

            # Validate advantage metrics
            if "advantage" in metrics:
                advantage = metrics["advantage"]
                advantage["max_advantage"] = max(-20, min(20, advantage.get("max_advantage", 0)))
                advantage["min_advantage"] = max(-20, min(20, advantage.get("min_advantage", 0)))
                advantage["average_advantage"] = max(-20, min(20, advantage.get("average_advantage", 0)))
                advantage["advantage_conversion"] = max(0, min(100, advantage.get("advantage_conversion", 0)))
                advantage["pressure_handling"] = max(0, min(100, advantage.get("pressure_handling", 0)))
                advantage["advantage_duration"] = max(0, advantage.get("advantage_duration", 0))
                advantage["winning_positions"] = max(0, advantage.get("winning_positions", 0))
                advantage["advantage_retention"] = max(0, min(100, advantage.get("advantage_retention", 0)))
                advantage["advantage_trend"] = max(-20, min(20, advantage.get("advantage_trend", 0)))

            # Validate resourcefulness metrics
            if "resourcefulness" in metrics:
                resourcefulness = metrics["resourcefulness"]
                resourcefulness["recovery_rate"] = max(0, min(100, resourcefulness.get("recovery_rate", 0)))
                resourcefulness["defensive_score"] = max(0, min(100, resourcefulness.get("defensive_score", 0)))
                resourcefulness["critical_defense"] = max(0, min(100, resourcefulness.get("critical_defense", 0)))
                resourcefulness["tactical_defense"] = max(0, min(100, resourcefulness.get("tactical_defense", 0)))
                resourcefulness["best_move_finding"] = max(0, min(100, resourcefulness.get("best_move_finding", 0)))
                resourcefulness["position_recovery"] = max(0, min(100, resourcefulness.get("position_recovery", 0)))
                resourcefulness["comeback_potential"] = max(0, min(100, resourcefulness.get("comeback_potential", 0)))
                resourcefulness["critical_defense_score"] = max(
                    0, min(100, resourcefulness.get("critical_defense_score", 0))
                )
                resourcefulness["defensive_resourcefulness"] = max(
                    0, min(100, resourcefulness.get("defensive_resourcefulness", 0))
                )

            return metrics
        except Exception as e:
            logger.error(f"Error validating metrics: {str(e)}")
            return metrics  # Return original metrics if validation fails

    @staticmethod
    def _get_default_metrics() -> Dict[str, Any]:
        """Return default metrics structure matching frontend requirements."""
        default_time_management = {
            "average_time": 0.0,
            "time_variance": 0.0,
            "time_consistency": 0.0,
            "time_pressure_moves": 0,
            "time_management_score": 0.0,
            "time_pressure_percentage": 0.0,
        }

        return {
            "overall": {
                "accuracy": 0.0,
                "consistency": 0.0,
                "mistakes": 0,
                "blunders": 0,
                "inaccuracies": 0,
                "quality_moves": 0,
                "critical_positions": 0,
                "position_quality": 0.0,
            },
            "phases": {
                "opening": {
                    "accuracy": 0.0,
                    "moves": [],
                    "mistakes": 0,
                    "blunders": 0,
                    "critical_moves": 0,
                    "time_management": default_time_management.copy(),
                },
                "middlegame": {
                    "accuracy": 0.0,
                    "moves": [],
                    "mistakes": 0,
                    "blunders": 0,
                    "critical_moves": 0,
                    "time_management": default_time_management.copy(),
                },
                "endgame": {
                    "accuracy": 0.0,
                    "moves": [],
                    "mistakes": 0,
                    "blunders": 0,
                    "critical_moves": 0,
                    "time_management": default_time_management.copy(),
                },
            },
            "tactics": {
                "opportunities": 0,
                "successful": 0,
                "brilliant_moves": 0,
                "missed": 0,
                "success_rate": 0.0,
                "pattern_recognition": 0.0,
                "tactical_score": 0.0,
            },
            "time_management": default_time_management.copy(),
            "advantage": {
                "max_advantage": 0.0,
                "min_advantage": 0.0,
                "average_advantage": 0.0,
                "advantage_conversion": 0.0,
                "pressure_handling": 0.0,
                "advantage_duration": 0,
                "winning_positions": 0,
                "advantage_retention": 0.0,
                "advantage_trend": 0.0,
            },
            "resourcefulness": {
                "recovery_rate": 0.0,
                "defensive_score": 0.0,
                "critical_defense": 0.0,
                "tactical_defense": 0.0,
                "best_move_finding": 0.0,
                "position_recovery": 0.0,
                "comeback_potential": 0.0,
                "critical_defense_score": 0.0,
                "defensive_resourcefulness": 0.0,
            },
        }

    @staticmethod
    def _calculate_move_quality(moves: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate move quality metrics.
        
        Args:
            moves: List of analyzed moves with their evaluations
            
        Returns:
            Dictionary containing move quality metrics
        """
        try:
            if not moves:
                return {
                    "accuracy": 0.0,
                    "mistakes": 0.0,
                    "blunders": 0.0,
                    "inaccuracies": 0.0,
                    "quality_moves": 0.0
                }
            
            total_moves = float(len(moves))
            
            # Count move types
            mistakes = sum(1.0 for m in moves if m.get("is_mistake", False))
            blunders = sum(1.0 for m in moves if m.get("is_blunder", False))
            inaccuracies = sum(1.0 for m in moves if m.get("is_inaccuracy", False))
            quality_moves = sum(1.0 for m in moves if m.get("is_best", False))
            
            # Calculate percentages
            accuracy = ((total_moves - (mistakes + blunders + inaccuracies)) / total_moves) * 100.0
            
            return {
                "accuracy": max(0.0, min(100.0, accuracy)),
                "mistakes": (mistakes / total_moves) * 100.0,
                "blunders": (blunders / total_moves) * 100.0,
                "inaccuracies": (inaccuracies / total_moves) * 100.0,
                "quality_moves": (quality_moves / total_moves) * 100.0
            }
            
        except Exception as e:
            logger.error(f"Error calculating move quality: {str(e)}")
            raise MetricsError(f"Failed to calculate move quality: {str(e)}")

    @staticmethod
    def _calculate_time_management(time_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate time management metrics.
        
        Args:
            time_data: List of time data for each move
            
        Returns:
            Dictionary containing time management metrics
        """
        try:
            if not time_data:
                return {
                    "time_usage": 0.0,
                    "time_consistency": 0.0,
                    "time_pressure": 0.0,
                    "avg_time_per_move": 0.0
                }
            
            total_moves = float(len(time_data))
            total_time = sum(float(t.get("time_spent", 0.0)) for t in time_data)
            
            # Calculate average time per move
            avg_time_per_move = total_time / total_moves if total_moves > 0 else 0.0
            
            # Calculate time variations
            time_variations = []
            for i in range(1, len(time_data)):
                prev_time = float(time_data[i-1].get("time_spent", 0.0))
                curr_time = float(time_data[i].get("time_spent", 0.0))
                if prev_time > 0:
                    variation = abs(curr_time - prev_time) / prev_time
                    time_variations.append(variation)
            
            # Calculate time consistency
            time_consistency = 100.0 * (1.0 - min(1.0, sum(time_variations) / max(1.0, float(len(time_variations)))))
            
            # Calculate time pressure (percentage of moves with less than 10% of average time)
            time_pressure = sum(1.0 for t in time_data 
                              if float(t.get("time_spent", 0.0)) < 0.1 * avg_time_per_move) / total_moves * 100.0
            
            # Calculate time usage (percentage of total time used)
            time_usage = min(100.0, (total_time / 3600.0) * 100.0)  # Assuming 1 hour game
            
            return {
                "time_usage": max(0.0, min(100.0, time_usage)),
                "time_consistency": max(0.0, min(100.0, time_consistency)),
                "time_pressure": max(0.0, min(100.0, time_pressure)),
                "avg_time_per_move": avg_time_per_move
            }
            
        except Exception as e:
            logger.error(f"Error calculating time management: {str(e)}")
            raise MetricsError(f"Failed to calculate time management: {str(e)}")

    def __init__(self):
        """Initialize the metrics calculator."""
        pass
