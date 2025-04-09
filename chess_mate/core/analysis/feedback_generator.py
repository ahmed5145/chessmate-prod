"""
Feedback generator for chess games.
Handles generation of game feedback using OpenAI API.
"""

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from openai import OpenAI

from ..cache import CACHE_BACKEND_REDIS, cache_delete, cache_get, cache_set
from ..error_handling import (
    ExternalServiceError,
    ResourceNotFoundError,
    TaskError,
    ValidationError,
)
from ..models import Game

logger = logging.getLogger(__name__)


class FeedbackGenerator:
    """Generates feedback for chess games using OpenAI."""

    def __init__(self):
        """Initialize the feedback generator."""
        self.openai_client = None
        self._initialize_openai()

    def _initialize_openai(self) -> None:
        """Initialize OpenAI client."""
        try:
            if not hasattr(settings, "OPENAI_API_KEY") or not settings.OPENAI_API_KEY:
                logger.warning("OpenAI API key not found in settings")
                self.openai_client = None
                return

                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {str(e)}")
            self.openai_client = None

    def generate_feedback(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate feedback based on analysis results."""
        try:
            # Validate metrics
            if not analysis_result.get('metrics') or not analysis_result['metrics'].get('summary'):
                logger.warning("Invalid metrics provided, using statistical feedback")
                return self._generate_statistical_feedback(analysis_result)
                
            metrics = analysis_result['metrics']['summary']
            
            # Generate feedback for each phase
            opening_feedback = self._generate_opening_feedback(metrics['phases']['opening'])
            middlegame_feedback = self._generate_middlegame_feedback(metrics['phases']['middlegame'])
            endgame_feedback = self._generate_endgame_feedback(metrics['phases']['endgame'])
            
            # Identify strengths and weaknesses
            strengths = self._identify_strengths(metrics)
            weaknesses = self._identify_weaknesses(metrics)
            
            # Find critical moments
            critical_moments = self._find_critical_moments(analysis_result['moves'])
            
            # Generate improvement areas
            improvement_areas = self._generate_improvement_areas(metrics, weaknesses)
            
            return {
                'source': 'ai',
                'strengths': strengths,
                'weaknesses': weaknesses,
                'critical_moments': critical_moments,
                'improvement_areas': improvement_areas,
                'opening': opening_feedback,
                'middlegame': middlegame_feedback,
                'endgame': endgame_feedback,
                'metrics': metrics
            }

        except Exception as e:
            logger.error(f"Error generating feedback: {str(e)}")
            return self._generate_statistical_feedback(analysis_result)
            
    def _generate_statistical_feedback(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic statistical feedback when AI feedback generation fails."""
        moves = analysis_result.get('moves', [])
        if not moves:
            return {
                'source': 'statistical',
                'strengths': [],
                'weaknesses': ['No moves available for analysis'],
                'critical_moments': [],
                'improvement_areas': ['Game data incomplete'],
                'opening': {'feedback': 'Insufficient data for opening analysis'},
                'middlegame': {'feedback': 'Insufficient data for middlegame analysis'},
                'endgame': {'feedback': 'Insufficient data for endgame analysis'},
                'metrics': {'summary': {'overall': {'accuracy': 0.0, 'consistency': 0.0}}}
            }
            
        # Basic statistical analysis
        total_moves = len(moves)
        good_moves = sum(1 for m in moves if m.get('classification') in ['good', 'excellent'])
        mistakes = sum(1 for m in moves if m.get('classification') in ['mistake', 'blunder'])
        
        accuracy = (good_moves / total_moves * 100) if total_moves > 0 else 0.0
        
        return {
            'source': 'statistical',
            'strengths': [f'Made {good_moves} good moves'] if good_moves > 0 else [],
            'weaknesses': [f'Made {mistakes} mistakes'] if mistakes > 0 else ['No major mistakes detected'],
            'critical_moments': self._find_critical_moments(moves),
            'improvement_areas': [
                f'Improve accuracy (current: {accuracy:.1f}%)',
                'Focus on consistent move quality'
            ],
            'opening': {'feedback': f'Opening phase: {self._analyze_phase(moves[:10])}'},
            'middlegame': {'feedback': f'Middlegame phase: {self._analyze_phase(moves[10:-10])}'},
            'endgame': {'feedback': f'Endgame phase: {self._analyze_phase(moves[-10:])}'},
            'metrics': {
                'summary': {
                    'overall': {
                        'accuracy': accuracy,
                        'consistency': self._calculate_consistency(moves),
                        'total_moves': total_moves,
                        'mistakes': mistakes
                    }
                }
            }
        }
        
    def _analyze_phase(self, moves: List[Dict[str, Any]]) -> str:
        """Analyze a specific phase of the game."""
        if not moves:
            return "No moves in this phase"
            
        good_moves = sum(1 for m in moves if m.get('classification') in ['good', 'excellent'])
        mistakes = sum(1 for m in moves if m.get('classification') in ['mistake', 'blunder'])
        accuracy = (good_moves / len(moves) * 100) if moves else 0.0
        
        return f"Accuracy: {accuracy:.1f}%, Good moves: {good_moves}, Mistakes: {mistakes}"
        
    def _calculate_consistency(self, moves: List[Dict[str, Any]]) -> float:
        """Calculate basic consistency score."""
        if not moves:
            return 100.0
            
        streak_lengths = []
        current_streak = 0
        
        for move in moves:
            if move.get('classification') in ['good', 'excellent']:
                current_streak += 1
            else:
                if current_streak > 0:
                    streak_lengths.append(current_streak)
                current_streak = 0
                
        if current_streak > 0:
            streak_lengths.append(current_streak)
            
        avg_streak = sum(streak_lengths) / len(streak_lengths) if streak_lengths else 0
        return min(100.0, (avg_streak / 5.0) * 100.0)  # Normalize to 5-move streaks

    def _validate_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Validate that the metrics contain required data."""
        try:
            # Check if we have the basic structure
            if not isinstance(metrics, dict):
                logger.warning("Metrics is not a dictionary")
                return False

            # Handle both nested and unnested structures
            if "analysis_results" in metrics:
                metrics = metrics["analysis_results"]

            # Handle summary wrapper
            if "summary" in metrics:
                summary = metrics["summary"]
            else:
                summary = metrics

            # Get moves from either top level or nested
            moves = metrics.get("moves", []) or summary.get("moves", [])
            has_moves = bool(moves)

            # Get overall metrics
            overall = summary.get("overall", {})
            if not overall and isinstance(summary.get("summary", {}), dict):
                overall = summary["summary"].get("overall", {})

            # More lenient validation
            has_accuracy = overall.get("accuracy", 0) >= 0  # Allow 0 accuracy
            has_moves_count = overall.get("total_moves", 0) > 0 or len(moves) > 0
            has_any_metrics = any(
                overall.get(key, 0) >= 0  # Allow 0 values
                for key in ["mistakes", "blunders", "inaccuracies", "time_management_score"]
            )

            # Consider valid if we have moves and any metrics
            is_valid = has_moves and (has_accuracy or has_any_metrics)

            if not is_valid:
                logger.warning(
                    f"Metrics validation failed: has_moves={has_moves}, accuracy={has_accuracy}, other_metrics={has_any_metrics}"
                )
                logger.debug(f"Overall metrics: {overall}")
                logger.debug(f"Moves count: {len(moves)}")
                logger.debug(f"Metrics structure: {list(metrics.keys())}")
            else:
                logger.info("Metrics validation passed successfully")

            return is_valid

        except Exception as e:
            logger.error(f"Error validating metrics: {str(e)}")
            logger.debug(f"Metrics that caused error: {metrics}")
            return False

    def _generate_analysis_prompt(self, game_metrics: Dict[str, Any]) -> str:
        """Generate a detailed prompt for AI analysis."""
        try:
            # Extract and validate metrics
            overall = game_metrics.get("overall", {})
            phases = game_metrics.get("phases", {})
            tactics = game_metrics.get("tactics", {})
            time_mgmt = game_metrics.get("time_management", {})

            prompt_data = {
                "game_metrics": {
                    "total_moves": overall.get("total_moves", 0),
                    "accuracy": overall.get("accuracy", 0),
                    "mistakes": overall.get("mistakes", 0),
                    "blunders": overall.get("blunders", 0),
                    "average_centipawn_loss": overall.get("average_centipawn_loss", 0),
                    "time_management": {
                        "time_pressure_moves": time_mgmt.get("time_pressure_moves", 0),
                        "average_time": time_mgmt.get("average_time", 0),
                        "time_management_score": time_mgmt.get("time_management_score", 0),
                    },
                    "tactics": {
                        "opportunities": tactics.get("opportunities", 0),
                        "successful": tactics.get("successful", 0),
                        "tactical_score": tactics.get("tactical_score", 0),
                    },
                    "phases": {
                        "opening": phases.get("opening", {}),
                        "middlegame": phases.get("middlegame", {}),
                        "endgame": phases.get("endgame", {}),
                    },
                }
            }

            return f"""Analyze these chess game metrics and provide detailed feedback in JSON format:

            Game metrics: {json.dumps(prompt_data, indent=2)}

            Provide analysis in this exact JSON structure:
            {{
                "feedback": {{
                    "source": "openai",
                    "strengths": ["list of specific strengths based on the metrics"],
                    "weaknesses": ["list of specific weaknesses and areas for improvement"],
                    "critical_moments": ["list of important moments or patterns identified"],
                    "improvement_areas": ["specific suggestions for improvement"],
                    "opening": {{
                        "analysis": "detailed analysis of opening play",
                        "suggestion": "specific suggestion for opening improvement"
                    }},
                    "middlegame": {{
                        "analysis": "detailed analysis of middlegame play",
                        "suggestion": "specific suggestion for middlegame improvement"
                    }},
                    "endgame": {{
                        "analysis": "detailed analysis of endgame play",
                        "suggestion": "specific suggestion for endgame improvement"
                    }}
                }}
            }}"""
        except Exception as e:
            logger.error(f"Error generating analysis prompt: {str(e)}")
            return ""

    def _extract_sections(self, text: str) -> Dict[str, List[str]]:
        """Extract sections from AI response text."""
        sections: Dict[str, List[str]] = {
            "strengths": [],
            "weaknesses": [],
            "critical_moments": [],
            "improvement_areas": [],
            "opening": [],
            "middlegame": [],
            "endgame": [],
        }

        current_section = None
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Check for section headers
            lower_line = line.lower()
            if "strengths:" in lower_line:
                current_section = "strengths"
                continue
            elif "weaknesses:" in lower_line:
                current_section = "weaknesses"
                continue
            elif "critical moments:" in lower_line:
                current_section = "critical_moments"
                continue
            elif "improvement areas:" in lower_line:
                current_section = "improvement_areas"
                continue
            elif "opening:" in lower_line:
                current_section = "opening"
                continue
            elif "middlegame:" in lower_line:
                current_section = "middlegame"
                continue
            elif "endgame:" in lower_line:
                current_section = "endgame"
                continue

            # Add content to current section
            if current_section and line:
                if line.startswith("- "):
                    line = line[2:]
                sections[current_section].append(line)

        return sections

    def _parse_ai_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse the AI response and extract structured feedback."""
        try:
            # First try to parse as JSON directly
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                logger.warning("Response is not valid JSON, attempting to extract sections")

            # Extract sections from text response
            sections = self._extract_sections(response)
            if sections:
                return {
                    "feedback": {
                        "source": "openai",
                        "strengths": sections.get("strengths", []),
                        "weaknesses": sections.get("weaknesses", []),
                        "critical_moments": sections.get("critical_moments", []),
                        "improvement_areas": sections.get("improvement_areas", []),
                        "opening": {
                            "analysis": sections.get("opening", [""])[0],
                            "suggestion": (
                                sections.get("opening", ["", ""])[1] if len(sections.get("opening", [])) > 1 else ""
                            ),
                        },
                        "middlegame": {
                            "analysis": sections.get("middlegame", [""])[0],
                            "suggestion": (
                                sections.get("middlegame", ["", ""])[1]
                                if len(sections.get("middlegame", [])) > 1
                                else ""
                            ),
                        },
                        "endgame": {
                            "analysis": sections.get("endgame", [""])[0],
                            "suggestion": (
                                sections.get("endgame", ["", ""])[1] if len(sections.get("endgame", [])) > 1 else ""
                            ),
                        },
                    }
                }

            logger.error(f"Failed to parse AI response: {response[:200]}...")
            return None

        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}")
            return None

    def _generate_statistical_feedback(self, game_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate feedback based on statistical analysis when AI is unavailable."""
        try:
            # Validate game_metrics structure
            if not isinstance(game_metrics, dict) or "overall" not in game_metrics:
                return {
                    "source": "statistical",
                    "strengths": [],
                    "weaknesses": ["Unable to analyze game properly"],
                    "critical_moments": [],
                    "improvement_areas": ["Overall game analysis"],
                    "opening": {"analysis": "Analysis unavailable", "suggestion": "Review basic principles"},
                    "middlegame": {"analysis": "Analysis unavailable", "suggestion": "Focus on fundamentals"},
                    "endgame": {"analysis": "Analysis unavailable", "suggestion": "Practice basic endgames"},
                    "metrics": {},
                }

            overall = game_metrics.get("overall", {})
            phases = game_metrics.get("phases", {})

            # Calculate strengths and weaknesses
            strengths = []
            weaknesses = []
            improvement_areas = []

            # Accuracy analysis
            accuracy = overall.get("accuracy", 0)
            if accuracy >= 80:
                strengths.append("High overall accuracy in move selection")
            elif accuracy < 60:
                weaknesses.append("Move accuracy needs improvement")
                improvement_areas.append("Overall move accuracy and calculation")

            # Time management
            time_score = overall.get("time_management_score", 0)
            if time_score >= 70:
                strengths.append("Effective time management")
            elif time_score < 50:
                weaknesses.append("Time management needs improvement")
                improvement_areas.append("Time management and decision making")

            # Tactical analysis
            if overall.get("mistakes", 0) > 2 or overall.get("blunders", 0) > 0:
                weaknesses.append("Tactical opportunities often missed")
                improvement_areas.append("Tactical pattern recognition and execution")

            # Phase analysis
            opening_accuracy = phases.get("opening", {}).get("accuracy", 0)
            middlegame_accuracy = phases.get("middlegame", {}).get("accuracy", 0)
            endgame_accuracy = phases.get("endgame", {}).get("accuracy", 0)

            feedback = {
                "source": "statistical",
                "strengths": strengths if strengths else ["Basic understanding of chess principles"],
                "weaknesses": weaknesses if weaknesses else ["Areas for improvement not identified"],
                "critical_moments": [],  # Statistical analysis doesn't identify specific moments
                "improvement_areas": improvement_areas if improvement_areas else ["General chess fundamentals"],
                "opening": {
                    "analysis": f"Opening play shows {opening_accuracy}% accuracy",
                    "suggestion": (
                        "Continue studying main lines of your openings"
                        if opening_accuracy >= 70
                        else "Focus on basic opening principles and development"
                    ),
                },
                "middlegame": {
                    "analysis": f"Middlegame performance at {middlegame_accuracy}% accuracy",
                    "suggestion": (
                        "Study complex positional play and strategic planning"
                        if middlegame_accuracy >= 70
                        else "Practice basic tactical patterns and piece activity"
                    ),
                },
                "endgame": {
                    "analysis": f"Endgame technique shows {endgame_accuracy}% accuracy",
                    "suggestion": (
                        "Study complex endgame positions and techniques"
                        if endgame_accuracy >= 70
                        else "Focus on basic endgame concepts and king activity"
                    ),
                },
            }

            # Add metrics
            feedback["metrics"] = self._calculate_statistical_metrics(game_metrics)

            return feedback

        except Exception as e:
            logger.error(f"Error generating statistical feedback: {str(e)}")
            # Return minimal feedback structure
            return {
                "source": "statistical",
                "strengths": [],
                "weaknesses": ["Unable to analyze game properly"],
                "critical_moments": [],
                "improvement_areas": ["Overall game analysis"],
                "opening": {"analysis": "Analysis unavailable", "suggestion": "Review basic principles"},
                "middlegame": {"analysis": "Analysis unavailable", "suggestion": "Focus on fundamentals"},
                "endgame": {"analysis": "Analysis unavailable", "suggestion": "Practice basic endgames"},
                "metrics": {},
            }

    def _calculate_statistical_metrics(self, game_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate statistical metrics from game data."""
        try:
            overall = game_metrics.get("overall", {})
            return {
                "total_moves": overall.get("total_moves", 0),
                "accuracy": overall.get("accuracy", 0),
                "mistakes": overall.get("mistakes", 0),
                "blunders": overall.get("blunders", 0),
                "average_centipawn_loss": overall.get("average_centipawn_loss", 0),
                "time_management_score": overall.get("time_management_score", 0),
            }
        except Exception as e:
            logger.error(f"Error calculating statistical metrics: {str(e)}")
            return {}

    def _generate_opening_feedback(self, opening_metrics: Dict[str, Any]) -> Dict[str, str]:
        """Generate feedback for the opening phase."""
        try:
            if not opening_metrics:
                return {"feedback": "No data available for opening phase analysis"}
                
            accuracy = opening_metrics.get('accuracy', 0)
            mistakes = opening_metrics.get('mistakes', 0)
            
            if accuracy > 80:
                quality = "excellent"
            elif accuracy > 60:
                quality = "good"
            elif accuracy > 40:
                quality = "average"
            else:
                quality = "poor"
                
            feedback = f"Opening play was {quality} with {accuracy:.1f}% accuracy."
            if mistakes > 0:
                feedback += f" Made {mistakes} mistakes in the opening phase."
                
            return {"feedback": feedback, "quality": quality, "accuracy": accuracy}
        except Exception as e:
            logger.error(f"Error generating opening feedback: {str(e)}")
            return {"feedback": "Insufficient data for opening analysis", "quality": "unknown"}
            
    def _generate_middlegame_feedback(self, middlegame_metrics: Dict[str, Any]) -> Dict[str, str]:
        """Generate feedback for the middlegame phase."""
        try:
            if not middlegame_metrics:
                return {"feedback": "No data available for middlegame phase analysis"}
                
            accuracy = middlegame_metrics.get('accuracy', 0)
            mistakes = middlegame_metrics.get('mistakes', 0)
            tactical_opportunities = middlegame_metrics.get('tactical_opportunities', 0)
            tactical_success = middlegame_metrics.get('tactical_success', 0)
            
            if accuracy > 80:
                quality = "excellent"
            elif accuracy > 60:
                quality = "good"
            elif accuracy > 40:
                quality = "average"
            else:
                quality = "poor"
                
            feedback = f"Middlegame play was {quality} with {accuracy:.1f}% accuracy."
            if mistakes > 0:
                feedback += f" Made {mistakes} mistakes in the middlegame phase."
            
            if tactical_opportunities > 0:
                success_rate = (tactical_success / tactical_opportunities * 100) if tactical_opportunities > 0 else 0
                feedback += f" Found {tactical_success} out of {tactical_opportunities} tactical opportunities ({success_rate:.1f}%)."
                
            return {"feedback": feedback, "quality": quality, "accuracy": accuracy}
        except Exception as e:
            logger.error(f"Error generating middlegame feedback: {str(e)}")
            return {"feedback": "Insufficient data for middlegame analysis", "quality": "unknown"}
            
    def _generate_endgame_feedback(self, endgame_metrics: Dict[str, Any]) -> Dict[str, str]:
        """Generate feedback for the endgame phase."""
        try:
            if not endgame_metrics:
                return {"feedback": "No data available for endgame phase analysis"}
                
            accuracy = endgame_metrics.get('accuracy', 0)
            mistakes = endgame_metrics.get('mistakes', 0)
            
            if accuracy > 80:
                quality = "excellent"
            elif accuracy > 60:
                quality = "good"
            elif accuracy > 40:
                quality = "average"
            else:
                quality = "poor"
                
            feedback = f"Endgame play was {quality} with {accuracy:.1f}% accuracy."
            if mistakes > 0:
                feedback += f" Made {mistakes} mistakes in the endgame phase."
                
            return {"feedback": feedback, "quality": quality, "accuracy": accuracy}
        except Exception as e:
            logger.error(f"Error generating endgame feedback: {str(e)}")
            return {"feedback": "Insufficient data for endgame analysis", "quality": "unknown"}
            
    def _identify_strengths(self, metrics: Dict[str, Any]) -> List[str]:
        """Identify player strengths based on metrics."""
        try:
            strengths = []
            overall = metrics.get('overall', {})
            phases = metrics.get('phases', {})
            tactics = metrics.get('tactics', {})
            time_mgmt = metrics.get('time_management', {})
            
            # Check overall accuracy
            accuracy = overall.get('accuracy', 0)
            if accuracy > 80:
                strengths.append(f"Strong overall play with {accuracy:.1f}% accuracy")
            
            # Check phase-specific strengths
            for phase_name, phase_data in phases.items():
                phase_accuracy = phase_data.get('accuracy', 0)
                if phase_accuracy > 75:
                    strengths.append(f"Strong {phase_name} play ({phase_accuracy:.1f}% accuracy)")
            
            # Check tactical awareness
            tactical_success = tactics.get('success_rate', 0)
            if tactical_success > 70:
                strengths.append(f"Good tactical awareness ({tactical_success:.1f}% success rate)")
            
            # Check time management
            time_score = time_mgmt.get('time_management_score', 0)
            if time_score > 70:
                strengths.append(f"Effective time management ({time_score:.1f}% efficiency)")
            
            # If no strengths identified, add a generic one
            if not strengths and accuracy > 40:
                strengths.append(f"Reasonable overall play with {accuracy:.1f}% accuracy")
            
            return strengths
        except Exception as e:
            logger.error(f"Error identifying strengths: {str(e)}")
            return ["Unable to determine strengths"]
            
    def _identify_weaknesses(self, metrics: Dict[str, Any]) -> List[str]:
        """Identify player weaknesses based on metrics."""
        try:
            weaknesses = []
            overall = metrics.get('overall', {})
            phases = metrics.get('phases', {})
            tactics = metrics.get('tactics', {})
            time_mgmt = metrics.get('time_management', {})
            
            # Check overall accuracy
            accuracy = overall.get('accuracy', 0)
            if accuracy < 50:
                weaknesses.append(f"Inconsistent overall play ({accuracy:.1f}% accuracy)")
            
            # Check mistakes and blunders
            mistakes = overall.get('mistakes', 0)
            blunders = overall.get('blunders', 0)
            if mistakes + blunders > 3:
                weaknesses.append(f"Made {mistakes} mistakes and {blunders} blunders")
            
            # Check phase-specific weaknesses
            for phase_name, phase_data in phases.items():
                phase_accuracy = phase_data.get('accuracy', 0)
                if phase_accuracy < 50:
                    weaknesses.append(f"Struggles in {phase_name} ({phase_accuracy:.1f}% accuracy)")
            
            # Check tactical awareness
            tactical_success = tactics.get('success_rate', 0)
            tactical_opportunities = tactics.get('opportunities', 0)
            if tactical_success < 40 and tactical_opportunities > 2:
                weaknesses.append(f"Missed tactical opportunities ({tactical_success:.1f}% success rate)")
            
            # Check time management
            time_score = time_mgmt.get('time_management_score', 0)
            if time_score < 40:
                weaknesses.append(f"Poor time management ({time_score:.1f}% efficiency)")
            
            # If no weaknesses identified, add a generic one
            if not weaknesses and accuracy < 80:
                weaknesses.append(f"Could improve overall accuracy (currently {accuracy:.1f}%)")
            
            return weaknesses
        except Exception as e:
            logger.error(f"Error identifying weaknesses: {str(e)}")
            return ["Unable to determine weaknesses"]
            
    def _find_critical_moments(self, moves: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find critical moments in the game."""
        try:
            critical_moments = []
            
            if not moves:
                return critical_moments
                
            # Sort moves by evaluation change (largest absolute value first)
            sorted_moves = sorted(
                [m for m in moves if 'eval_change' in m],
                key=lambda x: abs(x.get('eval_change', 0)),
                reverse=True
            )
            
            # Take the top 3 most significant moves
            for i, move in enumerate(sorted_moves[:3]):
                move_number = move.get('move_number', 0)
                move_san = move.get('san', move.get('move', '?'))
                eval_change = move.get('eval_change', 0)
                is_white = move.get('is_white', True)
                side = "White" if is_white else "Black"
                
                if abs(eval_change) < 50:
                    continue  # Skip if not actually significant
                    
                if eval_change < 0:
                    moment_type = "mistake"
                    if eval_change < -300:
                        moment_type = "blunder"
                else:
                    moment_type = "good move"
                    if eval_change > 300:
                        moment_type = "excellent move"
                
                description = f"Move {move_number}: {side}'s {moment_type} {move_san}"
                critical_moments.append({
                    "move_number": move_number,
                    "description": description,
                    "type": moment_type,
                    "eval_change": eval_change
                })
            
            return critical_moments
        except Exception as e:
            logger.error(f"Error finding critical moments: {str(e)}")
            return []
            
    def _generate_improvement_areas(self, metrics: Dict[str, Any], weaknesses: List[str]) -> List[str]:
        """Generate suggested improvement areas based on metrics and identified weaknesses."""
        try:
            improvement_areas = []
            overall = metrics.get('overall', {})
            phases = metrics.get('phases', {})
            
            # Look for the weakest phase
            weakest_phase = None
            lowest_accuracy = 100
            
            for phase_name, phase_data in phases.items():
                phase_accuracy = phase_data.get('accuracy', 0)
                if phase_accuracy < lowest_accuracy:
                    lowest_accuracy = phase_accuracy
                    weakest_phase = phase_name
            
            # Add phase-specific improvement suggestion
            if weakest_phase and lowest_accuracy < 70:
                improvement_areas.append(f"Study {weakest_phase} positions and principles")
            
            # Look at overall metrics
            mistakes = overall.get('mistakes', 0)
            blunders = overall.get('blunders', 0)
            
            if blunders > 2:
                improvement_areas.append("Practice calculation and double-check moves before playing them")
            
            if mistakes > 3:
                improvement_areas.append("Practice tactical exercises to improve pattern recognition")
            
            # Add general improvement areas
            if not improvement_areas:
                accuracy = overall.get('accuracy', 0)
                if accuracy < 90:
                    improvement_areas.append("Continue practicing tactics and game analysis")
                if accuracy < 70:
                    improvement_areas.append("Study basic chess principles and common patterns")
            
            return improvement_areas
        except Exception as e:
            logger.error(f"Error generating improvement areas: {str(e)}")
            return ["Practice tactics and analyze your games to improve"]
