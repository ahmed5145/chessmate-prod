"""
Feedback generator for chess games.
Handles generation of game feedback using OpenAI API.
"""

import logging
import json
import re
import time
from typing import Dict, Any, Optional, List
from django.conf import settings
from openai import OpenAI
from django.core.cache import cache

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
            if settings.OPENAI_API_KEY:
                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("OpenAI client initialized successfully")
            else:
                logger.warning("OpenAI API key not found")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {str(e)}")
            self.openai_client = None

    def generate_feedback(self, game_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate feedback for a game using OpenAI."""
        try:
            if not self.openai_client:
                logger.warning("OpenAI client not available, using statistical feedback")
                return self._generate_statistical_feedback(game_metrics)

            prompt = self._generate_analysis_prompt(game_metrics)
            response = self._make_openai_request(prompt)
            
            if not response:
                logger.warning("No response from OpenAI, using statistical feedback")
                return self._generate_statistical_feedback(game_metrics)

            feedback = self._parse_ai_response(response)
            if not feedback:
                logger.warning("Failed to parse AI response, using statistical feedback")
                return self._generate_statistical_feedback(game_metrics)

            # Add statistical metrics to AI feedback
            feedback['metrics'] = self._calculate_statistical_metrics(game_metrics)
            return feedback

        except Exception as e:
            logger.error(f"Error generating feedback: {str(e)}")
            return self._generate_statistical_feedback(game_metrics)

    def _generate_analysis_prompt(self, game_metrics: Dict[str, Any]) -> str:
        """Generate a detailed prompt for AI analysis."""
        prompt = {
            "game_metrics": {
                "total_moves": game_metrics.get('overall', {}).get('total_moves', 0),
                "accuracy": game_metrics.get('overall', {}).get('accuracy', 0),
                "mistakes": game_metrics.get('overall', {}).get('mistakes', 0),
                "blunders": game_metrics.get('overall', {}).get('blunders', 0),
                "time_pressure_moves": game_metrics.get('time_management', {}).get('time_pressure_moves', 0),
                "tactical_opportunities": game_metrics.get('tactics', {}).get('opportunities', 0),
                "successful_tactics": game_metrics.get('tactics', {}).get('successful', 0),
                "phases": {
                    "opening": game_metrics.get('phases', {}).get('opening', {}),
                    "middlegame": game_metrics.get('phases', {}).get('middlegame', {}),
                    "endgame": game_metrics.get('phases', {}).get('endgame', {})
                }
            }
        }

        return f"""Analyze these chess game metrics and provide detailed feedback in JSON format:

Game metrics: {json.dumps(prompt)}

Provide analysis in this exact JSON structure:
{{
    "feedback": {{
        "source": "openai",
        "strengths": ["list of specific strengths"],
        "weaknesses": ["list of specific weaknesses"],
        "critical_moments": [
            {{
                "move": "move number",
                "description": "what happened",
                "suggestion": "how to improve"
            }}
        ],
        "improvement_areas": ["list of areas to improve"],
        "opening": {{
            "analysis": "detailed opening analysis",
            "suggestion": "specific opening improvement suggestion"
        }},
        "middlegame": {{
            "analysis": "detailed middlegame analysis",
            "suggestion": "specific middlegame improvement suggestion"
        }},
        "endgame": {{
            "analysis": "detailed endgame analysis",
            "suggestion": "specific endgame improvement suggestion"
        }}
    }}
}}"""

    def _make_openai_request(self, prompt: str) -> Optional[str]:
        """Make a request to OpenAI API with retry logic."""
        try:
            if not self.openai_client:
                return None

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a chess analysis assistant. Provide detailed, specific feedback "
                        "focusing on concrete improvements. Format your entire response as a JSON object."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.openai_client.chat.completions.create(
                        model=settings.OPENAI_MODEL,
                        messages=messages,
                        temperature=settings.OPENAI_TEMPERATURE,
                        max_tokens=settings.OPENAI_MAX_TOKENS
                    )

                    if response and response.choices:
                        content = response.choices[0].message.content
                        if content:
                            try:
                                # Validate JSON structure
                                json.loads(content)
                                return content
                            except json.JSONDecodeError:
                                logger.warning(f"Invalid JSON in response, attempt {attempt + 1}")
                                continue

                except Exception as e:
                    logger.error(f"API call failed, attempt {attempt + 1}: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    continue

            return None

        except Exception as e:
            logger.error(f"Error making OpenAI request: {str(e)}")
            return None

    def _parse_ai_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse and validate the OpenAI response."""
        try:
            if not isinstance(response, str):
                logger.error("Response must be a string")
                return None

            # Clean up the response string
            cleaned_response = response.strip()
            
            # Extract JSON content
            json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
            if not json_match:
                logger.error("No valid JSON object found in response")
                return None
            
            json_str = json_match.group(0)
            
            # Fix common JSON formatting issues
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)  # Remove trailing commas
            json_str = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', json_str)  # Quote unquoted keys
            
            try:
                parsed_data = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {str(e)}")
                return None

            if not isinstance(parsed_data, dict):
                logger.error("Parsed data is not a dictionary")
                return None

            feedback = parsed_data.get('feedback', {})
            if not isinstance(feedback, dict):
                logger.error("Feedback is not a dictionary")
                return None

            # Validate required structure
            required_fields = {'source', 'strengths', 'weaknesses', 'critical_moments', 'improvement_areas', 'opening', 'middlegame', 'endgame'}
            if not all(field in feedback for field in required_fields):
                logger.error("Missing required fields in feedback")
                return None

            return feedback

        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}")
            return None

    def _generate_statistical_feedback(self, game_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate feedback based on statistical analysis when AI is unavailable."""
        try:
            overall = game_metrics.get('overall', {})
            phases = game_metrics.get('phases', {})
            tactics = game_metrics.get('tactics', {})
            time_mgmt = game_metrics.get('time_management', {})

            # Calculate strengths and weaknesses
            strengths = []
            weaknesses = []
            
            # Accuracy analysis
            accuracy = overall.get('accuracy', 0)
            if accuracy >= 80:
                strengths.append("High overall accuracy in move selection")
            elif accuracy < 60:
                weaknesses.append("Move accuracy needs improvement")

            # Tactical analysis
            tactical_success = tactics.get('success_rate', 0)
            if tactical_success >= 70:
                strengths.append("Strong tactical awareness")
            elif tactical_success < 50:
                weaknesses.append("Tactical opportunities often missed")

            # Time management
            time_pressure = time_mgmt.get('time_pressure_percentage', 0)
            if time_pressure < 20:
                strengths.append("Effective time management")
            elif time_pressure > 40:
                weaknesses.append("Frequent time pressure situations")

            # Phase analysis
            opening_accuracy = phases.get('opening', {}).get('accuracy', 0)
            middlegame_accuracy = phases.get('middlegame', {}).get('accuracy', 0)
            endgame_accuracy = phases.get('endgame', {}).get('accuracy', 0)

            phase_feedback = {
                'opening': {
                    'analysis': f"Opening play shows {opening_accuracy}% accuracy",
                    'suggestion': self._get_opening_suggestion(opening_accuracy)
                },
                'middlegame': {
                    'analysis': f"Middlegame performance at {middlegame_accuracy}% accuracy",
                    'suggestion': self._get_middlegame_suggestion(middlegame_accuracy)
                },
                'endgame': {
                    'analysis': f"Endgame technique shows {endgame_accuracy}% accuracy",
                    'suggestion': self._get_endgame_suggestion(endgame_accuracy)
                }
            }

            return {
                'feedback': {
                    'source': 'statistical',
                    'strengths': strengths,
                    'weaknesses': weaknesses,
                    'critical_moments': self._identify_critical_moments(game_metrics),
                    'improvement_areas': self._generate_improvement_areas(game_metrics),
                    'opening': phase_feedback['opening'],
                    'middlegame': phase_feedback['middlegame'],
                    'endgame': phase_feedback['endgame']
                }
            }

        except Exception as e:
            logger.error(f"Error generating statistical feedback: {str(e)}")
            return self._get_default_feedback()

    def _get_opening_suggestion(self, accuracy: float) -> str:
        if accuracy >= 80:
            return "Continue studying main lines of your openings"
        elif accuracy >= 60:
            return "Focus on understanding opening principles and piece development"
        else:
            return "Review basic opening principles and common structures"

    def _get_middlegame_suggestion(self, accuracy: float) -> str:
        if accuracy >= 80:
            return "Study complex positional play and strategic planning"
        elif accuracy >= 60:
            return "Work on piece coordination and pawn structure understanding"
        else:
            return "Practice basic tactical patterns and piece activity"

    def _get_endgame_suggestion(self, accuracy: float) -> str:
        if accuracy >= 80:
            return "Study complex endgame positions and techniques"
        elif accuracy >= 60:
            return "Practice fundamental endgame positions and principles"
        else:
            return "Focus on basic endgame concepts and king activity"

    def _identify_critical_moments(self, game_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify critical moments in the game."""
        critical_moments = []
        moves = game_metrics.get('moves', [])
        
        for move in moves:
            if move.get('is_critical', False):
                critical_moments.append({
                    'move': move.get('move_number', 0),
                    'description': self._describe_critical_moment(move),
                    'suggestion': self._get_improvement_suggestion(move)
                })

        return critical_moments

    def _describe_critical_moment(self, move: Dict[str, Any]) -> str:
        """Generate description for a critical moment."""
        if move.get('is_blunder', False):
            return "Significant mistake that changed the game's direction"
        elif move.get('is_mistake', False):
            return "Inaccuracy that weakened the position"
        elif move.get('is_best', False):
            return "Found the strongest continuation"
        else:
            return "Important position requiring careful consideration"

    def _get_improvement_suggestion(self, move: Dict[str, Any]) -> str:
        """Generate improvement suggestion for a move."""
        if move.get('is_blunder', False):
            return "Take more time in critical positions to evaluate all options"
        elif move.get('is_mistake', False):
            return "Calculate variations more carefully in complex positions"
        elif move.get('time_spent', 0) < 30:
            return "Consider spending more time on important decisions"
        else:
            return "Continue practicing calculation and evaluation skills"

    def _generate_improvement_areas(self, game_metrics: Dict[str, Any]) -> List[str]:
        """Generate list of improvement areas based on game metrics."""
        areas = []
        overall = game_metrics.get('overall', {})
        tactics = game_metrics.get('tactics', {})
        time_mgmt = game_metrics.get('time_management', {})

        if overall.get('accuracy', 0) < 70:
            areas.append("Overall move accuracy and calculation")
        if tactics.get('success_rate', 0) < 60:
            areas.append("Tactical pattern recognition and execution")
        if time_mgmt.get('time_pressure_percentage', 0) > 30:
            areas.append("Time management and decision making")
        if overall.get('mistakes', 0) > 3:
            areas.append("Position evaluation and move selection")
        if overall.get('blunders', 0) > 1:
            areas.append("Critical position handling")

        return areas

    def _get_default_feedback(self) -> Dict[str, Any]:
        """Return default feedback structure when analysis fails."""
        return {
            'feedback': {
                'source': 'basic',
                'strengths': ['Basic understanding of chess principles'],
                'weaknesses': ['Areas for improvement not identified'],
                'critical_moments': [],
                'improvement_areas': ['General chess fundamentals'],
                'opening': {
                    'analysis': 'Opening analysis not available',
                    'suggestion': 'Study basic opening principles'
                },
                'middlegame': {
                    'analysis': 'Middlegame analysis not available',
                    'suggestion': 'Practice piece coordination'
                },
                'endgame': {
                    'analysis': 'Endgame analysis not available',
                    'suggestion': 'Study fundamental endgame positions'
                }
            }
        } 