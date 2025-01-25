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

1. Overall Performance:
   - Score (0-100)
   - Key strengths and weaknesses
   - Areas for immediate improvement

2. Opening Phase (moves 1-10):
   - Opening choice evaluation
   - Development patterns
   - Pawn structure formation
   - Time usage in opening
   - Common mistakes or improvements
   - Specific recommendations for opening study

3. Middlegame Phase:
   - Positional understanding
   - Piece coordination
   - Pawn structure management
   - Strategic planning
   - Attack/defense balance
   - Common patterns to improve

4. Endgame Phase:
   - Technical execution
   - King activity
   - Pawn handling
   - Piece coordination
   - Time management
   - Critical improvements needed

5. Tactical Elements:
   - Tactical pattern recognition
   - Calculation accuracy
   - Missed opportunities
   - Common tactical themes
   - Suggested tactical exercises

6. Strategic Understanding:
   - Long-term planning
   - Piece placement
   - Pawn structure decisions
   - Strategic patterns to study

7. Time Management:
   - Phase-by-phase time usage
   - Critical time decisions
   - Time pressure handling
   - Specific time management tips

8. Resourcefulness:
   - Defensive techniques
   - Counter-attacking skills
   - Finding resources in tough positions
   - Improvement suggestions

9. Advantage Conversion:
   - Technical precision
   - Converting winning positions
   - Maintaining pressure
   - Common conversion patterns

10. Peer Comparison:
    - Performance vs similar rated players
    - Phase-by-phase comparison
    - Tactical/strategic balance

11. Detailed Study Plan:
    - Phase-specific exercises
    - Opening repertoire suggestions
    - Tactical patterns to study
    - Endgame principles to master
    - Time management drills

For each section, provide:
- Detailed analysis with specific examples
- Concrete, actionable suggestions
- Numerical scores where applicable
- Common patterns and anti-patterns
- Specific resources or exercises

Focus on providing actionable feedback that addresses each phase of the game distinctly while maintaining a holistic view of improvement areas.
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
        # Calculate phase-specific metrics
        opening_moves = game_analysis[:min(10, len(game_analysis))]
        middlegame_moves = game_analysis[min(10, len(game_analysis)):min(30, len(game_analysis))]
        endgame_moves = game_analysis[min(30, len(game_analysis)):]

        # Calculate accuracies for each phase
        opening_accuracy = self._calculate_phase_accuracy(opening_moves)
        middlegame_accuracy = self._calculate_phase_accuracy(middlegame_moves)
        endgame_accuracy = self._calculate_phase_accuracy(endgame_moves)

        # Calculate tactical metrics
        tactics_score, missed_wins = self._calculate_tactical_metrics(game_analysis)

        feedback: FeedbackData = {
            "overall_performance": {
                "score": 65,
                "interpretation": "Your overall performance shows both strengths and areas for improvement",
                "key_strengths": [
                    "Basic tactical awareness",
                    "Time management fundamentals",
                    "Basic positional understanding"
                ],
                "areas_to_improve": [
                    "Opening preparation depth",
                    "Endgame technique refinement",
                    "Tactical pattern recognition"
                ]
            },
            "opening": {
                "analysis": f"Opening play shows {opening_accuracy}% accuracy. {'Strong opening fundamentals' if opening_accuracy > 75 else 'Room for improvement in opening principles'}",
                "suggestions": [
                    "Study main lines of your chosen openings",
                    "Focus on piece development coordination",
                    "Pay attention to pawn structure formation",
                    "Practice time management in the opening phase"
                ]
            },
            "middlegame": {
                "analysis": f"Middlegame performance at {middlegame_accuracy}% accuracy. {'Good strategic understanding' if middlegame_accuracy > 75 else 'Strategic understanding needs development'}",
                "suggestions": [
                    "Improve piece coordination",
                    "Study typical pawn structures",
                    "Practice planning and evaluation",
                    "Work on identifying critical moments"
                ]
            },
            "tactics": {
                "analysis": f"Tactical awareness at {tactics_score}%. Found {missed_wins} missed tactical opportunities",
                "suggestions": [
                    "Practice daily tactical puzzles",
                    "Study common tactical patterns",
                    "Review critical positions",
                    "Work on calculation accuracy"
                ]
            },
            "strategy": {
                "analysis": "Basic strategic understanding demonstrated with room for improvement",
                "suggestions": [
                    "Study positional chess concepts",
                    "Practice pawn structure analysis",
                    "Learn typical strategic plans",
                    "Improve long-term planning skills"
                ]
            },
            "time_management": {
                "analysis": "Reasonable time usage with some pressure points noted",
                "suggestions": [
                    "Practice time allocation per phase",
                    "Plan moves during opponent's time",
                    "Improve decision-making speed",
                    "Set phase-specific time budgets"
                ]
            },
            "endgame": {
                "analysis": f"Endgame technique shows {endgame_accuracy}% accuracy. {'Strong technical skills' if endgame_accuracy > 75 else 'Technical execution needs improvement'}",
                "suggestions": [
                    "Study fundamental endgame positions",
                    "Practice king activation",
                    "Improve pawn endgame technique",
                    "Work on technical precision"
                ]
            },
            "resourcefulness": {
                "analysis": "Demonstrated basic defensive skills and counter-attacking abilities",
                "suggestions": [
                    "Practice finding defensive resources",
                    "Study prophylactic thinking",
                    "Improve counter-attacking skills",
                    "Learn fortress positions"
                ]
            },
            "advantage": {
                "analysis": "Mixed success in converting advantageous positions",
                "suggestions": [
                    "Practice converting winning positions",
                    "Study technique in better positions",
                    "Improve prophylaxis in good positions",
                    "Work on maintaining pressure"
                ]
            },
            "study_plan": {
                "focus_areas": [
                    "Opening principles and development",
                    "Tactical pattern recognition",
                    "Endgame fundamentals",
                    "Time management"
                ],
                "exercises": [
                    "Solve 10 tactical puzzles daily",
                    "Study one opening variation deeply",
                    "Practice basic endgame positions",
                    "Analyze games with time stamps"
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

    def _calculate_phase_accuracy(self, moves: List[Dict[str, Any]]) -> float:
        """Calculate accuracy for a specific phase of the game."""
        if not moves:
            return 65.0
        good_moves = sum(1 for move in moves if abs(move.get("score", 0)) < 100)
        return round((good_moves / len(moves)) * 100, 1)

    def _calculate_tactical_metrics(self, moves: List[Dict[str, Any]]) -> tuple[float, int]:
        """Calculate tactical score and missed wins."""
        if not moves:
            return 65.0, 0
        
        tactical_opportunities = 0
        successful_tactics = 0
        missed_wins = 0
        
        for i, move in enumerate(moves):
            current_eval = move.get("score", 0)
            next_eval = moves[i + 1].get("score", 0) if i < len(moves) - 1 else current_eval
            
            # Detect tactical opportunities
            if abs(next_eval - current_eval) > 200:
                tactical_opportunities += 1
                if next_eval > current_eval:
                    successful_tactics += 1
                else:
                    missed_wins += 1
        
        tactics_score = (successful_tactics / max(1, tactical_opportunities)) * 100
        return round(tactics_score, 1), missed_wins