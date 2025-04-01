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
            if not hasattr(settings, 'OPENAI_API_KEY') or not settings.OPENAI_API_KEY:
                logger.warning("OpenAI API key not found in settings")
                self.openai_client = None
                return

                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {str(e)}")
            self.openai_client = None

    def generate_feedback(self, game_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate feedback for a game using OpenAI."""
        try:
            # Validate metrics
            if not self._validate_metrics(game_metrics):
                logger.warning("Invalid metrics provided, using statistical feedback")
                return self._generate_statistical_feedback(game_metrics)

            # Initialize OpenAI if needed
            if not self.openai_client:
                self._initialize_openai()
            if not self.openai_client:
                logger.warning("OpenAI client not available, using statistical feedback")
                return self._generate_statistical_feedback(game_metrics)

            # Generate and validate prompt
            prompt = self._generate_analysis_prompt(game_metrics)
            if not prompt:
                logger.warning("Failed to generate prompt, using statistical feedback")
                return self._generate_statistical_feedback(game_metrics)

            # Make OpenAI request with retries
            max_retries = 3
            retry_delay = 2
            for attempt in range(max_retries):
                try:
                    response = self.openai_client.chat.completions.create(
                        model="gpt-4",  # Use GPT-4 for better analysis
                        messages=[
                            {"role": "system", "content": "You are a chess analysis expert. Provide detailed, accurate feedback based on game metrics."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=1000
                    )
                    
                    if response and response.choices:
                        ai_response = response.choices[0].message.content
                        logger.debug(f"OpenAI response received: {ai_response[:200]}...")
                        
                        # Parse response
                        feedback = self._parse_ai_response(ai_response)
                        if feedback:
                            # Add statistical metrics to AI feedback
                            feedback['metrics'] = self._calculate_statistical_metrics(game_metrics)
                            feedback['source'] = 'openai'
                            return feedback
                        
                    logger.warning("Failed to parse AI response, retrying...")
                    
                except Exception as e:
                    logger.error(f"Error in OpenAI request (attempt {attempt + 1}): {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    continue

            logger.warning("All OpenAI attempts failed, using statistical feedback")
            return self._generate_statistical_feedback(game_metrics)

        except Exception as e:
            logger.error(f"Error generating feedback: {str(e)}")
            return self._generate_statistical_feedback(game_metrics)

    def _validate_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Validate that the metrics contain required data."""
        try:
            # Check if we have the basic structure
            if not isinstance(metrics, dict):
                logger.warning("Metrics is not a dictionary")
                return False

            # Handle both nested and unnested structures
            if 'analysis_results' in metrics:
                metrics = metrics['analysis_results']
            
            # Handle summary wrapper
            if 'summary' in metrics:
                summary = metrics['summary']
            else:
                summary = metrics

            # Get moves from either top level or nested
            moves = metrics.get('moves', []) or summary.get('moves', [])
            has_moves = bool(moves)
            
            # Get overall metrics
            overall = summary.get('overall', {})
            if not overall and isinstance(summary.get('summary', {}), dict):
                overall = summary['summary'].get('overall', {})

            # More lenient validation
            has_accuracy = overall.get('accuracy', 0) >= 0  # Allow 0 accuracy
            has_moves_count = overall.get('total_moves', 0) > 0 or len(moves) > 0
            has_any_metrics = any(
                overall.get(key, 0) >= 0  # Allow 0 values
                for key in ['mistakes', 'blunders', 'inaccuracies', 'time_management_score']
            )

            # Consider valid if we have moves and any metrics
            is_valid = has_moves and (has_accuracy or has_any_metrics)
            
            if not is_valid:
                logger.warning(f"Metrics validation failed: has_moves={has_moves}, accuracy={has_accuracy}, other_metrics={has_any_metrics}")
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
            overall = game_metrics.get('overall', {})
            phases = game_metrics.get('phases', {})
            tactics = game_metrics.get('tactics', {})
            time_mgmt = game_metrics.get('time_management', {})

            prompt_data = {
            "game_metrics": {
                    "total_moves": overall.get('total_moves', 0),
                    "accuracy": overall.get('accuracy', 0),
                    "mistakes": overall.get('mistakes', 0),
                    "blunders": overall.get('blunders', 0),
                    "average_centipawn_loss": overall.get('average_centipawn_loss', 0),
                    "time_management": {
                        "time_pressure_moves": time_mgmt.get('time_pressure_moves', 0),
                        "average_time": time_mgmt.get('average_time', 0),
                        "time_management_score": time_mgmt.get('time_management_score', 0)
                    },
                    "tactics": {
                        "opportunities": tactics.get('opportunities', 0),
                        "successful": tactics.get('successful', 0),
                        "tactical_score": tactics.get('tactical_score', 0)
                    },
                "phases": {
                        "opening": phases.get('opening', {}),
                        "middlegame": phases.get('middlegame', {}),
                        "endgame": phases.get('endgame', {})
                    }
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
            'strengths': [],
            'weaknesses': [],
            'critical_moments': [],
            'improvement_areas': [],
            'opening': [],
            'middlegame': [],
            'endgame': []
        }
        
        current_section = None
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                                continue

            # Check for section headers
            lower_line = line.lower()
            if 'strengths:' in lower_line:
                current_section = 'strengths'
                continue
            elif 'weaknesses:' in lower_line:
                current_section = 'weaknesses'
                continue
            elif 'critical moments:' in lower_line:
                current_section = 'critical_moments'
                continue
            elif 'improvement areas:' in lower_line:
                current_section = 'improvement_areas'
                continue
            elif 'opening:' in lower_line:
                current_section = 'opening'
                continue
            elif 'middlegame:' in lower_line:
                current_section = 'middlegame'
                continue
            elif 'endgame:' in lower_line:
                current_section = 'endgame'
                continue

            # Add content to current section
            if current_section and line:
                if line.startswith('- '):
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
                    'feedback': {
                        'source': 'openai',
                        'strengths': sections.get('strengths', []),
                        'weaknesses': sections.get('weaknesses', []),
                        'critical_moments': sections.get('critical_moments', []),
                        'improvement_areas': sections.get('improvement_areas', []),
                        'opening': {
                            'analysis': sections.get('opening', [''])[0],
                            'suggestion': sections.get('opening', ['', ''])[1] if len(sections.get('opening', [])) > 1 else ''
                        },
                        'middlegame': {
                            'analysis': sections.get('middlegame', [''])[0],
                            'suggestion': sections.get('middlegame', ['', ''])[1] if len(sections.get('middlegame', [])) > 1 else ''
                        },
                        'endgame': {
                            'analysis': sections.get('endgame', [''])[0],
                            'suggestion': sections.get('endgame', ['', ''])[1] if len(sections.get('endgame', [])) > 1 else ''
                        }
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
            if not isinstance(game_metrics, dict) or 'overall' not in game_metrics:
                return {
                    'source': 'statistical',
                    'strengths': [],
                    'weaknesses': ['Unable to analyze game properly'],
                    'critical_moments': [],
                    'improvement_areas': ['Overall game analysis'],
                    'opening': {'analysis': 'Analysis unavailable', 'suggestion': 'Review basic principles'},
                    'middlegame': {'analysis': 'Analysis unavailable', 'suggestion': 'Focus on fundamentals'},
                    'endgame': {'analysis': 'Analysis unavailable', 'suggestion': 'Practice basic endgames'},
                    'metrics': {}
                }

            overall = game_metrics.get('overall', {})
            phases = game_metrics.get('phases', {})
            
            # Calculate strengths and weaknesses
            strengths = []
            weaknesses = []
            improvement_areas = []
            
            # Accuracy analysis
            accuracy = overall.get('accuracy', 0)
            if accuracy >= 80:
                strengths.append("High overall accuracy in move selection")
            elif accuracy < 60:
                weaknesses.append("Move accuracy needs improvement")
                improvement_areas.append("Overall move accuracy and calculation")

            # Time management
            time_score = overall.get('time_management_score', 0)
            if time_score >= 70:
                strengths.append("Effective time management")
            elif time_score < 50:
                weaknesses.append("Time management needs improvement")
                improvement_areas.append("Time management and decision making")

            # Tactical analysis
            if overall.get('mistakes', 0) > 2 or overall.get('blunders', 0) > 0:
                weaknesses.append("Tactical opportunities often missed")
                improvement_areas.append("Tactical pattern recognition and execution")

            # Phase analysis
            opening_accuracy = phases.get('opening', {}).get('accuracy', 0)
            middlegame_accuracy = phases.get('middlegame', {}).get('accuracy', 0)
            endgame_accuracy = phases.get('endgame', {}).get('accuracy', 0)

            feedback = {
                'source': 'statistical',
                'strengths': strengths if strengths else ['Basic understanding of chess principles'],
                'weaknesses': weaknesses if weaknesses else ['Areas for improvement not identified'],
                'critical_moments': [],  # Statistical analysis doesn't identify specific moments
                'improvement_areas': improvement_areas if improvement_areas else ['General chess fundamentals'],
                'opening': {
                    'analysis': f'Opening play shows {opening_accuracy}% accuracy',
                    'suggestion': 'Continue studying main lines of your openings' if opening_accuracy >= 70 
                                else 'Focus on basic opening principles and development'
                },
                'middlegame': {
                    'analysis': f'Middlegame performance at {middlegame_accuracy}% accuracy',
                    'suggestion': 'Study complex positional play and strategic planning' if middlegame_accuracy >= 70
                                else 'Practice basic tactical patterns and piece activity'
                },
                'endgame': {
                    'analysis': f'Endgame technique shows {endgame_accuracy}% accuracy',
                    'suggestion': 'Study complex endgame positions and techniques' if endgame_accuracy >= 70
                                else 'Focus on basic endgame concepts and king activity'
                }
            }

            # Add metrics
            feedback['metrics'] = self._calculate_statistical_metrics(game_metrics)
            
            return feedback

        except Exception as e:
            logger.error(f"Error generating statistical feedback: {str(e)}")
            # Return minimal feedback structure
            return {
                'source': 'statistical',
                'strengths': [],
                'weaknesses': ['Unable to analyze game properly'],
                'critical_moments': [],
                'improvement_areas': ['Overall game analysis'],
                'opening': {'analysis': 'Analysis unavailable', 'suggestion': 'Review basic principles'},
                'middlegame': {'analysis': 'Analysis unavailable', 'suggestion': 'Focus on fundamentals'},
                'endgame': {'analysis': 'Analysis unavailable', 'suggestion': 'Practice basic endgames'},
                'metrics': {}
            }

    def _calculate_statistical_metrics(self, game_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate statistical metrics from game data."""
        try:
            overall = game_metrics.get('overall', {})
            return {
                'total_moves': overall.get('total_moves', 0),
                'accuracy': overall.get('accuracy', 0),
                'mistakes': overall.get('mistakes', 0),
                'blunders': overall.get('blunders', 0),
                'average_centipawn_loss': overall.get('average_centipawn_loss', 0),
                'time_management_score': overall.get('time_management_score', 0)
            }
        except Exception as e:
            logger.error(f"Error calculating statistical metrics: {str(e)}")
            return {} 