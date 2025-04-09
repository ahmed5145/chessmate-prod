import json
import logging
import os
import re
import statistics
import time
from collections import defaultdict
from typing import Any, Dict, List, Literal, Match, Optional, TypedDict, Union, cast
from urllib.parse import urlparse

import openai
import redis
from django.conf import settings
from django.core.cache import cache, caches
from django.core.exceptions import ValidationError
from openai import OpenAI

from .models import Game  # Add Game model import

logger = logging.getLogger(__name__)

# Initialize Redis connection
try:
    redis_url = settings.REDIS_URL
    url = urlparse(redis_url)

    redis_client = redis.Redis.from_url(
        url=redis_url, decode_responses=True, socket_timeout=5, socket_connect_timeout=5, retry_on_timeout=True
    )
    # Test connection
    redis_client.ping()
    logger.info("Successfully connected to Redis")
except (redis.ConnectionError, AttributeError) as e:
    logger.error(f"Failed to connect to Redis: {str(e)}")
    redis_client = None


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


SectionType = Literal[
    "overall_performance",
    "opening",
    "middlegame",
    "tactics",
    "strategy",
    "time_management",
    "endgame",
    "resourcefulness",
    "advantage",
]


class RateLimiter:
    def __init__(self, max_calls: int, time_window: int):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls: List[float] = []
        self._cleanup_old_calls()

    def can_make_request(self) -> bool:
        self._cleanup_old_calls()
        return len(self.calls) < self.max_calls

    def _cleanup_old_calls(self) -> None:
        current_time = time.time()
        self.calls = [call_time for call_time in self.calls if current_time - call_time < self.time_window]


class AIFeedbackGenerator:
    """Class to handle AI-powered feedback generation for chess games."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the feedback generator with OpenAI API key."""
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.openai_client = OpenAI(api_key=self.api_key)
        self.rate_limiter = RateLimiter(max_calls=50, time_window=60)  # 50 calls per minute
        self.cache = caches["default"]

    def _create_analysis_prompt(self, game_analysis: List[Dict[str, Any]]) -> str:
        """Create a detailed prompt for the AI based on game analysis."""
        summary = self._prepare_analysis_summary(game_analysis)

        prompt = f"""Analyze this chess game in detail:

Game Overview:
- Total Moves: {summary['total_moves']}
- Critical Positions: {len(summary.get('critical_moves', []))}
- Mistakes: {len(summary.get('mistakes', []))}
- Average Position Quality: {summary.get('avg_position_quality', 0):.1f}
- Opening: {summary.get('opening_name', 'Unknown')}

Performance Metrics:
- Accuracy: {summary.get('accuracy', 0):.1f}%
- Tactical Opportunities Found: {summary.get('tactical_success_rate', 0):.1f}%
- Position Understanding: {summary.get('positional_score', 0):.1f}%
- Time Management: {summary.get('time_management_score', 0):.1f}%

Provide comprehensive feedback on:
1. Overall Performance
- Evaluate the player's overall strategy and decision-making
- Identify key moments that influenced the game
- Assess the balance between tactical and positional play

2. Opening Phase
- Evaluate opening choice and execution
- Identify any significant deviations or improvements
- Suggest potential improvements in opening preparation

3. Middlegame
- Analyze tactical opportunities (both found and missed)
- Evaluate positional understanding and piece coordination
- Assess pawn structure management

4. Endgame
- Evaluate technical execution
- Identify critical decisions
- Suggest improvements in endgame technique

5. Time Management
- Analyze time usage in critical positions
- Evaluate decision-making under time pressure
- Suggest improvements in time management

6. Specific Recommendations
- Provide 3-5 concrete areas for improvement
- Suggest specific exercises or study areas
- Recommend relevant chess concepts to focus on

Format the response in clear sections with specific examples from the game.
Include move numbers and concrete variations where relevant.
Focus on actionable feedback that will help improve future performance."""

        return prompt

    def _generate_ai_feedback(self, game_analysis: List[Dict[str, Any]], game: Optional[Game] = None) -> Dict[str, Any]:
        try:
            # Check rate limit
            if not self.rate_limiter.can_make_request():
                logger.warning("OpenAI API rate limit reached, using fallback")
                return cast(Dict[str, Any], self._generate_fallback_feedback(game_analysis))

            # Try to get cached feedback if game exists
            if game is not None:
                cache_key = f"game_feedback_{game.pk}"
                cached_feedback = self.cache.get(cache_key)
                if cached_feedback:
                    return cached_feedback
            else:
                logger.warning("No game object provided, skipping cache")

            # Generate feedback using OpenAI
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a chess analysis expert."},
                    {"role": "user", "content": self._create_analysis_prompt(game_analysis)},
                ],
                temperature=0.7,
                max_tokens=1000,
                n=1,
            )

            feedback_text = response.choices[0].message.content.strip()

            # Calculate metrics and structure feedback
            feedback = cast(Dict[str, Any], self._parse_ai_response(feedback_text, game_analysis))

            # Cache the feedback if game exists
            if game is not None:
                cache_key = f"game_feedback_{game.pk}"
                self.cache.set(cache_key, feedback, timeout=3600)  # Cache for 1 hour

            return feedback

        except openai.RateLimitError:
            logger.warning("OpenAI API rate limit exceeded, using fallback")
            return cast(Dict[str, Any], self._generate_fallback_feedback(game_analysis))
        except Exception as e:
            logger.error(f"Error generating AI feedback: {str(e)}")
            return cast(Dict[str, Any], self._generate_fallback_feedback(game_analysis))

    def _prepare_analysis_summary(self, game_analysis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare a summary of the game analysis for the AI prompt."""
        summary: Dict[str, Union[int, List[Dict[str, Any]]]] = {
            "total_moves": len(game_analysis),
            "critical_moves": [],
            "mistakes": [],
            "positional_notes": [],
            "time_management": [],
        }

        for move in game_analysis:
            if move.get("is_critical"):
                critical_moves = summary.get("critical_moves", [])
                if isinstance(critical_moves, list):
                    critical_moves.append(
                        {"move_number": move["move_number"], "move": move["move"], "evaluation": move["score"]}
                    )

            if move.get("is_mistake"):
                mistakes = summary.get("mistakes", [])
                if isinstance(mistakes, list):
                    mistakes.append(
                        {
                            "move_number": move["move_number"],
                            "move": move["move"],
                            "evaluation_drop": move.get("evaluation_drop", 0),
                        }
                    )

            if move.get("time_spent", 0) > 60:  # More than 60 seconds spent
                time_management = summary.get("time_management", [])
                if isinstance(time_management, list):
                    time_management.append({"move_number": move["move_number"], "time_spent": move["time_spent"]})

        return summary

    def _parse_ai_response(self, response_text: str, game_analysis: List[Dict[str, Any]]) -> FeedbackData:
        """Parse AI response into structured feedback data."""
        try:
            sections = self._extract_sections(response_text)

            feedback: FeedbackData = {
                "overall_performance": {"evaluation": "", "key_moments": [], "strengths": [], "weaknesses": []},
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
                    "percentile": 0,
                    "relative_strength": "",
                    "areas_above_peers": [],
                    "areas_below_peers": [],
                },
            }

            # Process each section
            for section, content in sections.items():
                self._process_section_content(section, content, feedback)

            # Add statistical metrics
            metrics = self._prepare_analysis_summary(game_analysis)
            feedback["metrics"] = metrics

            return feedback

        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}")
            return self._get_default_feedback()

    def _process_section_content(self, section: str, content: List[str], feedback: FeedbackData) -> None:
        """Process content for each feedback section."""
        try:
            if not content:
                return

            main_content = []
            suggestions = []
            current_list = main_content

            for line in content:
                line = line.strip()
                if not line:
                    continue

                # Check for suggestion markers
                if line.lower().startswith(("suggestion:", "recommend:", "improve:", "- ", "• ")):
                    current_list = suggestions
                    line = line.lstrip("- •").strip()
                    if ":" in line:
                        line = line.split(":", 1)[1].strip()
                else:
                    current_list = main_content

                current_list.append(line)

            # Map content to appropriate section
            if section.lower() == "overall performance":
                feedback["overall_performance"]["evaluation"] = "\n".join(main_content)
                self._extract_strengths_weaknesses(main_content, feedback)
            elif section.lower() in feedback:
                section_key = section.lower()
                feedback[section_key]["analysis"] = "\n".join(main_content)
                feedback[section_key]["suggestions"] = suggestions
            elif section.lower() == "study plan":
                for line in content:
                    line = line.strip()
                    if "exercise" in line.lower():
                        feedback["study_plan"]["exercises"].append(line)
                else:
                    feedback["study_plan"]["focus_areas"].append(line)

        except Exception as e:
            logger.error(f"Error processing section {section}: {str(e)}")

    def _extract_strengths_weaknesses(self, content: List[str], feedback: FeedbackData) -> None:
        """Extract strengths and weaknesses from overall performance content."""
        strengths = []
        weaknesses = []
        current_list = None

        for line in content:
            lower_line = line.lower()
            if "strength" in lower_line or "positive" in lower_line:
                current_list = strengths
            elif "weakness" in lower_line or "improvement" in lower_line:
                current_list = weaknesses
            elif current_list is not None and line.strip():
                current_list.append(line.strip())

        feedback["overall_performance"]["strengths"] = strengths
        feedback["overall_performance"]["weaknesses"] = weaknesses

    def _generate_fallback_feedback(self, game_analysis: List[Dict[str, Any]]) -> FeedbackData:
        """Generate basic feedback when AI generation fails."""
        # Calculate phase-specific metrics
        opening_moves = game_analysis[: min(10, len(game_analysis))]
        middlegame_moves = game_analysis[min(10, len(game_analysis)) : min(30, len(game_analysis))]
        endgame_moves = game_analysis[min(30, len(game_analysis)) :]

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
                    "Basic positional understanding",
                ],
                "areas_to_improve": [
                    "Opening preparation depth",
                    "Endgame technique refinement",
                    "Tactical pattern recognition",
                ],
            },
            "opening": {
                "analysis": f"Opening play shows {opening_accuracy}% accuracy. {'Strong opening fundamentals' if opening_accuracy > 75 else 'Room for improvement in opening principles'}",
                "suggestions": [
                    "Study main lines of your chosen openings",
                    "Focus on piece development coordination",
                    "Pay attention to pawn structure formation",
                    "Practice time management in the opening phase",
                ],
            },
            "middlegame": {
                "analysis": f"Middlegame performance at {middlegame_accuracy}% accuracy. {'Good strategic understanding' if middlegame_accuracy > 75 else 'Strategic understanding needs development'}",
                "suggestions": [
                    "Improve piece coordination",
                    "Study typical pawn structures",
                    "Practice planning and evaluation",
                    "Work on identifying critical moments",
                ],
            },
            "tactics": {
                "analysis": f"Tactical awareness at {tactics_score}%. Found {missed_wins} missed tactical opportunities",
                "suggestions": [
                    "Practice daily tactical puzzles",
                    "Study common tactical patterns",
                    "Review critical positions",
                    "Work on calculation accuracy",
                ],
            },
            "strategy": {
                "analysis": "Basic strategic understanding demonstrated with room for improvement",
                "suggestions": [
                    "Study positional chess concepts",
                    "Practice pawn structure analysis",
                    "Learn typical strategic plans",
                    "Improve long-term planning skills",
                ],
            },
            "time_management": {
                "analysis": "Reasonable time usage with some pressure points noted",
                "suggestions": [
                    "Practice time allocation per phase",
                    "Plan moves during opponent's time",
                    "Improve decision-making speed",
                    "Set phase-specific time budgets",
                ],
            },
            "endgame": {
                "analysis": f"Endgame technique shows {endgame_accuracy}% accuracy. {'Strong technical skills' if endgame_accuracy > 75 else 'Technical execution needs improvement'}",
                "suggestions": [
                    "Study fundamental endgame positions",
                    "Practice king activation",
                    "Improve pawn endgame technique",
                    "Work on technical precision",
                ],
            },
            "resourcefulness": {
                "analysis": "Demonstrated basic defensive skills and counter-attacking abilities",
                "suggestions": [
                    "Practice finding defensive resources",
                    "Study prophylactic thinking",
                    "Improve counter-attacking skills",
                    "Learn fortress positions",
                ],
            },
            "advantage": {
                "analysis": "Mixed success in converting advantageous positions",
                "suggestions": [
                    "Practice converting winning positions",
                    "Study technique in better positions",
                    "Improve prophylaxis in good positions",
                    "Work on maintaining pressure",
                ],
            },
            "study_plan": {
                "focus_areas": [
                    "Opening principles and development",
                    "Tactical pattern recognition",
                    "Endgame fundamentals",
                    "Time management",
                ],
                "exercises": [
                    "Solve 10 tactical puzzles daily",
                    "Study one opening variation deeply",
                    "Practice basic endgame positions",
                    "Analyze games with time stamps",
                ],
            },
            "peer_comparison": {
                "overall": {"percentile": 50, "interpretation": "Your performance is average compared to peers"},
                "tactics": {"percentile": 55, "interpretation": "Slightly above average tactical performance"},
                "strategy": {"percentile": 45, "interpretation": "Room for improvement in strategic play"},
            },
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

        for i in range(len(moves) - 1):
            try:
                current_move = moves[i]
                next_move = moves[i + 1]

                # Ensure we have valid score values
                current_eval = current_move.get("score")
                next_eval = next_move.get("score")

                if current_eval is None or next_eval is None:
                    continue

                # Convert string scores to integers if needed
                if isinstance(current_eval, str):
                    try:
                        current_eval = int(current_eval)
                    except (ValueError, TypeError):
                        continue

                if isinstance(next_eval, str):
                    try:
                        next_eval = int(next_eval)
                    except (ValueError, TypeError):
                        continue

                # Only process if both evaluations are numeric
                if isinstance(current_eval, (int, float)) and isinstance(next_eval, (int, float)):
                    # Detect tactical opportunities
                    if abs(next_eval - current_eval) > 200:
                        tactical_opportunities += 1
                        if next_eval > current_eval:
                            successful_tactics += 1
                        else:
                            missed_wins += 1
            except (IndexError, TypeError, ValueError) as e:
                logger.warning(f"Error calculating tactical metrics: {str(e)}")
                continue

        tactics_score = (successful_tactics / max(1, tactical_opportunities)) * 100
        return round(tactics_score, 1), missed_wins

    def _split_game_phases(
        self, game_analysis: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Split game analysis into opening, middlegame, and endgame phases safely."""
        if not isinstance(game_analysis, list):
            game_analysis = list(game_analysis)

        num_moves = len(game_analysis)
        opening_end = min(20, num_moves // 3)
        endgame_start = max(0, num_moves - min(20, num_moves // 3))

        opening = game_analysis[:opening_end] if opening_end > 0 else []
        endgame = game_analysis[endgame_start:] if endgame_start < num_moves else []
        middlegame = game_analysis[opening_end:endgame_start] if num_moves > 40 else []

        return opening, middlegame, endgame

    def generate_batch_feedback(
        self, games_analysis: List[Dict[str, Any]], player_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate feedback for a batch of games."""
        try:
            # Validate input
            if not isinstance(games_analysis, list):
                logger.error(f"games_analysis must be a list, got {type(games_analysis)}")
                return self._get_default_feedback()

            logger.debug(f"Processing {len(games_analysis)} games")

            # Calculate aggregate metrics
            metrics = self._aggregate_metrics(games_analysis)

            # Generate AI feedback using a single OpenAI call
            try:
                prompt = self._create_batch_analysis_prompt(metrics, player_profile)
                ai_response = self._make_openai_request(prompt)
                if ai_response:
                    feedback = self._parse_batch_ai_response(ai_response, metrics)
                    feedback["source"] = "ai"
                    return feedback
            except Exception as e:
                logger.error(f"Error generating AI feedback: {str(e)}")

            # Fallback to statistical feedback
            return self._generate_statistical_batch_feedback(metrics)

        except Exception as e:
            logger.error(f"Error generating batch feedback: {str(e)}")
            return self._get_default_feedback()

    def _create_batch_analysis_prompt(self, metrics: Dict[str, Any], player_profile: Dict[str, Any]) -> str:
        """Create a prompt for batch analysis."""
        return f"""Analyze the following chess games for player {player_profile.get('username', 'unknown')}:

Overall Performance:
- Total Games: {metrics['total_games']}
- Average Accuracy: {metrics['overall']['accuracy']}%
- Win Rate: {metrics['overall']['win_rate']}%
- Time Controls: {metrics['time_management']['time_controls']}

Tactical Performance:
- Tactical Opportunities Found: {metrics['tactics']['opportunities']}
- Successful Tactics: {metrics['tactics']['successful']}
- Success Rate: {metrics['tactics']['success_rate']}%

Opening Repertoire:
{metrics['openings']['summary']}

Common Patterns:
{metrics['patterns']['summary']}

Time Management:
- Average Time per Move: {metrics['time_management']['average_time']}s
- Time Pressure Frequency: {metrics['time_management']['time_pressure_percentage']}%

Based on this data, provide:
1. A comprehensive analysis of the player's strengths and weaknesses
2. Specific patterns in their play style
3. Concrete suggestions for improvement
4. A personalized study plan
5. Areas where they show the most promise
6. Critical aspects that need immediate attention

Format the response as a structured analysis with clear sections."""

    def _parse_batch_ai_response(self, response: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the AI response for batch analysis."""
        try:
            # Extract sections from AI response
            sections = self._extract_sections(response)

            return {
                "overall_metrics": {
                    "overall": metrics["overall"],
                    "tactics": metrics["tactics"],
                    "time_management": metrics["time_management"],
                },
                "pattern_analysis": {
                    "tactical_patterns": metrics["patterns"]["tactical"],
                    "positional_patterns": metrics["patterns"]["positional"],
                    "endgame_patterns": metrics["patterns"]["endgame"],
                    "games_analyzed": metrics["total_games"],
                },
                "ai_analysis": {
                    "strengths": sections.get("strengths", []),
                    "weaknesses": sections.get("weaknesses", []),
                    "patterns": sections.get("patterns", []),
                    "suggestions": sections.get("suggestions", []),
                    "study_plan": sections.get("study_plan", []),
                    "critical_areas": sections.get("critical_areas", []),
                },
                "player_profile": {
                    "username": metrics["player_profile"]["username"],
                    "total_games": metrics["total_games"],
                },
            }
        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}")
            return self._generate_statistical_batch_feedback(metrics)

    def _extract_sections(self, text: str) -> Dict[str, List[str]]:
        """Extract sections from AI response text."""
        sections = {
            "strengths": [],
            "weaknesses": [],
            "patterns": [],
            "suggestions": [],
            "study_plan": [],
            "critical_areas": [],
        }

        current_section = None
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Check for section headers
            lower_line = line.lower()
            if "strength" in lower_line:
                current_section = "strengths"
            elif "weakness" in lower_line:
                current_section = "weaknesses"
            elif "pattern" in lower_line:
                current_section = "patterns"
            elif "suggest" in lower_line:
                current_section = "suggestions"
            elif "study plan" in lower_line:
                current_section = "study_plan"
            elif "critical" in lower_line:
                current_section = "critical_areas"
            elif current_section and line.startswith("-"):
                # Add bullet points to current section
                sections[current_section].append(line[1:].strip())

        return sections

    def _aggregate_metrics(self, games_analysis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate metrics from multiple games."""
        total_games = len(games_analysis)
        if total_games == 0:
            return self._get_default_feedback()

        # Initialize counters
        total_moves = 0
        total_accuracy = 0
        wins = 0
        time_controls = defaultdict(int)
        openings = defaultdict(int)
        tactical_opportunities = 0
        successful_tactics = 0
        total_time = 0
        time_pressure_moves = 0

        # Process each game
        for game in games_analysis:
            analysis = game["analysis"]
            metadata = game["metadata"]

            # Count wins
            if metadata["result"] == "win":
                wins += 1

            # Track time controls
            time_controls[metadata["time_control"]] += 1

            # Process moves
            moves = analysis["results"]
            total_moves += len(moves)

            for move in moves:
                # Accuracy
                if "accuracy" in move:
                    total_accuracy += move["accuracy"]

                # Tactics
                if move.get("is_tactical"):
                    tactical_opportunities += 1
                    if move.get("evaluation_improvement", 0) > 0:
                        successful_tactics += 1

                # Time management
                time_spent = float(move.get("time_spent", 0.0))
                if time_spent > 0.0:
                    total_time += time_spent
                    if time_spent < 10.0:
                        time_pressure_moves += 1

        # Calculate averages and rates
        avg_accuracy = total_accuracy / total_moves if total_moves > 0 else 0
        win_rate = (wins / total_games) * 100
        avg_time = total_time / total_moves if total_moves > 0 else 0
        time_pressure_percentage = (time_pressure_moves / total_moves * 100) if total_moves > 0 else 0
        tactical_success_rate = (successful_tactics / tactical_opportunities * 100) if tactical_opportunities > 0 else 0

        return {
            "total_games": total_games,
            "overall": {"accuracy": round(avg_accuracy, 2), "win_rate": round(win_rate, 2), "total_moves": total_moves},
            "tactics": {
                "opportunities": tactical_opportunities,
                "successful": successful_tactics,
                "success_rate": round(tactical_success_rate, 2),
            },
            "time_management": {
                "average_time": round(avg_time, 2),
                "time_pressure_moves": time_pressure_moves,
                "time_pressure_percentage": round(time_pressure_percentage, 2),
                "time_controls": dict(time_controls),
            },
            "openings": {"summary": self._summarize_openings(openings)},
            "patterns": {
                "summary": self._analyze_patterns(games_analysis),
                "tactical": self._extract_tactical_patterns(games_analysis),
                "positional": self._extract_positional_patterns(games_analysis),
                "endgame": self._extract_endgame_patterns(games_analysis),
            },
            "player_profile": {
                "username": games_analysis[0]["metadata"].get("username", "unknown"),
                "total_games": total_games,
            },
        }

    def _summarize_openings(self, openings: Dict[str, int]) -> str:
        """Create a summary of opening choices."""
        if not openings:
            return "No opening data available"

        sorted_openings = sorted(openings.items(), key=lambda x: x[1], reverse=True)
        summary = []
        for opening, count in sorted_openings[:5]:
            percentage = (count / sum(openings.values())) * 100
            summary.append(f"{opening}: {percentage:.1f}% ({count} games)")

        return "\n".join(summary)

    def _analyze_patterns(self, games_analysis: List[Dict[str, Any]]) -> str:
        """Analyze patterns across all games."""
        patterns = {"tactical": defaultdict(int), "positional": defaultdict(int), "mistakes": defaultdict(int)}

        for game in games_analysis:
            analysis = game["analysis"]
            for move in analysis["results"]:
                if move.get("tactical_pattern"):
                    patterns["tactical"][move["tactical_pattern"]] += 1
                if move.get("positional_theme"):
                    patterns["positional"][move["positional_theme"]] += 1
                if move.get("mistake_type"):
                    patterns["mistakes"][move["mistake_type"]] += 1

        return self._format_pattern_summary(patterns)

    def _format_pattern_summary(self, patterns: Dict[str, Dict[str, int]]) -> str:
        """Format pattern analysis into a readable summary."""
        summary = []
        for category, items in patterns.items():
            if items:
                sorted_items = sorted(items.items(), key=lambda x: x[1], reverse=True)
                top_items = sorted_items[:3]
                summary.append(f"{category.title()}:")
                for item, count in top_items:
                    summary.append(f"- {item}: {count} occurrences")

        return "\n".join(summary) if summary else "No significant patterns found"

    def _generate_statistical_batch_feedback(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate statistical feedback for a batch of games."""
        # Implementation of statistical feedback generation logic
        # This is a placeholder and should be replaced with the actual implementation
        return self._get_default_feedback()

    def _get_default_feedback(self) -> Dict[str, Any]:
        """Return default feedback structure."""
        return {
            "overall_metrics": {
                "overall": {
                    "total_moves": 0,
                    "accuracy": 0,
                    "consistency_score": 0,
                    "mistakes": 0,
                    "blunders": 0,
                    "inaccuracies": 0,
                    "critical_positions": 0,
                },
                "phases": {
                    "opening": {"accuracy": 0, "moves": 0},
                    "middlegame": {"accuracy": 0, "moves": 0},
                    "endgame": {"accuracy": 0, "moves": 0},
                },
                "tactics": {"opportunities": 0, "successful": 0, "success_rate": 0},
                "time_management": {"average_time": 0, "time_pressure_moves": 0, "time_pressure_percentage": 0},
                "position_assessment": {"winning_positions": 0, "losing_positions": 0, "critical_positions": 0},
            }
        }

    def _calculate_game_accuracy(self, game_analysis: List[Dict[str, Any]]) -> float:
        """Calculate accuracy for a single game."""
        if not game_analysis:
            return 0.0

        total_eval = 0
        count = 0
        for move in game_analysis:
            if move.get("eval_diff") is not None:
                total_eval += abs(move["eval_diff"])
                count += 1

        if count == 0:
            return 0.0

        avg_eval_diff = total_eval / count
        accuracy = max(0, 100 - (avg_eval_diff * 10))  # Convert eval diff to accuracy
        return round(accuracy, 2)

    def _analyze_common_mistakes(self, mistakes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze patterns in mistakes."""
        if not mistakes:
            return []

        patterns = defaultdict(list)
        for mistake in mistakes:
            move_type = "mistake" if mistake.get("is_mistake") else "blunder"
            eval_diff = mistake.get("eval_diff", 0)
            position = mistake.get("position", "")

            patterns[move_type].append(
                {"eval_diff": eval_diff, "position": position, "move_number": mistake.get("move_number", 0)}
            )

        return [{"type": k, "instances": v} for k, v in patterns.items()]

    def _calculate_accuracy_trend(self, accuracies: List[float]) -> str:
        """Calculate trend in accuracy across games."""
        if len(accuracies) < 2:
            return "insufficient_data"

        # Calculate moving average
        window = min(5, len(accuracies))
        moving_avg = []
        for i in range(len(accuracies) - window + 1):
            avg = sum(accuracies[i : i + window]) / window
            moving_avg.append(avg)

        if len(moving_avg) < 2:
            return "stable"

        # Calculate trend
        first_avg = sum(moving_avg[:3]) / 3 if len(moving_avg) >= 3 else moving_avg[0]
        last_avg = sum(moving_avg[-3:]) / 3 if len(moving_avg) >= 3 else moving_avg[-1]

        diff = last_avg - first_avg
        if diff > 2:
            return "improving"
        elif diff < -2:
            return "declining"
        else:
            return "stable"
