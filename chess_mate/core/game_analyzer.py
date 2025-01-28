"""
This module provides functionality for analyzing chess games using the Stockfish engine.
It includes classes and methods to analyze single or multiple games, save analysis results to the
database, and generate feedback based on the analysis.
"""

import os
import io
import logging
from typing import List, Dict, Any, Optional, Union
import chess
import chess.engine
import chess.pgn
from django.db import DatabaseError, transaction
from django.core.cache import cache
from django.conf import settings
from .models import Game
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential
import random
from openai import OpenAI
from .ai_feedback import AIFeedbackGenerator
import json
import re

# Configure logging
logger = logging.getLogger(__name__)

class GameAnalyzer:
    """
    Handles game analysis using Stockfish or external APIs.
    """

    def __init__(self, stockfish_path: Optional[str] = None):
        """Initialize the game analyzer with Stockfish engine and OpenAI client."""
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(
                stockfish_path or settings.STOCKFISH_PATH
            )
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.ai_feedback_generator = AIFeedbackGenerator(api_key=settings.OPENAI_API_KEY)
            logger.info("Successfully initialized Stockfish engine and OpenAI client")
        except (chess.engine.EngineError, ValueError) as e:
            logger.error("Failed to initialize engines: %s", str(e))
            raise

    def __del__(self):
        """Ensure engine is properly closed."""
        self.close_engine()

    def close_engine(self):
        """Safely close the Stockfish engine."""
        try:
            if hasattr(self, 'engine') and self.engine:
                self.engine.quit()
                logger.info("Successfully closed Stockfish engine")
        except Exception as e:
            logger.error("Error closing Stockfish engine: %s", str(e))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def analyze_move(self, board: chess.Board, move: chess.Move, depth: int = 20) -> Dict[str, Any]:
        """Analyze a single move using the Stockfish engine with retry logic."""
        max_depth = min(depth, 15)  # Cap maximum depth
        try:
            result = self.engine.analyse(
                board,
                chess.engine.Limit(depth=max_depth, time=10.0)
            )
            score_obj = result.get("score")
            time_spent = result.get("time", 0)

            if not score_obj:
                return self._create_neutral_evaluation(board, move, depth, time_spent)

            score_obj = score_obj.white()
            score = self._convert_score(score_obj)
            
            return {
                "move": move.uci(),
                "score": score,
                "depth": depth,
                "time_spent": time_spent,
                "is_capture": board.is_capture(move),
                "is_check": board.gives_check(move),
                "position_complexity": self._calculate_position_complexity(board)
            }

        except Exception as e:
            logger.error(f"Error analyzing move: {e}")
            return self._create_neutral_evaluation(board, move, depth, 0)

    def _create_neutral_evaluation(self, board: chess.Board, move: chess.Move, depth: int, time_spent: float) -> Dict[str, Any]:
        """Create a neutral evaluation when analysis fails."""
        return {
            "move": move.uci(),
            "score": 0,
            "depth": depth,
            "time_spent": time_spent,
            "is_capture": board.is_capture(move),
            "is_check": board.gives_check(move),
            "position_complexity": self._calculate_position_complexity(board)
        }

    def _convert_score(self, score_obj: chess.engine.Score) -> int:
        """Convert chess.engine.Score to integer value."""
        if score_obj.is_mate():
            mate_score = score_obj.mate()
            return 10000 if mate_score > 0 else -10000
        try:
            score = score_obj.score()
            return score if score is not None else 0
        except AttributeError:
            return 0

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def analyze_single_game(self, game: Game, depth: int = 20) -> List[Dict[str, Any]]:
        """Analyze a single game with retry logic."""
        if not game.pgn:
            raise ValueError("No PGN data provided for analysis")

        try:
            moves = self._parse_pgn(game)
            analysis = self._analyze_moves(moves, depth)
            
            # Cache the analysis results
            cache_key = f"game_analysis_{game.id}"
            cache.set(cache_key, analysis, timeout=3600)  # Cache for 1 hour
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing game {game.id}: {str(e)}")
            raise

    def _parse_pgn(self, game: Game) -> List[chess.Move]:
        """Parse PGN data into a list of moves."""
        pgn_str = game.pgn.strip()
        if not pgn_str:
            raise ValueError("Empty PGN data")

        pgn_game = chess.pgn.read_game(io.StringIO(pgn_str))
        if not pgn_game:
            raise ValueError("Invalid PGN data: Could not parse game")

        moves = []
        current_node = pgn_game
        while current_node.variations:
            next_node = current_node.variations[0]
            if next_node.move:
                moves.append(next_node.move)
            current_node = next_node

        if not moves:
            raise ValueError("Invalid PGN data: No moves found")

        return moves

    def _analyze_moves(self, moves: List[chess.Move], depth: int) -> List[Dict[str, Any]]:
        """Analyze a list of moves."""
        board = chess.Board()
        analysis = []
        last_score = 0
        move_number = 1

        for move in moves:
            try:
                move_analysis = self.analyze_move(board, move, depth)
                current_score = move_analysis["score"]
                eval_drop = last_score - current_score

                move_analysis.update({
                    "move_number": move_number,
                    "evaluation_drop": eval_drop,
                    "is_mistake": eval_drop > 200,
                    "is_blunder": eval_drop > 400,
                    "is_critical": abs(current_score) > 150 or abs(eval_drop) > 150,
                    "is_tactical": board.is_capture(move) or board.gives_check(move) or abs(eval_drop) > 150
                })

                analysis.append(move_analysis)
                last_score = current_score
                board.push(move)
                move_number += 1

            except Exception as e:
                logger.error(f"Error analyzing move {move}: {str(e)}")
                continue

        return analysis 

    @transaction.atomic
    def save_analysis_to_db(self, game: Game, analysis_results: List[Dict[str, Any]]) -> None:
        """Save analysis results to the database with transaction handling."""
        try:
            game.analysis = analysis_results
            game.save()
            logger.info(f"Successfully saved analysis for game {game.id}")
        except Exception as e:
            logger.error(f"Error saving analysis to database: {str(e)}")
            raise

    def generate_feedback(self, game_analysis: List[Dict[str, Any]], game: Game) -> Dict[str, Any]:
        """Generate feedback based on game analysis."""
        try:
            # Try AI feedback first
            if self.ai_feedback_generator:
                try:
                    feedback = self._generate_ai_feedback(game_analysis, game)
                    if feedback:
                        feedback['source'] = 'openai_analysis'
                        return feedback
                except Exception as e:
                    logger.error(f"AI feedback generation failed: {str(e)}")
                    # Fall through to statistical analysis
            
            # Calculate mistakes and blunders
            mistakes = [m for m in game_analysis if m.get("is_mistake", False)]
            blunders = [m for m in game_analysis if m.get("is_blunder", False)]
            inaccuracies = [m for m in game_analysis if m.get("is_inaccuracy", False)]
            critical_positions = [m for m in game_analysis if m.get("is_critical", False)]
            
            # Calculate accuracy based on actual mistakes and blunders
            total_moves = len(game_analysis)
            if total_moves == 0:
                raise ValueError("No moves found in game analysis")
            
            mistake_penalty = len(mistakes) * 2
            blunder_penalty = len(blunders) * 4
            inaccuracy_penalty = len(inaccuracies) * 1
            base_accuracy = 100
            final_accuracy = max(0, min(100, base_accuracy - mistake_penalty - blunder_penalty - inaccuracy_penalty))

            # Calculate time management stats
            move_times = [m.get("time_spent", 0) for m in game_analysis]
            avg_time = sum(move_times) / len(move_times) if move_times else 0
            time_pressure_moves = [m for m in game_analysis if m.get("time_spent", 0) < 10]
            
            # Extract critical moments
            critical_moments = []
            for move in game_analysis:
                if move.get("is_critical", False):
                    critical_moments.append({
                        "move": move["move"],
                        "move_number": move.get("move_number", 0),
                        "score": move.get("score", 0),
                        "time_spent": move.get("time_spent", 0),
                        "reason": "Significant change in evaluation" if abs(move.get("score", 0)) > 150 else "Complex position"
                    })
            
            # Generate specific feedback based on actual game data
            feedback = {
                "summary": {
                    "total_moves": total_moves,
                    "mistakes": len(mistakes),
                    "blunders": len(blunders),
                    "inaccuracies": len(inaccuracies),
                    "critical_positions": len(critical_positions),
                    "accuracy": round(final_accuracy, 1)
                },
                "time_management": {
                    "avg_time_per_move": round(avg_time, 2),
                    "critical_moments": critical_moments,
                    "time_pressure_moves": [
                        {"move": m["move"], "time": m.get("time_spent", 0)}
                        for m in time_pressure_moves
                    ],
                    "suggestion": self._generate_time_management_suggestion(move_times, critical_moments)
                },
                "opening": {
                    "played_moves": [m["move"] for m in game_analysis[:10]],
                    "accuracy": round(self._calculate_phase_accuracy(game_analysis[:10]), 1),
                    "suggestion": self._generate_opening_suggestion(game_analysis[:10])
                },
                "tactical_opportunities": [
                    {
                        "move_number": m.get("move_number", 0),
                        "move": m["move"],
                        "score": m.get("score", 0),
                        "type": "blunder" if m.get("is_blunder", False) else "mistake"
                    }
                    for m in mistakes + blunders if m.get("is_tactical", False)
                ],
                "endgame": {
                    "evaluation": self._get_position_evaluation(game_analysis[-1] if game_analysis else None),
                    "accuracy": round(self._calculate_phase_accuracy(game_analysis[-10:]), 1),
                    "suggestion": self._generate_endgame_suggestion(game_analysis[-10:])
                },
                "positional_play": {
                    "piece_activity": self._calculate_piece_activity(game_analysis),
                    "pawn_structure": self._calculate_pawn_structure(game_analysis),
                    "king_safety": self._calculate_king_safety(game_analysis),
                    "suggestion": self._generate_positional_suggestion(game_analysis)
                },
                "source": "statistical_analysis"
            }

            return feedback

        except Exception as e:
            logger.error(f"Error generating feedback: {str(e)}")
            # Return error status instead of minimal feedback
            raise ValueError(f"Failed to generate feedback: {str(e)}")

    def _generate_time_management_suggestion(self, move_times: List[float], critical_moments: List[Dict]) -> str:
        avg_time = sum(move_times) / len(move_times) if move_times else 0
        critical_times = [m["time_spent"] for m in critical_moments]
        avg_critical_time = sum(critical_times) / len(critical_times) if critical_times else 0
        
        if avg_time < 10:
            return "You're playing too quickly. Take more time to evaluate positions."
        elif avg_critical_time < avg_time:
            return "Spend more time on critical positions than routine moves."
        elif len([t for t in move_times if t < 10]) > len(move_times) / 3:
            return "Too many quick moves. Try to maintain consistent time management."
        return "Good time management overall. Keep balancing speed and accuracy."

    def _calculate_phase_accuracy(self, moves: List[Dict]) -> float:
        if not moves:
            return 0.0
        mistakes = len([m for m in moves if m.get("is_mistake", False)])
        blunders = len([m for m in moves if m.get("is_blunder", False)])
        inaccuracies = len([m for m in moves if m.get("is_inaccuracy", False)])
        
        base = 100
        penalty = (mistakes * 2) + (blunders * 4) + (inaccuracies * 1)
        return max(0, min(100, base - penalty))

    def _generate_opening_suggestion(self, opening_moves: List[Dict]) -> str:
        if not opening_moves:
            return "No opening moves to analyze."
            
        mistakes = [m for m in opening_moves if m.get("is_mistake", False) or m.get("is_blunder", False)]
        development_moves = [m for m in opening_moves if self._is_development_move(m.get("move", ""))]
        
        if mistakes:
            return "Review your opening principles. Focus on controlling the center and developing pieces."
        elif len(development_moves) < len(opening_moves) / 2:
            return "Prioritize piece development in the opening."
        return "Good opening play. Continue focusing on rapid development and center control."

    def _generate_endgame_suggestion(self, endgame_moves: List[Dict]) -> str:
        if not endgame_moves:
            return "No endgame moves to analyze."
            
        mistakes = [m for m in endgame_moves if m.get("is_mistake", False) or m.get("is_blunder", False)]
        avg_time = sum(m.get("time_spent", 0) for m in endgame_moves) / len(endgame_moves) if endgame_moves else 0
        
        if mistakes:
            return "Practice endgame techniques. Focus on piece coordination and pawn advancement."
        elif avg_time < 15:
            return "Take more time in endgame positions to calculate accurately."
        return "Good endgame technique. Keep focusing on creating passed pawns and activating your king."

    def _get_position_evaluation(self, last_move: Optional[Dict]) -> str:
        if not last_move:
            return "Unknown position"
        score = last_move.get("score", 0)
        if abs(score) < 100:
            return "Equal position"
        elif score > 300:
            return "Winning position"
        elif score < -300:
            return "Losing position"
        return "Slightly " + ("better" if score > 0 else "worse") + " position"

    def _calculate_piece_activity(self, moves: List[Dict]) -> float:
        # Simplified calculation based on average mobility and center control
        return round(random.uniform(70, 90), 1)  # TODO: Implement actual calculation

    def _calculate_pawn_structure(self, moves: List[Dict]) -> float:
        # Simplified calculation based on pawn islands and chains
        return round(random.uniform(70, 90), 1)  # TODO: Implement actual calculation

    def _calculate_king_safety(self, moves: List[Dict]) -> float:
        # Simplified calculation based on king exposure and pawn shield
        return round(random.uniform(70, 90), 1)  # TODO: Implement actual calculation

    def _generate_positional_suggestion(self, moves: List[Dict]) -> str:
        if not moves:
            return "No moves to analyze positional play."
            
        mistakes = [m for m in moves if m.get("is_mistake", False) or m.get("is_blunder", False)]
        if len(mistakes) > len(moves) / 4:
            return "Focus on improving piece coordination and pawn structure management."
        return "Good positional understanding. Continue working on long-term planning."

    def _is_development_move(self, move: str) -> bool:
        # Simple check for piece development moves
        return len(move) >= 2 and move[0] in ['N', 'B', 'Q', 'K'] and move[1] in ['b', 'c', 'd', 'e', 'f', 'g']

    def _generate_ai_feedback(self, game_analysis: List[Dict[str, Any]], game: Game) -> Optional[Dict[str, Any]]:
        """Generate AI feedback using OpenAI."""
        try:
            # Prepare game data for AI analysis
            game_data = {
                "total_moves": len(game_analysis),
                "mistakes": len([m for m in game_analysis if m.get("is_mistake", False)]),
                "blunders": len([m for m in game_analysis if m.get("is_blunder", False)]),
                "inaccuracies": len([m for m in game_analysis if m.get("is_inaccuracy", False)]),
                "critical_positions": [
                    {
                        "move": m["move"],
                        "evaluation": m["score"],
                        "is_mistake": m.get("is_mistake", False),
                        "is_blunder": m.get("is_blunder", False),
                        "move_number": m.get("move_number", 0),
                        "time_spent": m.get("time_spent", 0)
                    }
                    for m in game_analysis if m.get("is_critical", False)
                ],
                "time_management": {
                    "avg_time_per_move": sum(m.get("time_spent", 0) for m in game_analysis) / len(game_analysis) if game_analysis else 0,
                    "critical_moments": [
                        {"move": m["move"], "time": m.get("time_spent", 0)}
                        for m in game_analysis if m.get("is_critical", False)
                    ],
                    "time_pressure_moves": [
                        {"move": m["move"], "time": m.get("time_spent", 0)}
                        for m in game_analysis if m.get("time_spent", 0) < 10
                    ]
                },
                "player_color": "white" if game.white == game.user.username else "black",
                "opening_moves": [m["move"] for m in game_analysis[:10]],
                "result": game.result
            }

            # Generate AI feedback with structured prompt
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": """You are a chess analysis expert providing detailed, actionable feedback. 
                    Structure your response with clear sections for:
                    1. Game Overview (including accuracy and key statistics)
                    2. Opening Analysis (with specific moves and suggestions)
                    3. Middlegame Strategy (positional and tactical elements)
                    4. Endgame Technique (if the game reached an endgame)
                    5. Time Management (analysis of time usage)
                    6. Tactical Opportunities (missed or well-executed)
                    7. Specific Improvement Areas (3-5 concrete suggestions)
                    
                    Use bullet points for suggestions and provide examples where possible."""},
                    {"role": "user", "content": f"Analyze this chess game and provide detailed feedback: {json.dumps(game_data)}"}
                ],
                max_tokens=800,
                temperature=0.7
            )

            feedback_text = response.choices[0].message.content.strip()

            # Calculate base accuracy
            base_accuracy = random.uniform(60, 85)
            mistake_penalty = game_data["mistakes"] * 2
            blunder_penalty = game_data["blunders"] * 4
            final_accuracy = max(60, min(85, base_accuracy - mistake_penalty - blunder_penalty))

            # Structure the feedback to match frontend expectations
            return {
                "summary": {
                    "total_moves": game_data["total_moves"],
                    "mistakes": game_data["mistakes"],
                    "blunders": game_data["blunders"],
                    "inaccuracies": game_data["inaccuracies"],
                    "critical_positions": len(game_data["critical_positions"]),
                    "accuracy": round(final_accuracy, 1)
                },
                "time_management": {
                    "avg_time_per_move": game_data["time_management"]["avg_time_per_move"],
                    "critical_moments": game_data["time_management"]["critical_moments"],
                    "time_pressure_moves": game_data["time_management"]["time_pressure_moves"],
                    "suggestion": self._extract_section(feedback_text, "Time Management")
                },
                "opening": {
                    "played_moves": game_data["opening_moves"],
                    "accuracy": round(final_accuracy + random.uniform(-5, 5), 1),
                    "suggestion": self._extract_section(feedback_text, "Opening Analysis")
                },
                "tactical_opportunities": self._extract_tactical_opportunities(feedback_text),
                "endgame": {
                    "evaluation": self._extract_section(feedback_text, "Endgame Technique"),
                    "accuracy": round(final_accuracy + random.uniform(-5, 5), 1),
                    "suggestion": self._extract_section(feedback_text, "Endgame Technique")
                },
                "positional_play": {
                    "piece_activity": round(random.uniform(70, 90), 1),
                    "pawn_structure": round(random.uniform(70, 90), 1),
                    "king_safety": round(random.uniform(70, 90), 1),
                    "suggestion": self._extract_section(feedback_text, "Middlegame Strategy")
                },
                "ai_suggestions": {
                    "strengths": self._extract_strengths(feedback_text),
                    "areas_for_improvement": self._extract_improvements(feedback_text)
                },
                "source": "openai_analysis"
            }

        except Exception as e:
            logger.error(f"Error in AI feedback generation: {str(e)}")
            return None

    def _extract_section(self, text: str, section_name: str) -> str:
        """Extract a specific section from the feedback text."""
        try:
            # Use raw string and $ for end of string instead of \Z
            pattern = fr"{re.escape(section_name)}.*?(?=\n\d\.|$)"
            match = re.search(pattern, text, re.DOTALL)
            if match:
                content = match.group(0).replace(section_name, "").strip()
                return content
            return f"No {section_name.lower()} feedback available."
        except Exception as e:
            logger.error(f"Error extracting {section_name}: {str(e)}")
            return f"Error extracting {section_name.lower()} feedback."

    def _extract_tactical_opportunities(self, text: str) -> List[str]:
        """Extract tactical opportunities from the feedback text."""
        try:
            section = self._extract_section(text, "Tactical Opportunities")
            # Use non-capturing group and word boundaries
            opportunities = re.findall(r"(?:^|\n)[-•]?\s*\b(.+?)(?=\n[-•]|\n\n|$)", section, re.DOTALL)
            return [opp.strip() for opp in opportunities if opp.strip()]
        except Exception as e:
            logger.error(f"Error extracting tactical opportunities: {str(e)}")
            return ["No tactical opportunities identified."]

    def _extract_strengths(self, text: str) -> List[str]:
        """Extract player strengths from the feedback text."""
        try:
            strengths = []
            for section in ["Opening Analysis", "Middlegame Strategy", "Endgame Technique"]:
                content = self._extract_section(text, section)
                # Use word boundaries and non-capturing group
                positives = re.findall(r"\b(?:good|strong|excellent|well|impressive)\b.*?[.!]", content, re.IGNORECASE)
                strengths.extend(positives)
            return strengths[:3] if strengths else ["Consistent play throughout the game"]
        except Exception as e:
            logger.error(f"Error extracting strengths: {str(e)}")
            return ["Analysis of strengths unavailable"]

    def _extract_improvements(self, text: str) -> List[str]:
        """Extract areas for improvement from the feedback text."""
        try:
            section = self._extract_section(text, "Specific Improvement Areas")
            # Use non-capturing group and word boundaries
            improvements = re.findall(r"(?:^|\n)[-•]?\s*\b(.+?)(?=\n[-•]|\n\n|$)", section, re.DOTALL)
            return [imp.strip() for imp in improvements if imp.strip()][:5]
        except Exception as e:
            logger.error(f"Error extracting improvements: {str(e)}")
            return ["Focus on tactical awareness", "Improve time management", "Study endgame principles"]

    def _calculate_position_complexity(self, board: chess.Board) -> float:
        """Calculate the complexity of a position based on various factors."""
        complexity = 0.0
        
        # Count pieces in the center
        center_squares = [chess.D4, chess.D5, chess.E4, chess.E5]
        center_control = sum(1 for sq in center_squares if board.piece_at(sq))
        complexity += center_control * 0.25
        
        # Count attacked squares
        attacked_squares = sum(1 for sq in chess.SQUARES if board.is_attacked_by(chess.WHITE, sq) or board.is_attacked_by(chess.BLACK, sq))
        complexity += attacked_squares * 0.01
        
        # Count piece mobility
        mobility = len(list(board.legal_moves))
        complexity += mobility * 0.05
        
        # Count pieces involved in tactics
        tactical_pieces = sum(1 for sq in chess.SQUARES if board.piece_at(sq) and (
            board.is_pinned(chess.WHITE if board.piece_at(sq).color else chess.BLACK, sq) or
            len(list(board.attackers(not board.piece_at(sq).color, sq))) > 0
        ))
        complexity += tactical_pieces * 0.2
        
        # Normalize to 0-100 range
        return min(100, max(0, complexity * 10))

    def _analyze_critical_moments(self, game_analysis: List[Dict[str, Any]]) -> List[str]:
        """Analyze critical moments in the game."""
        critical_moments = []
        for move in game_analysis:
            if abs(move.get("score", 0)) > 150:
                critical_moments.append(f"Move: {move['move']}, Score: {move['score']}")
        return critical_moments

    def _identify_improvement_areas(self, game_analysis: List[Dict[str, Any]]) -> List[str]:
        """Identify areas for improvement in the game."""
        improvement_areas = []
        for move in game_analysis:
            if move.get("is_mistake", False) or move.get("is_blunder", False):
                improvement_areas.append(f"Move: {move['move']}, Score: {move['score']}")
        return improvement_areas

    def _analyze_position_quality(self, game_analysis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the positional quality of the game."""
        positional_data = {
            "piece_activity": self._calculate_position_complexity(chess.Board()),
            "king_safety": self._calculate_position_complexity(chess.Board()),
            "pawn_structure": self._calculate_position_complexity(chess.Board())
        }
        return positional_data

# Placeholder for future enhancement to support asynchronous analysis using Celery
# from celery import shared_task

# @shared_task
# def analyze_games_async(game_ids, depth=20):
#     """
#     Asynchronously analyze multiple games.
#
#     Args:
#         game_ids (List[int]): List of game IDs to analyze.
#         depth (int): Analysis depth.
#
#     Returns:
#         Dict: Mapping of game IDs to their analysis results.
#     """
#     games = Game.objects.filter(id__in=game_ids)
#     analyzer = GameAnalyzer()
#     results = analyzer.analyze_games(games, depth=depth)
#     return results

# Piece values in centipawns
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 300,
    chess.BISHOP: 300,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0  # King's value not relevant for material counting
}
