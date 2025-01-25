import os
from openai import OpenAI
from typing import Dict, List, Any, Optional, TypedDict, Union, Literal
import logging
import re

logger = logging.getLogger(__name__)

class FeedbackSection(TypedDict):
    analysis: str
    suggestions: List[str]

class StudyPlan(TypedDict):
    focus_areas: List[str]
    exercises: List[str]

class FeedbackData(TypedDict):
    overall_performance: Dict[str, Any]
    opening: FeedbackSection
    middlegame: FeedbackSection
    tactics: FeedbackSection
    strategy: FeedbackSection
    time_management: FeedbackSection
    endgame: FeedbackSection
    resourcefulness: FeedbackSection
    advantage: FeedbackSection
    study_plan: StudyPlan
    peer_comparison: Dict[str, Any]

SectionType = Literal["overall_performance", "opening", "middlegame", "tactics", "strategy", "time_management", "endgame", "resourcefulness", "advantage"]

class AIFeedbackGenerator:
    """Class to handle AI-powered feedback generation for chess games."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the feedback generator with OpenAI API key."""
        self.client = None
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not set. AI feedback will be disabled.")
        else:
            self.client = OpenAI(api_key=api_key)

    def generate_personalized_feedback(
        self,
        game_analysis: List[Dict[str, Any]],
        player_profile: Dict[str, Any]
    ) -> FeedbackData:
        """
        Generate personalized feedback using OpenAI's GPT model.
        
        Args:
            game_analysis: List of move analysis data
            player_profile: Dictionary containing player information
            
        Returns:
            Dictionary containing structured feedback
        """
        try:
            if not self.client:
                logger.warning("OpenAI client not initialized. Using fallback feedback.")
                return self._generate_fallback_feedback(game_analysis)

            # Check if we have enough analysis data
            if not game_analysis or len(game_analysis) < 5:
                logger.warning("Insufficient analysis data for AI feedback")
                return self._generate_fallback_feedback(game_analysis)

            # Prepare the analysis summary
            analysis_summary = self._prepare_analysis_summary(game_analysis)
            
            # Create the prompt
            prompt = self._create_analysis_prompt(analysis_summary, player_profile)
            
            # Generate feedback using OpenAI with retry logic
            max_retries = 2
            retry_count = 0
            while retry_count <= max_retries:
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a chess analysis expert providing specific, actionable feedback to help players improve their game."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        max_tokens=500,
                        temperature=0.7
                    )
                    
                    content = response.choices[0].message.content
                    if not content:
                        logger.warning("Empty response from OpenAI API")
                        return self._generate_fallback_feedback(game_analysis)
                        
                    feedback = self._parse_ai_response(content)
                    return feedback
                except Exception as e:
                    if "insufficient_quota" in str(e) or "429" in str(e):
                        logger.warning("OpenAI API quota exceeded, using fallback feedback")
                        return self._generate_fallback_feedback(game_analysis)
                    elif retry_count < max_retries:
                        retry_count += 1
                        logger.warning(f"Retrying OpenAI API call ({retry_count}/{max_retries})")
                        continue
                    else:
                        logger.error("Error generating AI feedback: %s", str(e))
                        return self._generate_fallback_feedback(game_analysis)
            
        except Exception as e:
            logger.error("Error generating AI feedback: %s", str(e))
            return self._generate_fallback_feedback(game_analysis)

    def _prepare_analysis_summary(self, game_analysis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare a summary of the game analysis for the AI prompt."""
        summary: Dict[str, Union[int, List[Dict[str, Any]]]] = {
            "total_moves": len(game_analysis),
            "critical_moves": [],
            "mistakes": [],
            "positional_notes": [],
            "time_management": []
        }
        
        for move in game_analysis:
            if move.get("is_critical"):
                critical_moves = summary.get("critical_moves", [])
                if isinstance(critical_moves, list):
                    critical_moves.append({
                        "move_number": move["move_number"],
                        "move": move["move"],
                        "evaluation": move["score"]
                    })
            
            if move.get("is_mistake"):
                mistakes = summary.get("mistakes", [])
                if isinstance(mistakes, list):
                    mistakes.append({
                        "move_number": move["move_number"],
                        "move": move["move"],
                        "evaluation_drop": move.get("evaluation_drop", 0)
                    })
            
            if move.get("time_spent", 0) > 60:  # More than 60 seconds spent
                time_management = summary.get("time_management", [])
                if isinstance(time_management, list):
                    time_management.append({
                        "move_number": move["move_number"],
                        "time_spent": move["time_spent"]
                    })
        
        return summary

    def _create_analysis_prompt(
        self,
        analysis_summary: Dict[str, Any],
        player_profile: Dict[str, Any]
    ) -> str:
        """Create a detailed prompt for the AI based on analysis and player profile."""
        preferences = player_profile.get('preferences', {})
        prompt = f"""
Analyze this chess game for {player_profile.get('username', 'Anonymous')} (Rating: {player_profile.get('rating', 'Unrated')})
Total games played: {player_profile.get('total_games', 0)}
Preferred openings: {', '.join(preferences.get('preferred_openings', ['Not specified']))}

Game Summary:
- Total moves: {analysis_summary['total_moves']}
- Critical positions: {len(analysis_summary.get('critical_moves', []))}
- Mistakes: {len(analysis_summary.get('mistakes', []))}
- Time management issues: {len(analysis_summary.get('time_management', []))}

Please provide comprehensive analysis in the following areas:
1. Overall Performance: Score (0-100), interpretation, key strengths, and areas to improve
2. Opening Analysis: Evaluation of opening choices and execution
3. Middlegame Play: Assessment of positional understanding and piece coordination
4. Tactical Awareness: Evaluation of combinations and tactical opportunities
5. Strategic Understanding: Assessment of long-term planning and positional play
6. Time Management: Analysis of time usage in critical positions
7. Endgame Technique: Evaluation of technical execution
8. Resourcefulness: Assessment of defensive skills and finding resources
9. Advantage Conversion: Analysis of ability to convert advantages
10. Peer Comparison: Performance relative to players of similar rating
11. Study Plan: Specific focus areas and exercises for improvement

For each section, provide:
- Detailed analysis of performance
- Concrete suggestions for improvement
- Numerical scores where applicable
- Specific examples from the game

Focus on actionable feedback that will help the player improve.
"""
        return prompt

    def _parse_ai_response(self, response_text: str) -> FeedbackData:
        """Parse and structure the AI's response into organized feedback."""
        feedback: FeedbackData = {
            "overall_performance": {
                "score": 0,
                "interpretation": "",
                "key_strengths": [],
                "areas_to_improve": []
            },
            "opening": {"analysis": "", "suggestions": []},
            "middlegame": {"analysis": "", "suggestions": []},
            "tactics": {"analysis": "", "suggestions": []},
            "strategy": {"analysis": "", "suggestions": []},
            "time_management": {"analysis": "", "suggestions": []},
            "endgame": {"analysis": "", "suggestions": []},
            "resourcefulness": {"analysis": "", "suggestions": []},
            "advantage": {"analysis": "", "suggestions": []},
            "study_plan": {"focus_areas": [], "exercises": []},
            "peer_comparison": {
                "overall": {"percentile": 0, "interpretation": ""},
                "tactics": {"percentile": 0, "interpretation": ""},
                "strategy": {"percentile": 0, "interpretation": ""}
            }
        }
        
        current_section: Optional[Union[SectionType, Literal["study_plan", "peer_comparison"]]] = None
        
        for line in response_text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Identify sections
            if "overall performance" in line.lower():
                current_section = "overall_performance"
            elif "opening" in line.lower():
                current_section = "opening"
            elif "middlegame" in line.lower():
                current_section = "middlegame"
            elif "tactical" in line.lower():
                current_section = "tactics"
            elif "strategic" in line.lower():
                current_section = "strategy"
            elif "time" in line.lower():
                current_section = "time_management"
            elif "endgame" in line.lower():
                current_section = "endgame"
            elif "resourceful" in line.lower():
                current_section = "resourcefulness"
            elif "advantage" in line.lower():
                current_section = "advantage"
            elif "study plan" in line.lower():
                current_section = "study_plan"
            elif "peer comparison" in line.lower():
                current_section = "peer_comparison"
            
            # Parse content based on section
            if current_section == "overall_performance":
                if "score:" in line.lower():
                    try:
                        feedback["overall_performance"]["score"] = int(line.split(":")[1].strip().split()[0])
                    except (ValueError, IndexError):
                        pass
                elif "strength:" in line.lower():
                    feedback["overall_performance"]["key_strengths"].append(line.split(":")[1].strip())
                elif "improve:" in line.lower():
                    feedback["overall_performance"]["areas_to_improve"].append(line.split(":")[1].strip())
                else:
                    feedback["overall_performance"]["interpretation"] += line + " "
            elif current_section == "peer_comparison":
                for category in ["overall", "tactics", "strategy"]:
                    if category in line.lower():
                        try:
                            percentile = int(re.search(r'\d+', line).group())
                            feedback["peer_comparison"][category]["percentile"] = percentile
                            feedback["peer_comparison"][category]["interpretation"] = line
                        except (AttributeError, ValueError):
                            pass
            elif current_section == "study_plan":
                if line.startswith("-") or line.startswith("•"):
                    if "exercise" in line.lower():
                        feedback["study_plan"]["exercises"].append(line[1:].strip())
                    else:
                        feedback["study_plan"]["focus_areas"].append(line[1:].strip())
            elif current_section:
                if line.startswith("-") or line.startswith("•"):
                    section = feedback.get(current_section)
                    if section and "suggestions" in section:
                        section["suggestions"].append(line[1:].strip())
                else:
                    section = feedback.get(current_section)
                    if section and "analysis" in section:
                        section["analysis"] += line + " "
        
        return feedback

    def _generate_fallback_feedback(self, game_analysis: List[Dict[str, Any]]) -> FeedbackData:
        """Generate basic feedback when AI generation fails."""
        feedback: FeedbackData = {
            "overall_performance": {
                "score": 65,
                "interpretation": "Your overall performance shows room for improvement",
                "key_strengths": ["Basic tactical awareness", "Time management"],
                "areas_to_improve": ["Opening preparation", "Endgame technique"]
            },
            "opening": {
                "analysis": "Standard opening moves with some inaccuracies",
                "suggestions": ["Study main lines of your chosen openings", "Focus on piece development"]
            },
            "middlegame": {
                "analysis": "Mixed performance in complex positions",
                "suggestions": ["Improve piece coordination", "Study pawn structure basics"]
            },
            "tactics": {
                "analysis": "Several tactical opportunities missed",
                "suggestions": ["Practice daily tactical puzzles", "Review critical positions"]
            },
            "strategy": {
                "analysis": "Basic strategic understanding demonstrated",
                "suggestions": ["Study positional chess concepts", "Improve long-term planning"]
            },
            "time_management": {
                "analysis": "Reasonable time usage with some pressure points",
                "suggestions": ["Practice time allocation", "Plan moves in opponent's time"]
            },
            "endgame": {
                "analysis": "Technical execution needs improvement",
                "suggestions": ["Study basic endgame principles", "Practice common endgame patterns"]
            },
            "resourcefulness": {
                "analysis": "Showed resilience in difficult positions",
                "suggestions": ["Practice finding defensive resources", "Study similar positions"]
            },
            "advantage": {
                "analysis": "Mixed success in converting advantages",
                "suggestions": ["Practice converting winning positions", "Study technique in better positions"]
            },
            "study_plan": {
                "focus_areas": ["Tactics", "Opening preparation", "Endgame technique"],
                "exercises": [
                    "Solve 10 tactical puzzles daily",
                    "Study one opening variation deeply",
                    "Practice basic endgame positions"
                ]
            },
            "peer_comparison": {
                "overall": {
                    "percentile": 50,
                    "interpretation": "Your performance is average compared to peers"
                },
                "tactics": {
                    "percentile": 55,
                    "interpretation": "Slightly above average tactical performance"
                },
                "strategy": {
                    "percentile": 45,
                    "interpretation": "Room for improvement in strategic play"
                }
            }
        }
        return feedback 