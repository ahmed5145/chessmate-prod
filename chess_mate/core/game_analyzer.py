"""
This module provides functionality for analyzing chess games using the Stockfish engine.
It includes classes and methods to analyze single or multiple games, save analysis results to the
database, and generate feedback based on the analysis.
"""

import os
import io
import logging
import chess
import chess.engine
import chess.pgn
from django.db import DatabaseError
from .models import Game
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

STOCKFISH_PATH = os.getenv("STOCKFISH_PATH")

class GameAnalyzer:
    """
    Handles game analysis using Stockfish or external APIs.
    """

    def __init__(self, stockfish_path=STOCKFISH_PATH):
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
        except (chess.engine.EngineError, ValueError) as e:
            logger.error("Failed to initialize Stockfish engine: %s", str(e))
            raise

    def analyze_move(self, board: chess.Board, move: chess.Move, depth: int = 20) -> Dict[str, Any]:
        """Analyze a single move using the Stockfish engine."""
        # Limit depth to prevent timeouts
        max_depth = min(depth, 15)  # Cap maximum depth
        try:
            # Add time limit along with depth limit
            result = self.engine.analyse(
                board,
                chess.engine.Limit(depth=max_depth, time=10.0)  # 10 second time limit
            )
            score_obj = result.get("score")
            
            # Track time spent
            time_spent = result.get("time", 0)
            
            if not score_obj:
                # If no score object, return a neutral evaluation
                return {
                    "move": move.uci(),
                    "score": 0,
                    "depth": depth,
                    "time_spent": time_spent,
                    "is_capture": board.is_capture(move),
                    "is_check": board.gives_check(move),
                    "position_complexity": self._calculate_position_complexity(board)
                }
            
            # Convert score to white's perspective
            score_obj = score_obj.white()
            
            # Handle mate scores
            if score_obj.is_mate():
                mate_score = score_obj.mate()
                # Convert mate score to centipawns (±10000 for mate)
                score = 10000 if mate_score > 0 else -10000
            else:
                # Handle regular scores
                try:
                    score = score_obj.score()
                    if score is None:
                        score = 0
                except AttributeError:
                    score = 0
            
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
            # Return a neutral evaluation instead of None
            return {
                "move": move.uci(),
                "score": 0,
                "depth": depth,
                "time_spent": 0,
                "is_capture": board.is_capture(move),
                "is_check": board.gives_check(move),
                "position_complexity": 0
            }

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

    def analyze_games(self, games: List[Game], depth: int = 20) -> Dict[int, List[Dict[str, Any]]]:
        """
        Analyze a list of games.
        
        Args:
            games: List of Game objects to analyze
            depth: Depth of analysis (default: 20)
            
        Returns:
            Dictionary mapping game IDs to their analysis results
            
        Raises:
            ValueError: If no games are provided or if any game has invalid PGN data
        """
        if not games:
            raise ValueError("No games provided for analysis")
            
        results = {}
        total_games = len(games)
        for i, game in enumerate(games):
            try:
                results[game.id] = self.analyze_single_game(game, depth)
                # Calculate and log progress
                progress = ((i + 1) / total_games) * 100
                logger.info(f"Analysis progress: {progress:.1f}% ({i + 1}/{total_games} games)")
            except Exception as e:
                logger.error(f"Error analyzing game {game.id}: {str(e)}")
                continue
        return results

    def analyze_single_game(self, game: Game, depth: int = 20) -> List[Dict[str, Any]]:
        """
        Analyze a single game.

        Args:
            game: Game object to analyze
            depth: Depth of analysis (default: 20)

        Returns:
            List of dictionaries containing analysis data for each move

        Raises:
            ValueError: If the game has no PGN data or if PGN is invalid
        """
        if not game.pgn:
            raise ValueError("No PGN data provided for analysis")

        board = chess.Board()
        moves = []
        analysis = []
        last_score = 0

        # Parse moves from PGN
        try:
            # Clean PGN data
            pgn_str = game.pgn.strip()
            if not pgn_str:
                raise ValueError("Empty PGN data")

            # Parse game
            pgn_game = chess.pgn.read_game(io.StringIO(pgn_str))
            if not pgn_game:
                raise ValueError("Invalid PGN data: Could not parse game")

            # Collect moves
            current_node = pgn_game
            while True:
                next_node = current_node.variations[0] if current_node.variations else None
                if not next_node:
                    break
                if not next_node.move:
                    continue
                moves.append(next_node.move)
                current_node = next_node

            if not moves:
                raise ValueError("Invalid PGN data: No moves found")
        except Exception as e:
            logger.error(f"Error parsing PGN for game {game.id}: {str(e)}")
            raise ValueError(f"Invalid PGN data: {str(e)}")

        # Analyze each move
        for move in moves:
            try:
                move_analysis = self.analyze_move(board, move, depth)
                if move_analysis:  # Only process if move_analysis is not None
                    # Calculate evaluation drop and mark critical moves
                    current_score = move_analysis["score"]
                    eval_drop = last_score - current_score

                    move_analysis.update({
                        "evaluation_drop": eval_drop,
                        "is_mistake": eval_drop > 200,  # More than 2 pawns drop
                        "is_blunder": eval_drop > 400,  # More than 4 pawns drop
                        "is_critical": abs(current_score) > 150 or abs(eval_drop) > 150
                    })

                    analysis.append(move_analysis)
                    last_score = current_score

                board.push(move)
            except Exception as e:
                logger.error(f"Error analyzing move {move} in game {game.id}: {str(e)}")
                continue

        return analysis

    def save_analysis_to_db(self, game, analysis_results):
        """
        Save analysis results to the database.

        Args:
            game (Game): The Game object.
            analysis_results (List[dict]): The analysis results.
        """
        try:
            game.analysis = analysis_results  # Store the analysis results as JSON
            game.save()
        except (DatabaseError, ValueError) as e:
            logger.error("Error saving analysis to database: %s", str(e))

    def generate_feedback(self, game_analysis: List[Dict[str, Any]], game: Game) -> Dict[str, Any]:
        """Generate feedback based on game analysis."""
        # Default values for empty analysis
        default_feedback = {
            "overall_accuracy": 65.0,
            "elo_performance": game.user.profile.rating or 1200,
            "game_length": 0,
            "performance_breakdown": {
                "opening": 65.0,
                "middlegame": 65.0,
                "endgame": 65.0
            },
            "opening_analysis": {
                "accuracy": 65.0,
                "book_moves": 0,
                "suggestions": ["Study basic opening principles"]
            },
            "tactical_analysis": {
                "tactics_score": 65.0,
                "missed_wins": 0,
                "critical_mistakes": 0,
                "suggestions": ["Practice basic tactical patterns"]
            },
            "resourcefulness": {
                "overall_score": 65.0,
                "defensive_saves": 0,
                "counter_attacks": 0,
                "suggestions": ["Focus on defensive techniques"]
            },
            "advantage": {
                "conversion_rate": 65.0,
                "missed_wins": 0,
                "winning_positions": 0,
                "suggestions": ["Practice converting advantages"]
            },
            "time_management": {
                "average_move_time": 30.0,
                "critical_time_decisions": 0,
                "time_trouble_frequency": "Low",
                "suggestions": ["Maintain consistent time usage"]
            },
            "comparison": {
                "accuracy_percentile": 50,
                "tactics_percentile": 50,
                "time_management_percentile": 50
            }
        }

        if not game_analysis:
            return default_feedback

        # Calculate overall accuracy
        total_positions = len(game_analysis)
        good_moves = sum(1 for move in game_analysis if abs(move.get("score", 0)) < 100)
        accuracy = (good_moves / total_positions) * 100 if total_positions > 0 else 65.0
        accuracy = max(min(accuracy, 100), 50)  # Keep between 50 and 100

        # Phase analysis
        opening_moves = game_analysis[:min(10, len(game_analysis))]
        middlegame_moves = game_analysis[min(10, len(game_analysis)):min(30, len(game_analysis))]
        endgame_moves = game_analysis[min(30, len(game_analysis)):]

        # Calculate phase accuracies
        opening_accuracy = sum(1 for move in opening_moves if abs(move.get("score", 0)) < 50) / len(opening_moves) * 100 if opening_moves else 65.0
        middlegame_accuracy = sum(1 for move in middlegame_moves if abs(move.get("score", 0)) < 100) / len(middlegame_moves) * 100 if middlegame_moves else 65.0
        endgame_accuracy = sum(1 for move in endgame_moves if abs(move.get("score", 0)) < 100) / len(endgame_moves) * 100 if endgame_moves else 65.0

        # Tactical analysis
        tactics_score = 0
        missed_wins = 0
        critical_mistakes = 0
        winning_positions = 0
        defensive_saves = 0
        counter_attacks = 0

        last_eval = 0
        for move in game_analysis:
            current_eval = move.get("score", 0)
            
            # Detect tactical opportunities
            if abs(current_eval - last_eval) > 200:
                if current_eval > last_eval:
                    tactics_score += 1
                    counter_attacks += 1
                else:
                    critical_mistakes += 1
                    
            # Detect winning positions and missed wins
            if current_eval > 300:
                winning_positions += 1
                if next_eval := next((m.get("score", 0) for m in game_analysis[game_analysis.index(move)+1:]), current_eval):
                    if next_eval < current_eval - 200:
                        missed_wins += 1
                        
            # Detect defensive saves
            if last_eval < -200 and current_eval > -100:
                defensive_saves += 1
                
            last_eval = current_eval

        # Calculate tactics score
        total_opportunities = max(1, tactics_score + critical_mistakes)
        tactics_score = (tactics_score / total_opportunities) * 100 if total_opportunities > 0 else 65.0

        # Time management analysis
        move_times = [move.get("time_spent", 30) for move in game_analysis]
        avg_time = sum(move_times) / len(move_times) if move_times else 30.0
        critical_time_decisions = sum(1 for t in move_times if t < avg_time * 0.3)

        # Calculate resourcefulness score
        defensive_opportunities = sum(1 for move in game_analysis if move.get("score", 0) < -200)
        resourcefulness_score = (defensive_saves / max(1, defensive_opportunities)) * 100 if defensive_opportunities > 0 else 65.0

        # Calculate advantage conversion
        conversion_rate = ((winning_positions - missed_wins) / max(1, winning_positions)) * 100 if winning_positions > 0 else 65.0

        return {
            "overall_accuracy": round(accuracy, 1),
            "elo_performance": round(1200 + (accuracy - 65) * 5),  # Adjust ELO based on accuracy
            "game_length": len(game_analysis),
            "performance_breakdown": {
                "opening": round(opening_accuracy, 1),
                "middlegame": round(middlegame_accuracy, 1),
                "endgame": round(endgame_accuracy, 1)
            },
            "opening_analysis": {
                "accuracy": round(opening_accuracy, 1),
                "book_moves": len(opening_moves),
                "suggestions": [
                    "Study basic opening principles" if opening_accuracy < 70 else "Expand your opening repertoire",
                    "Focus on piece development" if opening_accuracy < 80 else "Study advanced variations"
                ]
            },
            "tactical_analysis": {
                "tactics_score": round(tactics_score, 1),
                "missed_wins": missed_wins,
                "critical_mistakes": critical_mistakes,
                "suggestions": [
                    "Practice basic tactical patterns" if tactics_score < 70 else "Study complex combinations",
                    "Focus on calculation accuracy" if critical_mistakes > 2 else "Keep up the tactical awareness"
                ]
            },
            "resourcefulness": {
                "overall_score": round(resourcefulness_score, 1),
                "defensive_saves": defensive_saves,
                "counter_attacks": counter_attacks,
                "suggestions": [
                    "Work on defensive technique" if resourcefulness_score < 70 else "Maintain strong defensive skills",
                    "Practice finding counterplay" if counter_attacks < 2 else "Continue finding active defenses"
                ]
            },
            "advantage": {
                "conversion_rate": round(conversion_rate, 1),
                "missed_wins": missed_wins,
                "winning_positions": winning_positions,
                "suggestions": [
                    "Practice converting advantages" if conversion_rate < 70 else "Maintain technical precision",
                    "Study endgame techniques" if missed_wins > 1 else "Keep up the winning technique"
                ]
            },
            "time_management": {
                "average_move_time": round(avg_time, 1),
                "critical_time_decisions": critical_time_decisions,
                "time_trouble_frequency": "High" if critical_time_decisions > 5 else "Medium" if critical_time_decisions > 2 else "Low",
                "suggestions": [
                    "Manage time more carefully" if critical_time_decisions > 5 else "Maintain good time management",
                    "Plan moves in advance" if avg_time > 45 else "Take more time in critical positions"
                ]
            },
            "comparison": {
                "accuracy_percentile": round(min(100, max(1, (accuracy - 50) * 2))),
                "tactics_percentile": round(min(100, max(1, (tactics_score - 50) * 2))),
                "time_management_percentile": round(min(100, max(1, (100 - critical_time_decisions * 10))))
            }
        }

    def _generate_time_management_suggestion(self, time_data):
        avg_time = time_data["avg_time_per_move"]
        critical_moments = len(time_data["critical_moments"])
        time_pressure = len(time_data["time_pressure_moves"])

        if critical_moments > 3:
            return "You're making quick moves in critical positions. Take more time to evaluate complex positions."
        elif time_pressure > 5:
            return "You're getting into time trouble frequently. Try to manage your time better in the opening and middlegame."
        elif avg_time > 45:
            return "You're spending too much time on some moves. Try to make decisions more quickly in clear positions."
        else:
            return "Your time management is generally good. Keep balancing quick play with careful consideration in critical positions."

    def _generate_opening_suggestion(self, opening_data):
        accuracy = opening_data["accuracy"]
        if accuracy < 50:
            return "Your opening play needs improvement. Study common opening principles and popular lines in your repertoire."
        elif accuracy < 80:
            return "Your opening play is decent but could be more accurate. Focus on understanding the key ideas behind your chosen openings."
        else:
            return "Your opening play is strong. Consider expanding your repertoire with more complex variations."

    def _generate_endgame_suggestion(self, endgame_data):
        accuracy = endgame_data["accuracy"]
        if accuracy < 50:
            return "Your endgame technique needs work. Practice basic endgame positions and principles."
        elif accuracy < 80:
            return "Your endgame play is solid but could be more precise. Study typical endgame patterns and techniques."
        else:
            return "Your endgame technique is strong. Focus on maximizing your advantages in winning positions."

    def _generate_positional_suggestion(self, positional_data):
        """Generate suggestion based on positional play data."""
        piece_activity = positional_data["piece_activity"]
        king_safety = positional_data["king_safety"]
        
        if king_safety < 60:
            return "Focus on king safety and avoiding unnecessary checks. Consider castle timing and pawn structure around the king."
        elif piece_activity < 50:
            return "Work on piece coordination and activity. Look for opportunities to improve piece placement and control central squares."
        else:
            return "Your positional understanding is good. Continue focusing on piece coordination and maintaining a solid pawn structure."

    def close_engine(self):
        """Closes the Stockfish engine."""
        if self.engine:
            self.engine.quit()

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
