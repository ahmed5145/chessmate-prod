"""
Metrics calculator for chess games.
Handles calculation of various game metrics and statistics.
"""

import logging
from typing import List, Dict, Any, Optional, Union, cast, TypedDict
import statistics
import math

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
            'average_time': 0.0,
            'time_pressure_moves': 0,
            'time_pressure_percentage': 0.0,
            'time_variance': 0.0
        }

    @staticmethod
    def calculate_game_metrics(moves: List[Dict[str, Any]], is_white: bool = True) -> Dict[str, Any]:
        """Calculate comprehensive game metrics."""
        try:
            if not moves:
                return MetricsCalculator._get_default_metrics()

            # Calculate phase transitions
            phases = MetricsCalculator._detect_phase_transitions(moves)
            
            # Calculate overall metrics
            try:
                overall_metrics = {
                    'accuracy': MetricsCalculator._calculate_accuracy(moves),
                    'consistency': MetricsCalculator._calculate_consistency(moves),
                    'mistakes': sum(1 for m in moves if m.get('is_mistake', False)),
                    'blunders': sum(1 for m in moves if m.get('is_blunder', False)),
                    'inaccuracies': sum(1 for m in moves if m.get('is_inaccuracy', False)),
                    'quality_moves': sum(1 for m in moves if m.get('is_best', False)),
                    'critical_positions': sum(1 for m in moves if m.get('is_critical', False)),
                    'position_quality': sum(m.get('position_quality', 0) for m in moves) / len(moves) if moves else 0
                }
            except Exception as e:
                logger.error(f"Error calculating overall metrics: {str(e)}")
                overall_metrics = MetricsCalculator._get_default_metrics()['overall']

            # Calculate phase-specific metrics
            try:
                phase_metrics = {
                    'opening': MetricsCalculator._calculate_phase_metrics(moves[:phases['opening']], is_white),
                    'middlegame': MetricsCalculator._calculate_phase_metrics(moves[phases['opening']:phases['middlegame']], is_white),
                    'endgame': MetricsCalculator._calculate_phase_metrics(moves[phases['middlegame']:], is_white)
                }
            except Exception as e:
                logger.error(f"Error calculating phase metrics: {str(e)}")
                phase_metrics = MetricsCalculator._get_default_metrics()['phases']

            # Calculate tactical metrics
            try:
                tactical_metrics = MetricsCalculator._calculate_tactical_metrics(moves, is_white)
            except Exception as e:
                logger.error(f"Error calculating tactical metrics: {str(e)}")
                tactical_metrics = MetricsCalculator._get_default_metrics()['tactics']

            # Calculate time management metrics
            try:
                time_metrics = MetricsCalculator._calculate_time_metrics(moves)
            except Exception as e:
                logger.error(f"Error calculating time metrics: {str(e)}")
                time_metrics = MetricsCalculator._get_default_metrics()['time_management']

            # Calculate advantage metrics
            try:
                advantage_metrics = MetricsCalculator._calculate_advantage_metrics(moves, is_white)
            except Exception as e:
                logger.error(f"Error calculating advantage metrics: {str(e)}")
                advantage_metrics = MetricsCalculator._get_default_metrics()['advantage']

            # Calculate resourcefulness metrics
            try:
                resourcefulness_metrics = MetricsCalculator._calculate_resourcefulness_metrics(moves, is_white)
            except Exception as e:
                logger.error(f"Error calculating resourcefulness metrics: {str(e)}")
                resourcefulness_metrics = MetricsCalculator._get_default_metrics()['resourcefulness']

            # Validate and return all metrics
            metrics = {
                'overall': overall_metrics,
                'phases': phase_metrics,
                'tactics': tactical_metrics,
                'time_management': time_metrics,
                'advantage': advantage_metrics,
                'resourcefulness': resourcefulness_metrics
            }
            
            return MetricsCalculator._validate_metrics(metrics)

        except Exception as e:
            logger.error(f"Error calculating game metrics: {str(e)}")
            return MetricsCalculator._get_default_metrics()

    @staticmethod
    def _detect_phase_transitions(moves: List[Dict[str, Any]]) -> Dict[str, int]:
        """Enhanced phase detection using multiple indicators."""
        try:
            total_moves = len(moves)
            if total_moves == 0:
                return {'opening': 0, 'middlegame': 0}

            # Initialize phase transition points
            opening_end = min(10, total_moves)  # Default opening length
            middlegame_start = opening_end
            endgame_start = total_moves * 2 // 3

            # Track material count
            material_count = 32  # Starting position
            for i, move in enumerate(moves):
                # Update material count if available
                if 'material_count' in move:
                    material_count = float(str(move['material_count']))
                
                # Detect opening end based on multiple factors
                if i < total_moves // 3:
                    if (material_count < 28 or  # Significant material exchange
                        bool(move.get('is_tactical', False)) or  # Tactical play started
                        i >= 10):  # Hard limit on opening
                        opening_end = i
                        middlegame_start = i
                        break

                # Detect endgame start
                if i > total_moves // 2:
                    if material_count < 20:  # Clear endgame material situation
                        endgame_start = i
                        break

            return {
                'opening': opening_end,
                'middlegame': endgame_start
            }
        except Exception as e:
            logger.error(f"Error detecting phase transitions: {str(e)}")
            # Fallback to simple division
            third = total_moves // 3
            return {
                'opening': third,
                'middlegame': third * 2
            }

    @staticmethod
    def _validate_evaluation(eval_value: float, move_number: int, phase: str) -> float:
        """Validate evaluation values with context awareness."""
        try:
            # Check for suspicious values
            if abs(eval_value) > 2000:  # Unrealistic evaluation
                return 0.0
            
            # Validate based on game phase
            if phase == 'opening' and abs(eval_value) > 300:
                return math.copysign(300, eval_value)
            
            if phase == 'endgame' and abs(eval_value) > 1000:
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
                'average_time': 0.0,
                'time_pressure_moves': 0,
                'time_pressure_percentage': 0.0,
                'time_variance': 0.0,
                'time_management_score': 0.0,
                'normalized_times': [],
                'remaining_time': 0.0
            }
        
        # Validate input parameters
        total_time = max(1.0, float(total_time))  # Ensure minimum total time
        increment = max(0.0, float(increment))     # No negative increments
        
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
        pressure_moves = sum(1 for t, thresh in zip(cleaned_times, pressure_thresholds) 
                            if t <= thresh)
        pressure_percentage = (pressure_moves / len(cleaned_times)) * 100
        
        # Enhanced time management score calculation
        time_management_score = 0.0
        
        # Factor 1: Time usage consistency (35%)
        normalized_variance = min(1.0, variance / (expected_time_per_move ** 2))
        consistency_score = 1.0 - normalized_variance
        
        # Factor 2: Appropriate time usage (35%)
        time_usage_ratio = sum(cleaned_times) / total_time
        appropriate_usage = 1.0 - abs(0.5 - time_usage_ratio)  # Optimal ratio around 0.5
        
        # Factor 3: Time pressure handling (30%)
        pressure_handling = 1.0 - (pressure_percentage / 100)
        
        # Calculate final score with increment bonus
        increment_bonus = 0.1 if increment > 0 else 0.0  # Small bonus for increment time control
        
        time_management_score = (
            (consistency_score * 0.35) +
            (appropriate_usage * 0.35) +
            (pressure_handling * 0.30) +
            increment_bonus
        )
        
        # Normalize final score to 0-1 range
        time_management_score = min(1.0, max(0.0, time_management_score))
        
        return {
            'average_time': round(avg_time, 2),
            'time_pressure_moves': pressure_moves,
            'time_pressure_percentage': round(pressure_percentage, 2),
            'time_variance': round(variance, 2),
            'time_management_score': round(time_management_score, 3),
            'normalized_times': cleaned_times,
            'remaining_time': round(remaining_time, 2)
        }

    @staticmethod
    def _calculate_time_metrics(moves: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comprehensive time management metrics."""
        if not moves:
            return {
                'average_time': 0.0,
                'time_variance': 0.0,
                'time_consistency': 0.0,
                'time_pressure_moves': 0,
                'time_management_score': 0.0,
                'time_pressure_percentage': 0.0
            }

        try:
            # Extract time data
            time_spent = []
            total_time = 0.0
            
            for move in moves:
                spent = move.get('time_spent', 0)
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
            time_variations = [abs(t - avg_time) / max(1.0, avg_time) for t in time_spent]
            time_consistency = 100.0 * (1.0 - min(1.0, sum(time_variations) / len(moves)))
            
            # Calculate time management score
            base_score = 100.0
            
            # Deduct for time pressure
            pressure_penalty = (time_pressure_percentage / 100) * 30  # Up to 30 points
            
            # Deduct for inconsistency
            consistency_penalty = (1 - (time_consistency / 100)) * 40  # Up to 40 points
            
            # Deduct for extreme variance
            variance_penalty = min(30, (time_variance / (avg_time ** 2)) * 30)  # Up to 30 points
            
            time_management_score = max(0, min(100, base_score - pressure_penalty - consistency_penalty - variance_penalty))
            
            return {
                'average_time': round(avg_time, 1),
                'time_variance': round(time_variance, 1),
                'time_consistency': round(time_consistency, 1),
                'time_pressure_moves': time_pressure_moves,
                'time_management_score': round(time_management_score, 1),
                'time_pressure_percentage': round(time_pressure_percentage, 1)
            }
            
        except Exception as e:
            logger.error(f"Error calculating time metrics: {str(e)}")
            return MetricsCalculator._get_default_time_metrics()

    @staticmethod
    def _calculate_phase_time_metrics(moves: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate time metrics for a specific game phase."""
        if not moves:
            return {
                'average_time': 0.0,
                'time_pressure_percentage': 0.0,
                'time_consistency': 0.0
            }
        
        try:
            time_spent = [float(m.get('time_spent', 0)) for m in moves]
            avg_time = statistics.mean(time_spent)
            
            # Calculate time pressure
            pressure_threshold = avg_time * 0.3
            pressure_moves = int(sum(1 for t in time_spent if t < pressure_threshold))
            pressure_percentage = (pressure_moves / len(moves) * 100.0)
            
            # Calculate consistency
            variations = [abs(t - avg_time) / max(1.0, avg_time) for t in time_spent]
            consistency = 100.0 * (1.0 - min(1.0, sum(variations) / len(moves)))
            
            return {
                'average_time': round(avg_time, 2),
                'time_pressure_percentage': round(pressure_percentage, 1),
                'time_consistency': round(consistency, 1)
            }
            
        except Exception as e:
            logger.error(f"Error calculating phase time metrics: {str(e)}")
            return {
                'average_time': 0.0,
                'time_pressure_percentage': 0.0,
                'time_consistency': 0.0
            }

    @staticmethod
    def _calculate_time_management_score(
        time_spent: List[float],
        time_pressure_percentage: float,
        time_consistency: float,
        critical_time_ratio: float,
        phase_times: Dict[str, Dict[str, float]]
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
            opening_time = phase_times['opening']['average_time']
            endgame_time = phase_times['endgame']['average_time']
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
                    eval_improvement_val = move.get('evaluation_improvement')
                    if eval_improvement_val is None:
                        continue
                        
                    try:
                        eval_improvement = float(str(eval_improvement_val))
                    except (ValueError, TypeError):
                        continue
                    
                    # Get position metrics if available
                    position_metrics = cast(Dict[str, Any], move.get('position_metrics', {}))
                    position_quality = float(str(position_metrics.get('position_quality', '50.0')))
                    piece_activity = float(str(position_metrics.get('piece_activity', '50.0')))
                    
                    # Calculate complexity based on position metrics
                    complexity_factors = [
                        position_quality,
                        piece_activity,
                        float(str(position_metrics.get('king_safety', '50.0'))),
                        float(str(position_metrics.get('pawn_structure', '50.0')))
                    ]
                    position_complexity = sum(complexity_factors) / len(complexity_factors)
                    
                    is_critical = bool(move.get('is_critical', False))
                    
                    # Weight based on position complexity and critical moments
                    weight = 1.0
                    if is_critical:
                        weight *= 1.5  # Critical positions have higher weight
                    weight *= (0.5 + position_complexity / 100.0)  # More complex positions have higher weight
                    
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
            return 0.0

        try:
            # Initialize tracking variables
            good_move_streaks = []
            current_good_streak = 0
            mistake_clusters = []
            mistakes_in_window = 0
            window_size = 5  # Look for mistake clusters in 5-move windows
            
            # Base score starts at 100, will be adjusted based on performance
            base_score = 100
            
            for i, move in enumerate(moves):
                # Track good move streaks
                if not any([
                    move.get('is_mistake', False),
                    move.get('is_blunder', False),
                    move.get('evaluation_drop', 0) > 100
                ]):
                    current_good_streak += 1
                else:
                    if current_good_streak >= 3:  # Only count significant streaks
                        good_move_streaks.append(current_good_streak)
                    current_good_streak = 0
                
                # Track mistake clusters in rolling window
                if any([move.get('is_mistake', False), move.get('is_blunder', False)]):
                    mistakes_in_window = int(mistakes_in_window + 1)
                
                # Update mistake clusters when window is full
                if i >= window_size - 1:
                    if mistakes_in_window >= 2:  # Two or more mistakes in window is a cluster
                        mistake_clusters.append(mistakes_in_window)
                    if i - window_size + 1 >= 0:
                        # Remove oldest mistake from window
                        old_move = moves[i - window_size + 1]
                        if any([old_move.get('is_mistake', False), old_move.get('is_blunder', False)]):
                            mistakes_in_window = int(mistakes_in_window - 1)
            
            # Add final good streak if it exists
            if current_good_streak >= 3:
                good_move_streaks.append(current_good_streak)
            
            # Calculate deductions for mistakes and blunders
            mistake_penalty = sum(1 for m in moves if m.get('is_mistake', False)) * 3
            blunder_penalty = sum(1 for m in moves if m.get('is_blunder', False)) * 8
            
            # Calculate bonus for good move streaks
            streak_bonus = sum(min(streak * 2, 15) for streak in good_move_streaks)  # Cap bonus at 15 points per streak
            
            # Penalize for mistake clusters (more than pattern of isolated mistakes)
            cluster_penalty = sum(cluster * 2 for cluster in mistake_clusters)
            
            # Calculate time consistency if time data is available
            time_consistency = 0
            if any(move.get('time_spent') is not None for move in moves):
                times = [move.get('time_spent', 0) for move in moves]
                avg_time = sum(times) / len(times)
                time_variations = [abs(t - avg_time) / avg_time for t in times if avg_time > 0]
                time_consistency = 10 * (1 - min(1, sum(time_variations) / len(moves)))
            
            # Calculate final score
            final_score = (
                base_score
                - mistake_penalty
                - blunder_penalty
                - cluster_penalty
                + streak_bonus
                + time_consistency
            )
            
            return max(0, min(100, final_score))

        except Exception as e:
            logger.error(f"Error calculating consistency: {str(e)}")
            return 0.0

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
                if move.get('is_tactical', False):
                    tactical_positions.append({
                        'move': move,
                        'features': move.get('tactical_features', []),
                        'evaluation': float(str(move.get('evaluation', '0.0')))
                    })
                    total_positions += 1
            
            # Second pass: analyze tactical positions
            for i, tpos in enumerate(tactical_positions):
                move = cast(Dict[str, Any], tpos['move'])
                try:
                    improvement_val = move.get('evaluation_improvement')
                    eval_improvement = float(str(improvement_val)) if improvement_val is not None else 0.0
                except (ValueError, TypeError):
                    eval_improvement = 0.0
                
                # Success calculation with normalized scoring
                if (eval_improvement > 0 if is_white else eval_improvement < 0):
                    success_weight = 1.0
                    
                    # Weight based on features with normalized values
                    features = cast(List[str], tpos['features'])
                    if 'check' in features:
                        success_weight *= 1.1  # Reduced from 1.2
                    if 'material' in features:
                        success_weight *= 1.05  # Reduced from 1.1
                    if 'complex_position' in features:
                        success_weight *= 1.15  # Reduced from 1.3
                    
                    successful += success_weight
                    
                    # Identify brilliant moves with normalized threshold
                    if abs(eval_improvement) > 200 and len(features) >= 2:  # Reduced from 300
                        brilliant_moves += 1
                
                # Pattern recognition with normalized scoring
                if i > 0:
                    prev_pos = tactical_positions[i-1]
                    try:
                        prev_improvement_val = prev_pos['move'].get('evaluation_improvement')
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
                'total_positions': total_positions,
                'success_rate': float(success_rate),
                'pattern_recognition': float(pattern_recognition),
                'brilliant_moves': brilliant_moves,
                'normalized_score': float((success_rate + pattern_recognition) / 2.0)
            }
            
        except Exception as e:
            logger.error(f"Error calculating phase metrics: {str(e)}")
            return {
                'total_positions': 0,
                'success_rate': 0.0,
                'pattern_recognition': 0.0,
                'brilliant_moves': 0,
                'normalized_score': 0.0
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
                    material_val = move.get('material_change')
                    material_change = float(str(material_val)) if material_val is not None else 0.0
                    if abs(material_change) >= 1:  # At least a pawn worth
                        is_tactical = True
                        tactical_features.append('material')
                except (ValueError, TypeError):
                    material_change = 0.0
                
                # Check for check/checkmate
                if move.get('is_check', False):
                    is_tactical = True
                    tactical_features.append('check')
                
                # Check for significant position improvement
                try:
                    improvement_val = move.get('evaluation_improvement')
                    eval_improvement = float(str(improvement_val)) if improvement_val is not None else 0.0
                    if abs(eval_improvement) > 200:  # 2 pawns worth
                        is_tactical = True
                        tactical_features.append('position_improvement')
                except (ValueError, TypeError):
                    eval_improvement = 0.0
                
                # Check for piece activity increase
                try:
                    activity_val = move.get('piece_activity_change')
                    activity_change = float(str(activity_val)) if activity_val is not None else 0.0
                    if activity_change > 0.3:
                        is_tactical = True
                        tactical_features.append('piece_activity')
                except (ValueError, TypeError):
                    activity_change = 0.0
                
                # Consider position complexity
                try:
                    complexity_val = move.get('position_complexity')
                    complexity = float(str(complexity_val)) if complexity_val is not None else 0.5
                    if complexity > 0.7:  # High complexity positions more likely tactical
                        is_tactical = True
                        tactical_features.append('complex_position')
                except (ValueError, TypeError):
                    complexity = 0.5
                
                if is_tactical:
                    tactical_positions.append({
                        'move': move,
                        'features': tactical_features,
                        'complexity': complexity,
                        'eval_improvement': eval_improvement
                    })
            
            opportunities = len(tactical_positions)
            
            # Second pass: analyze tactical positions
            for i, tpos in enumerate(tactical_positions):
                move = tpos['move']
                try:
                    improvement_val = move.get('evaluation_improvement')
                    eval_improvement = float(str(improvement_val)) if improvement_val is not None else 0.0
                except (ValueError, TypeError):
                    eval_improvement = 0.0
                
                # Success calculation
                if (eval_improvement > 0 if is_white else eval_improvement < 0):
                    success_weight = 1.0
                    
                    # Weight based on features
                    if 'check' in tpos['features']:
                        success_weight *= 1.2
                    if 'material' in tpos['features']:
                        success_weight *= 1.1
                    if 'complex_position' in tpos['features']:
                        success_weight *= 1.3
                    
                    successful += success_weight
                    
                    # Identify brilliant moves
                    if abs(eval_improvement) > 300 and len(tpos['features']) >= 2:
                        brilliant_moves += 1
                
                # Pattern recognition
                if i > 0:
                    prev_pos = tactical_positions[i-1]
                    try:
                        prev_improvement_val = prev_pos['move'].get('evaluation_improvement')
                        prev_eval = float(str(prev_improvement_val)) if prev_improvement_val is not None else 0.0
                        if (abs(prev_eval) > 100 and abs(eval_improvement) > 100):
                            pattern_scores.append(100.0)
                        elif (abs(prev_eval) > 50 and abs(eval_improvement) > 50):
                            pattern_scores.append(50.0)
                    except (ValueError, TypeError):
                        continue
            
            # Calculate metrics
            success_rate = (successful / max(1, opportunities) * 100.0)
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
                'opportunities': opportunities,
                'successful': round(successful, 1),
                'brilliant_moves': brilliant_moves,
                'missed': missed_opportunities,
                'success_rate': round(success_rate, 1),
                'pattern_recognition': round(pattern_recognition, 1),
                'tactical_score': round(tactical_score, 1)
            }
            
        except Exception as e:
            logger.error(f"Error calculating tactical metrics: {str(e)}")
            return MetricsCalculator._get_default_tactical_metrics()

    @staticmethod
    def _get_default_tactical_metrics() -> Dict[str, Any]:
        """Return default tactical metrics."""
        return {
            'opportunities': 0,
            'successful': 0,
            'brilliant_moves': 0,
            'missed': 0,
            'success_rate': 0.0,
            'pattern_recognition': 0.0,
            'tactical_score': 0.0
        }

    @staticmethod
    def _calculate_advantage_metrics(moves: List[Dict[str, Any]], is_white: bool) -> Dict[str, Any]:
        """Calculate metrics related to advantage maintenance and conversion."""
        if not moves:
            return {
                'max_advantage': 0.0,
                'min_advantage': 0.0,
                'average_advantage': 0.0,
                'advantage_conversion': 0.0,
                'pressure_handling': 0.0,
                'advantage_duration': 0,
                'winning_positions': 0,
                'advantage_retention': 0.0,
                'advantage_trend': 0.0
            }

        try:
            # Track advantage throughout the game
            advantages: List[float] = []
            winning_positions = 0
            advantage_retention = 0
            
            for i, move in enumerate(moves):
                try:
                    eval_after = float(str(move.get('eval_after', '0.0')))
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
                            next_eval = float(str(moves[i + 1].get('eval_after', '0.0')))
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
            converted_positions = sum(1 for i in range(len(advantages) - 1)
                                   if advantages[i] > 200.0 and advantages[i + 1] >= advantages[i])
            
            conversion_rate = (converted_positions / max(1, advantage_positions) * 100.0)
            retention_rate = (advantage_retention / max(1, winning_positions) * 100.0)
            
            # Calculate pressure handling with validation
            pressure_positions = sum(1 for a in advantages if a < -150.0)
            good_defenses = sum(1 for i in range(len(advantages) - 1)
                              if advantages[i] < -150.0 and advantages[i + 1] > advantages[i])
            
            pressure_score = (good_defenses / max(1, pressure_positions) * 100.0)
            
            # Calculate advantage trend with validation
            advantage_trend: float = 0.0
            if len(advantages) > 5:
                early_avg = statistics.mean(advantages[:len(advantages)//3])
                late_avg = statistics.mean(advantages[-len(advantages)//3:])
                advantage_trend = late_avg - early_avg
            
            return {
                'max_advantage': round(max_advantage / 100.0, 2),  # Convert to pawn units
                'min_advantage': round(min_advantage / 100.0, 2),
                'average_advantage': round(avg_advantage / 100.0, 2),
                'advantage_conversion': round(conversion_rate, 1),
                'pressure_handling': round(pressure_score, 1),
                'advantage_duration': advantage_positions,
                'winning_positions': winning_positions,
                'advantage_retention': round(retention_rate, 1),
                'advantage_trend': round(advantage_trend / 100.0, 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating advantage metrics: {str(e)}")
            return {
                'max_advantage': 0.0,
                'min_advantage': 0.0,
                'average_advantage': 0.0,
                'advantage_conversion': 0.0,
                'pressure_handling': 0.0,
                'advantage_duration': 0,
                'winning_positions': 0,
                'advantage_retention': 0.0,
                'advantage_trend': 0.0
            }

    @staticmethod
    def _calculate_resourcefulness_metrics(moves: List[Dict[str, Any]], is_white: bool) -> Dict[str, Any]:
        """Calculate metrics related to resourcefulness and finding best moves under pressure."""
        if not moves:
            return {
                'recovery_rate': 0.0,
                'defensive_score': 0.0,
                'critical_defense': 0.0,
                'tactical_defense': 0.0,
                'best_move_finding': 0.0,
                'position_recovery': 0.0,
                'comeback_potential': 0.0,
                'critical_defense_score': 0.0,
                'defensive_resourcefulness': 0.0
            }

        try:
            # Track critical positions and responses
            critical_positions: List[Dict[str, Any]] = []
            defensive_scores: List[float] = []
            recovery_positions: List[float] = []
            tactical_defenses: List[float] = []
            
            for i, move in enumerate(moves):
                try:
                    eval_before = float(str(move.get('eval_before', '0.0')))
                    eval_after = float(str(move.get('eval_after', '0.0')))
                except (ValueError, TypeError):
                    eval_before = 0.0
                    eval_after = 0.0
                    
                # Adjust evaluations based on color
                eval_before = eval_before if is_white else -eval_before
                eval_after = eval_after if is_white else -eval_after
                
                # Identify critical positions
                is_critical = (
                    bool(move.get('is_critical', False)) or
                    eval_before < -150.0 or  # Bad position
                    bool(move.get('in_check', False)) or  # Under check
                    bool(move.get('under_attack', False))  # Piece under attack
                )
                
                if is_critical:
                    critical_positions.append({
                        'position': move,
                        'eval_before': eval_before,
                        'eval_after': eval_after,
                        'improvement': float(eval_after - eval_before)
                    })
                    
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
                if bool(move.get('is_tactical', False)) and eval_before < -100.0:
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
            critical_defense = sum(1 for pos in critical_positions if float(pos['improvement']) > 0.0)
            critical_defense_rate = (critical_defense / total_critical * 100.0) if total_critical > 0 else 0.0
            
            # Calculate tactical defense
            tactical_defense_score = statistics.mean(tactical_defenses) if tactical_defenses else 0.0
            
            # Calculate best move finding
            best_moves = sum(1 for m in moves if bool(m.get('is_critical', False)) and bool(m.get('is_best', False)))
            best_move_rate = (best_moves / total_critical * 100.0) if total_critical > 0 else 0.0
            
            # Calculate position recovery
            position_recovery = statistics.mean(recovery_positions) if recovery_positions else 0.0
            
            # Calculate comeback potential
            worst_eval = min((float(pos['eval_before']) for pos in critical_positions), default=0.0)
            final_eval = float(str(moves[-1].get('eval_after', '0.0'))) if moves else 0.0
            comeback_potential = min(100.0, max(0.0, (final_eval - worst_eval) / 4.0)) if worst_eval < -200.0 else 0.0
            
            return {
                'recovery_rate': round(recovery_rate, 1),
                'defensive_score': round(defensive_score, 1),
                'critical_defense': round(critical_defense_rate, 1),
                'tactical_defense': round(tactical_defense_score, 1),
                'best_move_finding': round(best_move_rate, 1),
                'position_recovery': round(position_recovery, 1),
                'comeback_potential': round(comeback_potential, 1),
                'critical_defense_score': round(critical_defense_rate, 1),
                'defensive_resourcefulness': round((defensive_score + critical_defense_rate) / 2.0, 1)
            }
            
        except Exception as e:
            logger.error(f"Error calculating resourcefulness metrics: {str(e)}")
            return {
                'recovery_rate': 0.0,
                'defensive_score': 0.0,
                'critical_defense': 0.0,
                'tactical_defense': 0.0,
                'best_move_finding': 0.0,
                'position_recovery': 0.0,
                'comeback_potential': 0.0,
                'critical_defense_score': 0.0,
                'defensive_resourcefulness': 0.0
            }

    @staticmethod
    def _calculate_overall_metrics(moves: List[Dict[str, Any]], is_white: bool) -> Dict[str, Any]:
        """Calculate overall game metrics with enhanced validation."""
        try:
            total_moves = len(moves)
            mistakes = sum(1 for m in moves if m.get('is_mistake', False))
            blunders = sum(1 for m in moves if m.get('is_blunder', False))
            inaccuracies = sum(1 for m in moves if m.get('evaluation_drop', 0) > 100)
            quality_moves = sum(1 for m in moves if m.get('evaluation_improvement', 0) > 50)
            
            # Calculate overall accuracy with perspective
            accuracy = MetricsCalculator._calculate_accuracy(moves)
            consistency = MetricsCalculator._calculate_consistency(moves)
            
            # Calculate critical positions
            critical_positions = sum(1 for m in moves if m.get('is_critical', False))
            
            # Calculate average position quality
            position_quality = statistics.mean([
                m.get('position_complexity', 0.5) * 
                (1 - abs(m.get('eval_after', 0)) / 1000)  # Normalize evaluation
                for m in moves
            ]) if moves else 0.0
            
            return {
                'total_moves': total_moves,
                'accuracy': round(accuracy, 1),
                'consistency_score': round(consistency, 1),
                'mistakes': mistakes,
                'blunders': blunders,
                'inaccuracies': inaccuracies,
                'quality_moves': quality_moves,
                'critical_positions': critical_positions,
                'position_quality': round(position_quality * 100, 1)  # Convert to percentage
            }
        except Exception as e:
            logger.error(f"Error calculating overall metrics: {str(e)}")
            return MetricsCalculator._get_default_overall_metrics()

    @staticmethod
    def _get_default_overall_metrics() -> Dict[str, Any]:
        """Return default overall metrics."""
        return {
            'total_moves': 0,
            'accuracy': 0.0,
            'consistency_score': 0.0,
            'mistakes': 0,
            'blunders': 0,
            'inaccuracies': 0,
            'quality_moves': 0,
            'critical_positions': 0,
            'position_quality': 0.0
            }

    @staticmethod
    def _validate_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize all metrics to ensure they are within reasonable ranges."""
        try:
            # Validate time metrics
            if 'time_management' in metrics:
                time_metrics = metrics['time_management']
                time_metrics['average_time'] = max(0, min(3600, time_metrics.get('average_time', 0)))
                time_metrics['time_pressure_percentage'] = max(0, min(100, time_metrics.get('time_pressure_percentage', 0)))
                time_metrics['time_consistency'] = max(0, min(100, time_metrics.get('time_consistency', 0)))
                time_metrics['time_management_score'] = max(0, min(100, time_metrics.get('time_management_score', 0)))

            # Validate tactical metrics
            if 'tactics' in metrics:
                tactical_metrics = metrics['tactics']
                tactical_metrics['opportunities'] = max(0, tactical_metrics.get('opportunities', 0))
                tactical_metrics['successful'] = max(0, min(tactical_metrics.get('successful', 0), tactical_metrics.get('opportunities', 0)))
                tactical_metrics['success_rate'] = max(0, min(100, tactical_metrics.get('success_rate', 0)))
                tactical_metrics['tactical_score'] = max(0, min(100, tactical_metrics.get('tactical_score', 0)))

            # Validate advantage metrics
            if 'advantage' in metrics:
                advantage_metrics = metrics['advantage']
                advantage_metrics['max_advantage'] = max(-2000, min(2000, advantage_metrics.get('max_advantage', 0)))
                advantage_metrics['average_advantage'] = max(-2000, min(2000, advantage_metrics.get('average_advantage', 0)))
                advantage_metrics['conversion_rate'] = max(0, min(100, advantage_metrics.get('conversion_rate', 0)))
                advantage_metrics['advantage_retention'] = max(0, min(100, advantage_metrics.get('advantage_retention', 0)))

            # Validate phase metrics
            if 'phases' in metrics:
                for phase in metrics['phases'].values():
                    if phase:
                        phase['accuracy'] = max(0, min(100, phase.get('accuracy', 0)))
                        phase['moves_count'] = max(0, phase.get('moves_count', 0))
                        if 'time_management' in phase:
                            phase['time_management']['average_time'] = max(0, min(3600, phase['time_management'].get('average_time', 0)))
                            phase['time_management']['time_pressure_percentage'] = max(0, min(100, phase['time_management'].get('time_pressure_percentage', 0)))

            # Validate resourcefulness metrics
            if 'resourcefulness' in metrics:
                resourcefulness_metrics = metrics['resourcefulness']
                resourcefulness_metrics['defensive_score'] = max(0, min(100, resourcefulness_metrics.get('defensive_score', 0)))
                resourcefulness_metrics['counter_play'] = max(0, min(100, resourcefulness_metrics.get('counter_play', 0)))
                resourcefulness_metrics['recovery_rate'] = max(0, min(100, resourcefulness_metrics.get('recovery_rate', 0)))
                resourcefulness_metrics['critical_defense'] = max(0, min(100, resourcefulness_metrics.get('critical_defense', 0)))
                resourcefulness_metrics['best_move_finding'] = max(0, min(100, resourcefulness_metrics.get('best_move_finding', 0)))

            return metrics
        except Exception as e:
            logger.error(f"Error validating metrics: {str(e)}")
            return metrics  # Return original metrics if validation fails

    @staticmethod
    def _get_default_metrics() -> Dict[str, Any]:
        """Return default metrics structure matching frontend requirements."""
        default_time_management = {
            'average_time': 0.0,
            'time_variance': 0.0,
            'time_consistency': 0.0,
            'time_pressure_moves': 0,
            'time_management_score': 0.0,
            'time_pressure_percentage': 0.0
        }

        return {
            'overall': {
                'accuracy': 0.0,
                'consistency': 0.0,
                'mistakes': 0,
                'blunders': 0,
                'inaccuracies': 0,
                'quality_moves': 0,
                'critical_positions': 0,
                'position_quality': 0.0
            },
            'phases': {
                'opening': {
                    'accuracy': 0.0,
                    'moves': [],
                    'mistakes': 0,
                    'blunders': 0,
                    'critical_moves': 0,
                    'time_management': default_time_management.copy()
                },
                'middlegame': {
                    'accuracy': 0.0,
                    'moves': [],
                    'mistakes': 0,
                    'blunders': 0,
                    'critical_moves': 0,
                    'time_management': default_time_management.copy()
                },
                'endgame': {
                    'accuracy': 0.0,
                    'moves': [],
                    'mistakes': 0,
                    'blunders': 0,
                    'critical_moves': 0,
                    'time_management': default_time_management.copy()
                }
            },
            'tactics': {
                'opportunities': 0,
                'successful': 0,
                'brilliant_moves': 0,
                'missed': 0,
                'success_rate': 0.0,
                'pattern_recognition': 0.0,
                'tactical_score': 0.0
            },
            'time_management': default_time_management.copy(),
            'advantage': {
                'max_advantage': 0.0,
                'min_advantage': 0.0,
                'average_advantage': 0.0,
                'advantage_conversion': 0.0,
                'pressure_handling': 0.0,
                'advantage_duration': 0,
                'winning_positions': 0,
                'advantage_retention': 0.0,
                'advantage_trend': 0.0
            },
            'resourcefulness': {
                'recovery_rate': 0.0,
                'defensive_score': 0.0,
                'critical_defense': 0.0,
                'tactical_defense': 0.0,
                'best_move_finding': 0.0,
                'position_recovery': 0.0,
                'comeback_potential': 0.0,
                'critical_defense_score': 0.0,
                'defensive_resourcefulness': 0.0
            }
        }

    def __init__(self):
        """Initialize the metrics calculator."""
        pass