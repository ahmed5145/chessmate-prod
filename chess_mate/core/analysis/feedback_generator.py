"""
Feedback generator for chess games.
Handles generation of game feedback using OpenAI API.
"""

import logging
import json
import re
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
                logger.warning("OpenAI client not available")
                return self._get_default_feedback()

            prompt = self._generate_analysis_prompt(game_metrics)
            response_text = self._make_openai_request(prompt)
            
            if not response_text:
                logger.warning("No response from OpenAI")
                return self._get_default_feedback()

            feedback = self._parse_ai_response(response_text)
            if not feedback:
                logger.warning("Failed to parse AI response")
                return self._get_default_feedback()

            return feedback

        except Exception as e:
            logger.error(f"Error generating feedback: {str(e)}")
            return self._get_default_feedback()

    def _generate_analysis_prompt(self, game_metrics: Dict[str, Any]) -> str:
        """Generate a concise prompt for AI analysis."""
        prompt = {
            "game_metrics": {
                "total_moves": game_metrics.get('overall', {}).get('total_moves', 0),
                "accuracy": game_metrics.get('overall', {}).get('accuracy', 0),
                "mistakes": game_metrics.get('overall', {}).get('mistakes', 0),
                "blunders": game_metrics.get('overall', {}).get('blunders', 0),
                "time_pressure_moves": game_metrics.get('time_management', {}).get('time_pressure_moves', 0),
                "tactical_opportunities": game_metrics.get('tactics', {}).get('opportunities', 0),
                "successful_tactics": game_metrics.get('tactics', {}).get('successful', 0)
            }
        }

        return """Analyze these chess game metrics and provide feedback in a specific JSON format. Keep all text responses very concise (max 10-15 words per field).

Game metrics: """ + json.dumps(prompt) + """

Provide analysis in this exact JSON structure:
{
    "feedback": {
        "summary": {
            "accuracy": number,
            "evaluation": string,
            "comment": string
        },
        "phases": {
            "opening": {
                "analysis": string,
                "suggestions": [string]
            },
            "middlegame": {
                "analysis": string,
                "suggestions": [string]
            },
            "endgame": {
                "analysis": string,
                "suggestions": [string]
            }
        },
        "tactics": {
            "analysis": string,
            "opportunities": number,
            "successful": number,
            "success_rate": number,
            "suggestions": [string]
        },
        "time_management": {
            "score": number,
            "avg_time_per_move": number,
            "time_pressure_moves": number,
            "time_pressure_percentage": number,
            "suggestion": string
        }
    }
}"""

    def _make_openai_request(self, prompt: str) -> Optional[str]:
        """Make a request to OpenAI API."""
        try:
            if not self.openai_client:
                logger.error("OpenAI client not initialized")
                return None

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a chess analysis assistant. Your response must be a valid JSON object. "
                        "Format your entire response as a JSON object with the exact structure specified in the user's prompt. "
                        "Do not include any text outside the JSON object."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            # Retry logic for API calls
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1000
                    )

                    if not response or not response.choices:
                        logger.error("Invalid completion response from OpenAI")
                        continue

                    content = response.choices[0].message.content
                    if not content:
                        logger.error("Empty content in OpenAI response")
                        continue

                    # Validate JSON before returning
                    try:
                        json.loads(content)
                        return content
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in response, attempt {attempt + 1}")
                        continue

                except Exception as e:
                    logger.error(f"API call failed, attempt {attempt + 1}: {str(e)}")
                    if attempt < max_retries - 1:
                        continue
                    break

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
            required_fields = {'summary', 'phases', 'tactics', 'time_management'}
            if not all(field in feedback for field in required_fields):
                logger.error("Missing required fields in feedback")
                return None

            return feedback

        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}")
            return None

    def _get_default_feedback(self) -> Dict[str, Any]:
        """Return default feedback when generation fails."""
        return {
            'summary': {
                'accuracy': 50.0,
                'evaluation': 'Analysis not available',
                'comment': 'Unable to generate detailed feedback'
            },
            'phases': {
                'opening': {
                    'analysis': 'No analysis available',
                    'suggestions': ['Review basic opening principles']
                },
                'middlegame': {
                    'analysis': 'No analysis available',
                    'suggestions': ['Focus on piece coordination']
                },
                'endgame': {
                    'analysis': 'No analysis available',
                    'suggestions': ['Practice basic endgames']
                }
            },
            'tactics': {
                'analysis': 'No tactical analysis available',
                'opportunities': 0,
                'successful': 0,
                'success_rate': 0,
                'suggestions': ['Practice tactical puzzles']
            },
            'time_management': {
                'score': 50,
                'avg_time_per_move': 0,
                'time_pressure_moves': 0,
                'time_pressure_percentage': 0,
                'suggestion': 'Work on time management'
            }
        } 