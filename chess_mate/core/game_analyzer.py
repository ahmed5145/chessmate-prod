"""
This module provides functionality for analyzing chess games using the Stockfish engine.
It includes classes and methods to analyze single or multiple games, save analysis results to the
database, and generate feedback based on the analysis.
"""

import os
import io
import logging
from typing import List, Dict, Any, Optional, Union, cast, TypedDict
import chess
import chess.engine
import chess.pgn
from django.db import DatabaseError, transaction, models
from django.core.cache import cache
from django.conf import settings
from .models import Game
from django.utils import timezone
from tenacity import retry, stop_after_attempt, wait_exponential
import random
from openai import OpenAI
from .ai_feedback import AIFeedbackGenerator
import json
import re
from .analysis.metrics_calculator import MetricsCalculator
import time
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

class GameMetrics(TypedDict):
    moves: List[Dict[str, Any]]
    overall: Dict[str, Any]
    phases: Dict[str, Any]
    tactics: Dict[str, Any]
    time_management: Dict[str, Any]
    positional: Dict[str, Any]
    advantage: Dict[str, Any]
    resourcefulness: Dict[str, Any]

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

    def cleanup(self):
        """Cleanup resources."""
        self.close_engine()

    def analyze_move(self, board: chess.Board, move: chess.Move, depth: int = 20, is_white: bool = True) -> Dict[str, Any]:
        """Analyze a single move and return evaluation data."""
        try:
            # Validate move is legal before proceeding
            if move not in board.legal_moves:
                logger.error(f"Illegal move encountered: {move.uci()} in position {board.fen()}")
                return self._create_neutral_evaluation(board, move, depth, 0.0)
            
            # Create a copy of the board for analysis
            board_copy = board.copy()
            
            # Get position evaluation before the move
            eval_before = self.engine.analyse(board_copy, chess.engine.Limit(depth=depth))
            score_before = self._convert_score(eval_before.get('score', 0), is_white) if eval_before else 0.0
            
            # Make the move and get evaluation after
            board_copy.push(move)
            eval_after = self.engine.analyse(board_copy, chess.engine.Limit(depth=depth))
            score_after = self._convert_score(eval_after.get('score', 0), is_white) if eval_after else 0.0
            
            # Calculate evaluation change
            eval_change = score_after - score_before
            
            # Determine move phase
            total_pieces = len(board_copy.piece_map())
            phase = 'opening' if board_copy.fullmove_number <= 10 else ('endgame' if total_pieces <= 12 else 'middlegame')
            
            # Check if move is tactical
            is_tactical = self._is_tactical_move(board_copy, move, eval_change, eval_after)
            
            # Check if move is critical
            is_critical = abs(eval_change) >= 2.0  # Consider moves with 2+ pawn swing as critical
            
            # Calculate move accuracy (scale of 0-100)
            if abs(score_before) > 5.0:  # Already winning/losing position
                accuracy = 100.0 if eval_change >= -0.5 else max(0.0, 100.0 + (eval_change * 10))
            else:
                max_loss = -3.0  # Maximum expected evaluation loss
                accuracy = max(0.0, 100.0 * (1.0 + eval_change / max_loss))
            
            return {
                'move': move.uci(),
                'phase': phase,
                'score': score_after,
                'score_before': score_before,
                'score_after': score_after,
                'accuracy': round(accuracy, 2),
                'is_tactical': is_tactical,
                'is_critical': is_critical,
                'eval_change': eval_change,
                'depth': depth,
                'pv': [m.uci() for m in eval_after.get('pv', [])] if eval_after else [],
                'nodes': eval_after.get('nodes', 0) if eval_after else 0,
                'time': eval_after.get('time', 0.0) if eval_after else 0.0
            }
            
        except Exception as e:
            logger.error(f"Error analyzing move: {str(e)}")
            return self._create_neutral_evaluation(board, move, depth, 0.0)

    def _is_tactical_position(self, board: chess.Board) -> bool:
        """Determine if the current position is tactical."""
        try:
            # Count attacked pieces
            attacked_pieces = 0
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece:
                    if board.is_attacked_by(not piece.color, square):
                        attacked_pieces += 1
            
            # Position is tactical if there are multiple pieces under attack
            return attacked_pieces >= 2
            
        except Exception as e:
            logger.error(f"Error checking tactical position: {str(e)}")
            return False

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

    def _convert_score(self, score: Union[chess.engine.Score, chess.engine.PovScore, int, float, None], is_white: bool = True) -> float:
        """Convert chess.engine.Score to a float value."""
        try:
            if score is None:
                return 0.0
            
            raw_score = 0.0  # Initialize raw_score with a default value
            
            # Handle PovScore objects
            if isinstance(score, chess.engine.PovScore):
                score_value = score.relative.score()
                if score_value is None:
                    return 0.0
                # PovScore is already from white's perspective
                raw_score = float(score_value) / 100.0 if isinstance(score.relative, chess.engine.Cp) else (
                    10000.0 if score_value > 0 else -10000.0
                )
            
            # Handle Score objects
            elif isinstance(score, chess.engine.Score):
                score_value = score.score()
                if score_value is None:
                    return 0.0
                raw_score = float(score_value) / 100.0 if isinstance(score, chess.engine.Cp) else (
                    10000.0 if score_value > 0 else -10000.0
                )
            
            # Handle numeric values
            elif isinstance(score, (int, float)):
                raw_score = float(score)
            
            return raw_score if is_white else -raw_score
            
        except Exception as e:
            logger.error(f"Error converting score: {str(e)}")
            return 0.0

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def analyze_single_game(self, game: Game, depth: int = 20) -> Dict[str, Any]:
        """Analyze a single game and return comprehensive results."""
        if not game or not game.id:
            logger.error("Invalid game object provided")
            return self._get_error_response(None, "Invalid game object")

        try:
            # Parse moves from PGN
            moves = self._parse_pgn(game)
            
            # Handle empty game case
            if not moves:
                logger.warning(f"No moves found in game {game.id}")
                return {
                    'analysis_complete': True,
                    'game_id': game.id,
                    'analysis_results': {
                        'summary': self._get_default_metrics(),
                        'moves': []
                    },
                    'feedback': {
                        'source': 'system',
                        'feedback': {
                            'strengths': [],
                            'weaknesses': ['No moves were made in the game, indicating a lack of gameplay or analysis provided.'],
                            'critical_moments': [],
                            'improvement_areas': ['Start playing games to gather data for analysis.'],
                            'opening': {
                                'analysis': 'No data available as no moves were made.',
                                'suggestion': 'Start playing games to gather data on opening choices and performance.'
                            },
                            'middlegame': {
                                'analysis': 'No data available as no moves were made.',
                                'suggestion': 'Start playing games to assess middlegame decision-making and tactics.'
                            },
                            'endgame': {
                                'analysis': 'No data available as no moves were made.',
                                'suggestion': 'Start playing games to evaluate endgame strategies and execution.'
                            }
                        },
                        'metrics': self._get_default_metrics()['overall']
                    }
                }

            # Analyze moves
            analysis_results = self._analyze_moves(moves, depth, game.white == game.user.username)
            if not analysis_results:
                return self._get_error_response(game.id, "Move analysis failed")

            # Calculate metrics
            metrics = self._calculate_metrics({'moves': analysis_results, 'is_white': game.white == game.user.username})
            
            # Ensure metrics has moves for feedback generation
            metrics['moves'] = analysis_results
            
            # Generate feedback
            feedback_source = 'openai' if settings.USE_OPENAI else 'statistical'
            try:
                feedback = self.generate_feedback(metrics)
                if not feedback:
                    feedback_source = 'basic'
                    feedback = self._get_default_feedback()
            except Exception as e:
                logger.error(f"Error generating feedback: {str(e)}")
                feedback_source = 'basic'
                feedback = self._get_default_feedback()

            # Structure the response
            response = {
                'analysis_complete': True,
                'game_id': game.id,
                'analysis_results': metrics,
                'feedback': {
                    'source': feedback_source,
                    'feedback': feedback
                }
            }

            return response

        except Exception as e:
            logger.error(f"Error analyzing game {game.id}: {str(e)}", exc_info=True)
            return self._get_error_response(game.id, str(e))

    def _get_error_response(self, game_id: Optional[int], error_message: str) -> Dict[str, Any]:
        """Generate a standardized error response."""
        return {
            'analysis_complete': True,
            'game_id': game_id,
            'analysis_results': {
                'summary': self._get_default_metrics(),
                'moves': []
            },
            'feedback': {
                'source': 'system',
                'feedback': {
                    'strengths': [],
                    'weaknesses': [f'Analysis failed: {error_message}'],
                    'critical_moments': [],
                    'improvement_areas': ['Try analyzing the game again'],
                    'opening': {
                        'analysis': 'Analysis not available due to error',
                        'suggestion': 'Try analyzing the game again'
                    },
                    'middlegame': {
                        'analysis': 'Analysis not available due to error',
                        'suggestion': 'Try analyzing the game again'
                    },
                    'endgame': {
                        'analysis': 'Analysis not available due to error',
                        'suggestion': 'Try analyzing the game again'
                    }
                },
                'metrics': self._get_default_metrics()['overall']
            }
        }

    def _parse_pgn(self, game: Game) -> List[chess.Move]:
        """Parse moves from PGN and return a list of valid moves."""
        try:
            if not game or not game.pgn:
                logger.warning(f"No game or PGN data found for game_id: {game.id if game else None}")
                return []

            # Clean PGN data
            pgn_data = game.pgn.strip()
            if not pgn_data:
                logger.warning(f"Empty PGN data for game_id: {game.id}")
                return []

            # Parse PGN
            try:
                pgn_game = chess.pgn.read_game(io.StringIO(pgn_data))
                if not pgn_game:
                    logger.error(f"Failed to parse PGN for game_id: {game.id}")
                    return []

                # Extract moves
                moves: List[chess.Move] = []
                board = pgn_game.board()
                for move in pgn_game.mainline_moves():
                    if move in board.legal_moves:
                        moves.append(move)
                        board.push(move)
                    else:
                        logger.warning(f"Illegal move found in game {game.id}: {move.uci()}")
                        break

                if not moves:
                    logger.warning(f"No valid moves found in game {game.id}")
                else:
                    logger.info(f"Successfully parsed {len(moves)} moves from game {game.id}")

                return moves

            except Exception as e:
                logger.error(f"Error parsing PGN for game {game.id}: {str(e)}")
                return []

        except Exception as e:
            logger.error(f"Error in _parse_pgn: {str(e)}")
            return []

    def _analyze_moves(self, moves: List[chess.Move], depth: int, is_white: bool = True) -> List[Dict[str, Any]]:
        """Analyze a list of moves."""
        analysis = []
        move_number = 1
        current_is_white = True
        last_score: float = 0.0  # Initialize as float
        
        board = chess.Board()

        for move in moves:
            try:
                # Validate move is legal before analyzing
                if not isinstance(move, chess.Move):
                    logger.error(f"Invalid move object: {move}")
                    continue
                    
                if move not in board.legal_moves:
                    logger.error(f"Illegal move encountered: {move.uci()} in position {board.fen()}")
                    continue

                # Create a copy of the board for analysis
                board_copy = board.copy()
                
                # Analyze the move
                move_analysis = self.analyze_move(board_copy, move, depth, is_white)
                
                if not move_analysis or 'score' not in move_analysis:
                    logger.error(f"Error analyzing move: Invalid analysis result")
                    continue

                # Now make the move on the main board
                board.push(move)
                current_score = float(str(move_analysis["score"]))
                
                # Calculate evaluation drop from player's perspective
                eval_drop = (last_score - current_score) if current_is_white == is_white else (current_score - last_score)
                eval_improvement = max(0, -eval_drop)  # Positive when position improves

                # Calculate material count
                material_count = self._calculate_material_count(board)

                # Calculate position complexity
                position_complexity = self._calculate_position_complexity(board)

                # Add additional analysis data
                move_analysis.update({
                "move_number": move_number,
                "evaluation_drop": eval_drop,
                    "evaluation_improvement": eval_improvement,
                    "is_mistake": eval_drop > 200,
                    "is_blunder": eval_drop > 400,
                    "is_inaccuracy": 100 < eval_drop <= 200,
                    "is_critical": abs(current_score) > 150 or abs(eval_drop) > 150,
                    "is_tactical": self._is_tactical_move(board, move, eval_drop, move_analysis),
                    "phase": 'opening' if move_number <= 10 else ('endgame' if len(board.piece_map()) <= 12 else 'middlegame'),
                    "is_white": current_is_white == is_white,
                    "material_count": material_count,
                    "position_complexity": position_complexity,
                    "time_spent": move_analysis.get('time', 0.0),
                    "eval_before": last_score,
                    "eval_after": current_score
                })

                analysis.append(move_analysis)
                last_score = float(current_score)  # Convert to float explicitly
                move_number += 1
                current_is_white = not current_is_white
            
            except Exception as e:
                logger.error(f"Error analyzing move: {str(e)}")
                continue
            
        return analysis if analysis else []

    def _validate_time_metrics(self, time_spent: float, total_time: float, increment: float) -> Dict[str, Any]:
        """Validate and normalize time metrics."""
        try:
            time_spent = max(0.0, float(time_spent))
            total_time = max(1.0, float(total_time))
            increment = max(0.0, float(increment))
            
            return {
                'time_pressure': False,
                'critical_time': False,
                'time_ratio': time_spent / total_time,
                'remaining_time': total_time - time_spent + increment,
                'normalized_time': min(1.0, time_spent / total_time)
            }
        except Exception as e:
            logger.error(f"Error validating time metrics: {str(e)}")
            return {
                'time_pressure': False,
                'critical_time': False,
                'time_ratio': 0.0,
                'remaining_time': total_time,
                'normalized_time': 0.0
            }

    @transaction.atomic
    def save_analysis_to_db(self, game: Game, analysis_results: Dict[str, Any]) -> None:
        """Save analysis results to the database with transaction handling."""
        try:
            # Generate feedback and metrics
            feedback = self.generate_feedback(analysis_results, game)
            
            # Structure the analysis data
            analysis_data = {
                'moves': analysis_results.get('moves', []),
                'feedback': feedback,
                'analysis_complete': True,
                'timestamp': timezone.now().isoformat()
            }
            
            # Save to database
            game.analysis = analysis_data
            game.save()
            if hasattr(game, 'id'):
                logger.info(f"Successfully saved analysis for game {game.id}")
            else:
                logger.info("Successfully saved analysis for game")
        except Exception as e:
            logger.error(f"Error saving analysis to database: {str(e)}")
            raise

    def _calculate_overall_accuracy(self, moves: List[Dict[str, Any]]) -> float:
        """Calculate overall accuracy from move evaluations."""
        if not moves:
            return 0.0
        
        total_accuracy = 0.0
        num_moves = 0
        
        for move in moves:
            # Skip moves without evaluations
            if 'eval_before' not in move or 'eval_after' not in move:
                    continue
            
            eval_before = self._convert_score(move['eval_before'])
            eval_after = self._convert_score(move['eval_after'])
            
            # Calculate accuracy based on evaluation difference
            eval_diff = abs(eval_after - eval_before)
            move_accuracy = max(0.0, 100.0 - (eval_diff * 10.0))  # Convert eval diff to accuracy percentage
            
            total_accuracy += move_accuracy
            num_moves += 1
        
        return round(total_accuracy / num_moves if num_moves > 0 else 0.0, 2)

    def generate_feedback(self, analysis_data: Dict[str, Any], game: Game) -> Dict[str, Any]:
        """Generate comprehensive feedback from analysis data."""
        try:
            moves = analysis_data.get('moves', [])
            metrics = analysis_data.get('metrics', {})
            
            # Split moves into phases
            opening_moves = moves[:min(10, len(moves))]
            middlegame_moves = moves[min(10, len(moves)):min(30, len(moves))]
            endgame_moves = moves[min(30, len(moves)):]
            
            # Generate feedback
            feedback = {
                'source': 'statistical',
                'strengths': self._identify_strengths(metrics),
                'weaknesses': self._identify_weaknesses(metrics),
                    'critical_moments': self._identify_critical_moments(moves),
                'improvement_areas': self._generate_overall_assessment(metrics),
                'opening': {
                    'analysis': self._analyze_phase(opening_moves, 'opening'),
                    'suggestion': self._generate_opening_suggestion(opening_moves)
                },
                'middlegame': {
                    'analysis': self._analyze_phase(middlegame_moves, 'middlegame'),
                    'suggestion': self._generate_middlegame_suggestion(middlegame_moves)
                },
                'endgame': {
                    'analysis': self._analyze_phase(endgame_moves, 'endgame'),
                    'suggestion': self._generate_endgame_suggestion(endgame_moves)
                },
                'tactics': {
                    'analysis': metrics.get('tactics', {}).get('analysis', ''),
                    'opportunities': metrics.get('tactics', {}).get('opportunities', 0),
                    'successful': metrics.get('tactics', {}).get('successful', 0),
                    'success_rate': metrics.get('tactics', {}).get('success_rate', 0)
                },
                'time_management': {
                    'analysis': metrics.get('time_management', {}).get('analysis', ''),
                    'avg_time_per_move': metrics.get('time_management', {}).get('average_time', 0),
                    'time_pressure_moves': metrics.get('time_management', {}).get('time_pressure_moves', 0),
                    'time_pressure_percentage': metrics.get('time_management', {}).get('time_pressure_percentage', 0)
                },
                'advantage': {
                    'analysis': metrics.get('advantage', {}).get('analysis', ''),
                    'max_advantage': metrics.get('advantage', {}).get('max_advantage', 0),
                    'min_advantage': metrics.get('advantage', {}).get('min_advantage', 0),
                    'average_advantage': metrics.get('advantage', {}).get('average_advantage', 0),
                    'winning_positions': metrics.get('advantage', {}).get('winning_positions', 0),
                    'advantage_retention': metrics.get('advantage', {}).get('advantage_retention', 0)
                },
                'resourcefulness': {
                    'analysis': metrics.get('resourcefulness', {}).get('analysis', ''),
                    'recovery_rate': metrics.get('resourcefulness', {}).get('recovery_rate', 0),
                    'defensive_score': metrics.get('resourcefulness', {}).get('defensive_score', 0),
                    'critical_defense': metrics.get('resourcefulness', {}).get('critical_defense', 0),
                    'position_recovery': metrics.get('resourcefulness', {}).get('position_recovery', 0)
                }
            }
            
            return feedback

        except Exception as e:
            logger.error(f"Error generating feedback: {str(e)}")
            return self._get_default_feedback()

    def _analyze_phase(self, moves: List[Dict[str, Any]], phase: str) -> str:
        """Analyze a specific game phase."""
        if not moves:
            return f"No {phase} moves to analyze."

        mistakes = sum(1 for m in moves if m.get('is_mistake', False))
        blunders = sum(1 for m in moves if m.get('is_blunder', False))
        accuracy = self._calculate_phase_accuracy(moves)

        if accuracy >= 80:
            quality = "excellent"
        elif accuracy >= 70:
            quality = "good"
        elif accuracy >= 60:
            quality = "reasonable"
        else:
            quality = "needs improvement"

        return f"{phase.title()} play was {quality} with {mistakes} mistakes and {blunders} blunders."

    def _generate_middlegame_suggestion(self, middlegame_moves: List[Dict[str, Any]]) -> str:
        """Generate middlegame suggestions."""
        if not middlegame_moves:
            return "No middlegame moves to analyze."

        mistakes = [m for m in middlegame_moves if m.get('is_mistake', False) or m.get('is_blunder', False)]
        tactical_moves = [m for m in middlegame_moves if m.get('is_tactical', False)]

        if mistakes:
            return "Focus on positional understanding and tactical awareness in complex positions."
        elif len(tactical_moves) < len(middlegame_moves) / 4:
            return "Look for more tactical opportunities in the middlegame."
        return "Good middlegame play. Continue working on piece coordination and strategic planning."

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

    def _calculate_piece_activity(self, board: chess.Board) -> float:
        """Calculate piece activity/development score (0-1)."""
        developed_pieces = 0
        total_pieces = 0
        
        # Check piece development for both sides
        for color in [chess.WHITE, chess.BLACK]:
            # Count developed minor pieces
            for piece_type in [chess.KNIGHT, chess.BISHOP]:
                pieces = board.pieces(piece_type, color)
                total_pieces += len(pieces)
                for square in pieces:
                    rank = chess.square_rank(square)
                    if color == chess.WHITE and rank > 1:
                        developed_pieces += 1
                    elif color == chess.BLACK and rank < 6:
                        developed_pieces += 1
        
        return developed_pieces / max(1, total_pieces)

    def _calculate_pawn_structure(self, board: chess.Board) -> float:
        """Calculate pawn structure complexity (0-1)."""
        total_pawns = 0
        complex_pawns = 0
        
        for color in [chess.WHITE, chess.BLACK]:
            pawns = board.pieces(chess.PAWN, color)
            total_pawns += len(pawns)
            
            # Count pawns in complex structures
            files_with_pawns = [chess.square_file(square) for square in pawns]
            for file in range(8):
                if files_with_pawns.count(file) > 1:  # Doubled pawns
                    complex_pawns += 1
                if file > 0 and file - 1 in files_with_pawns and file in files_with_pawns:  # Connected pawns
                    complex_pawns += 1
        
        return complex_pawns / max(1, total_pawns)

    def _calculate_center_control(self, board: chess.Board) -> float:
        """Calculate center control score (0-1)."""
        center_squares = [chess.E4, chess.D4, chess.E5, chess.D5]
        control_score: float = 0.0
        
        for square in center_squares:
            if board.is_attacked_by(chess.WHITE, square):
                control_score = float(control_score + 0.125)
            if board.is_attacked_by(chess.BLACK, square):
                control_score = float(control_score + 0.125)
            if board.piece_at(square) is not None:
                control_score = float(control_score + 0.125)
        
        return min(1.0, control_score)

    def _has_queens(self, board: chess.Board) -> bool:
        """Check if both sides still have queens."""
        return (len(board.pieces(chess.QUEEN, chess.WHITE)) > 0 and 
                len(board.pieces(chess.QUEEN, chess.BLACK)) > 0)

    def _is_positionally_sound(self, board: chess.Board, move: chess.Move) -> bool:
        """Determine if a move is positionally sound."""
        try:
            # Basic positional principles
            if board.is_capture(move):
                return True  # Captures are generally good if evaluation is stable
            
            to_square = move.to_square
            piece = board.piece_at(move.from_square)
            
            if not piece:
                return False
            
            # Center control
            if piece.piece_type in [chess.PAWN, chess.KNIGHT] and chess.square_rank(to_square) in [3, 4]:
                return True
                
            # Development
            if piece.piece_type in [chess.KNIGHT, chess.BISHOP]:
                if piece.color == chess.WHITE and chess.square_rank(to_square) > 1:
                    return True
                if piece.color == chess.BLACK and chess.square_rank(to_square) < 6:
                    return True
            
            # Rook to open file
            if piece.piece_type == chess.ROOK:
                file = chess.square_file(to_square)
                pawns_in_file = 0
                for rank in range(8):
                    square = chess.square(file, rank)
                    square_piece = board.piece_at(square)
                    if square_piece and square_piece.piece_type == chess.PAWN:
                        pawns_in_file += 1
                if pawns_in_file == 0:
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking positional soundness: {str(e)}")
            return False

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
                "result": game.result,
                "player_name": game.user.username
            }

            # Generate AI feedback with structured prompt
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": """You are an experienced, encouraging chess coach providing personalized feedback.
                    Your primary goal is to boost the player's confidence by highlighting their strengths while offering constructive suggestions for improvement.
                    
                    Key Guidelines:
                    1. Always address the player by name and use "you" and "your" throughout the feedback
                    2. For each strength identified, provide a specific example from their game
                    3. Frame improvement areas as opportunities for growth, not weaknesses
                    4. Maintain an encouraging and positive tone throughout
                    5. Focus on one or two key improvements rather than overwhelming with too many suggestions
                    
                    Structure your response as a JSON object with the following format:
                    {
                        "feedback": {
                            "overall_performance": {
                                "interpretation": "[Player's name], your game showed [specific strength]. You demonstrated [positive observation]...",
                                "key_strengths": [
                                    "In move [X], you brilliantly [specific strength]",
                                    "Your [specific aspect] was particularly strong when..."
                                ],
                                "areas_to_improve": [
                                    "You can enhance your [aspect] by...",
                                    "Consider taking more time to..."
                                ]
                            },
                            "opening": {
                                "suggestion": "Your opening choice of [specific moves] showed good understanding. To build on this strength..."
                            },
                            "middlegame": {
                                "suggestion": "You handled the complex middlegame position well, particularly when [specific example]..."
                            },
                            "endgame": {
                                "suggestion": "Your endgame technique showed promise, especially in [specific position]..."
                            },
                            "tactics": {
                                "suggestion": "You found several strong tactical opportunities, like [specific example]..."
                            },
                            "time_management": {
                                "suggestion": "Your time management was [positive aspect], particularly during [specific phase]..."
                            }
                        }
                    }"""},
                    {"role": "user", "content": f"Analyze this chess game and provide encouraging, personalized feedback for {game_data['player_name']}, focusing on their strengths and opportunities for growth: {json.dumps(game_data)}"}
                ],
                max_tokens=1500,
                temperature=0.7
            )

            logger.info("Received response from OpenAI: %s", response)
            feedback_text = response.choices[0].message.content
            logger.info("Feedback text: %s", feedback_text)
            if not feedback_text:
                logger.error("Empty response from OpenAI")
                return None
            try:
                # Parse the response as JSON
                feedback_data = json.loads(feedback_text)
                logger.info("Parsed feedback data: %s", feedback_data)
                # Validate the structure
                if not isinstance(feedback_data, dict) or 'feedback' not in feedback_data:
                    logger.error("Invalid feedback structure")
                    return None
                feedback = feedback_data['feedback']
                # Ensure all required sections are present
                required_sections = ['overall_performance', 'opening', 'middlegame', 'endgame', 'tactics', 'time_management']
                if not all(section in feedback for section in required_sections):
                    logger.error("Missing required sections in feedback")
                    return None
                return feedback
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OpenAI response as JSON: {str(e)}")
                return None
        except Exception as e:
            logger.error(f"Error generating AI feedback: {str(e)}")
            return None

    def _calculate_position_complexity(self, board: chess.Board) -> float:
        """
        Calculate the complexity of a position based on multiple factors.
        
        Returns:
            Float between 0 and 1 indicating position complexity
        """
        complexity_score = 0.0
        
        # 1. Piece density in the center
        center_squares = [chess.D4, chess.D5, chess.E4, chess.E5]
        center_pieces = sum(1 for sq in center_squares if board.piece_at(sq) is not None)
        complexity_score += center_pieces * 0.1
        
        # 2. Number of possible moves
        legal_moves = len(list(board.legal_moves))
        complexity_score += min(0.4, legal_moves / 40)  # Cap at 40 moves
        
        # 3. Piece interaction
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                attackers = len(board.attackers(not piece.color, square))
                defenders = len(board.attackers(piece.color, square))
                if attackers > 0 and defenders > 0:
                    complexity_score += 0.05  # Add for each contested piece
        
        # 4. Pawn structure complexity
        pawn_files = set()
        doubled_pawns = False
        isolated_pawns = False
        
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.piece_type == chess.PAWN:
                file = chess.square_file(square)
                if file in pawn_files:
                    doubled_pawns = True
                pawn_files.add(file)
                
                # Check for isolated pawns
                adjacent_files = set()
                if file > 0:
                    adjacent_files.add(file - 1)
                if file < 7:
                    adjacent_files.add(file + 1)
                    
                if not any(f in pawn_files for f in adjacent_files):
                    isolated_pawns = True
        
        if doubled_pawns:
            complexity_score += 0.1
        if isolated_pawns:
            complexity_score += 0.1
        
        # Normalize final score
        return min(1.0, complexity_score)

    def _identify_strengths(self, metrics: Dict[str, Any]) -> List[str]:
        """Identify player's strengths based on analysis metrics."""
        strengths = []
        
        # Check accuracy thresholds
        if metrics['overall']['accuracy'] >= 80:
            strengths.append("High overall accuracy")
        
        # Check tactical performance
        if metrics['tactics']['success_rate'] >= 70:
            strengths.append("Strong tactical awareness")
        
        # Check time management
        if metrics['time_management']['time_pressure_moves'] < 5:
            strengths.append("Good time management")
        
        # Check phase performance
        if metrics['phases']['opening']['accuracy'] >= 75:
            strengths.append("Solid opening play")
        if metrics['phases']['middlegame']['accuracy'] >= 75:
            strengths.append("Strong middlegame understanding")
        if metrics['phases']['endgame']['accuracy'] >= 75:
            strengths.append("Excellent endgame technique")
        
        return strengths[:3]  # Return top 3 strengths

    def _identify_weaknesses(self, metrics: Dict[str, Any]) -> List[str]:
        """Identify player's weaknesses based on analysis metrics."""
        weaknesses = []
        
        # Check accuracy thresholds
        if metrics['overall']['accuracy'] < 60:
            weaknesses.append("Low overall accuracy")
        
        # Check tactical performance
        if metrics['tactics']['success_rate'] < 50:
            weaknesses.append("Missed tactical opportunities")
        
        # Check time management
        if metrics['time_management']['time_pressure_percentage'] > 30:
            weaknesses.append("Poor time management")
        
        # Check phase performance
        if metrics['phases']['opening']['accuracy'] < 60:
            weaknesses.append("Opening preparation")
        if metrics['phases']['middlegame']['accuracy'] < 60:
            weaknesses.append("Middlegame strategy")
        if metrics['phases']['endgame']['accuracy'] < 60:
            weaknesses.append("Endgame technique")
        
        return weaknesses[:3] if weaknesses else ["No specific weaknesses identified"]

    def _identify_critical_moments(self, moves: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify critical moments in the game."""
        critical_moments = []
        
        for i, move in enumerate(moves):
            eval_before = self._convert_score(move.get('eval_before', 0))
            eval_after = self._convert_score(move.get('eval_after', 0))
            
            # Check for significant evaluation changes
            eval_swing = abs(eval_after - eval_before)
            if eval_swing >= 2.0:  # Significant change in evaluation
                critical_moments.append({
                    'move_number': move.get('move_number', i + 1),
                    'move': move.get('move', ''),
                    'eval_before': eval_before,
                    'eval_after': eval_after,
                    'description': self._describe_critical_moment(eval_before, eval_after)
                })
        
        return critical_moments

    def _describe_critical_moment(self, eval_before: float, eval_after: float) -> str:
        """Generate a description for a critical moment."""
        eval_diff = eval_after - eval_before
        if eval_diff > 0:
            return "Missed opportunity to gain advantage"
        return "Position significantly worsened after this move"

    def _generate_overall_assessment(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate overall assessment and improvement areas."""
        assessment = []
        
        # Check accuracy thresholds
        if metrics['overall']['accuracy'] < 60:
            assessment.append("Focus on reducing major mistakes and blunders")
        
        # Check tactical performance
        if metrics['tactics']['success_rate'] < 50:
            assessment.append("Practice tactical pattern recognition")
        
        # Check time management
        if metrics['time_management']['time_pressure_percentage'] > 30:
            assessment.append("Improve time management in critical positions")
        
        # Check phase performance
        if metrics['phases']['opening']['accuracy'] < 60:
            assessment.append("Study opening principles and common patterns")
        if metrics['phases']['middlegame']['accuracy'] < 60:
            assessment.append("Work on positional understanding and planning")
        if metrics['phases']['endgame']['accuracy'] < 60:
            assessment.append("Practice basic endgame techniques")
            
        return assessment[:3] if assessment else ["Focus on general chess principles"]

    def _calculate_phase_accuracy(self, moves: List[Dict[str, Any]]) -> float:
        """Calculate accuracy for a specific phase."""
        if not moves:
            return 0.0
            
        total_accuracy = 0.0
        num_moves = 0
        
        for move in moves:
            if 'accuracy' in move:
                total_accuracy += move['accuracy']
                num_moves += 1
                
        return round(total_accuracy / max(1, num_moves), 2)

    def _calculate_resourcefulness(self, moves: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate resourcefulness metrics."""
        if not moves:
            return {
                'defensive_moves': 0,
                'winning_conversions': 0,
                'resourcefulness_score': 0.0,
                'analysis': 'No moves to analyze'
            }
            
        total_positions = len(moves)
        defensive_moves = 0
        winning_conversions = 0
        
        for move in moves:
            eval_before = self._convert_score(move.get('eval_before', 0))
            eval_after = self._convert_score(move.get('eval_after', 0))
            
            # Count defensive moves in bad positions
            if eval_before < -1.5 and eval_after > eval_before:
                defensive_moves += 1
            
            # Count successful winning conversions
            if eval_before > 1.5 and eval_after > 2.0:
                winning_conversions += 1
            
        # Calculate resourcefulness score
        resourcefulness_score = round((defensive_moves + winning_conversions) / total_positions * 100 if total_positions > 0 else 0, 2)
        
        # Generate analysis text
        if resourcefulness_score >= 80:
            analysis = "Excellent resourcefulness in critical positions"
        elif resourcefulness_score >= 60:
            analysis = "Good defensive skills and advantage conversion"
        elif resourcefulness_score >= 40:
            analysis = "Moderate ability to handle critical positions"
        else:
            analysis = "Room for improvement in defensive play and advantage conversion"
            
        return {
            'defensive_moves': defensive_moves,
            'winning_conversions': winning_conversions,
            'resourcefulness_score': resourcefulness_score,
            'analysis': analysis
        }

    def _calculate_metrics(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive metrics with proper frontend integration."""
        try:
            # Ensure moves exist and are in the correct format
            moves = analysis_data.get('moves', [])
            if not isinstance(moves, list):
                logger.error("Invalid moves data format")
                return self._get_default_metrics()
                
            is_white = analysis_data.get('is_white', True)
            
            # Calculate base metrics using enhanced calculator
            try:
                metrics = MetricsCalculator.calculate_game_metrics(moves, is_white)
            except Exception as e:
                logger.error(f"Error in MetricsCalculator: {str(e)}")
                metrics = self._get_default_metrics()
            
            # Return the metrics
            return metrics

        except Exception as e:
            logger.error(f"Error calculating metrics: {str(e)}")
            return self._get_default_metrics()

    def _get_default_metrics(self) -> Dict[str, Any]:
        """Return default metrics structure with zero values."""
        return {
            'overall': {
                'accuracy': 0,
                'mistakes': 0,
                'blunders': 0,
                'average_centipawn_loss': 0,
                'time_management_score': 0,
                'total_moves': 0
            },
            'phases': {
                'opening': {
                    'accuracy': 0,
                    'mistakes': 0,
                    'blunders': 0,
                    'average_centipawn_loss': 0,
                    'time_per_move': 0
                },
                'middlegame': {
                    'accuracy': 0,
                    'mistakes': 0,
                    'blunders': 0,
                    'average_centipawn_loss': 0,
                    'time_per_move': 0
                },
                'endgame': {
                    'accuracy': 0,
                    'mistakes': 0,
                    'blunders': 0,
                    'average_centipawn_loss': 0,
                    'time_per_move': 0
                }
            },
            'tactics': {
                'opportunities_found': 0,
                'opportunities_missed': 0,
                'total_opportunities': 0,
                'tactical_accuracy': 0
            },
            'time_management': {
                'time_pressure_mistakes': 0,
                'average_time_per_move': 0,
                'time_management_score': 0
            },
            'positional': {
                'piece_placement_score': 0,
                'center_control_score': 0,
                'king_safety_score': 0,
                'pawn_structure_score': 0
            },
            'advantage': {
                'maximum_advantage': 0,
                'average_advantage': 0,
                'advantage_transitions': 0
            },
            'resourcefulness': {
                'defense_score': 0,
                'counter_play_score': 0,
                'recovery_score': 0
            }
        }

    def _get_default_phase_metrics(self) -> Dict[str, Any]:
        """Return default phase metrics."""
        return {
            'accuracy': 0.0,
            'moves': 0,
            'mistakes': 0,
            'blunders': 0,
            'critical_moves': 0,
            'time_management': {
                'average_time': 0.0,
                'time_variance': 0.0,
                'time_consistency': 0.0,
                'time_pressure_moves': 0,
                'time_management_score': 0.0,
                'time_pressure_percentage': 0.0
            }
        }

    def _calculate_phase_metrics(self, moves: List[Dict[str, Any]], phase: str) -> Dict[str, Any]:
        """Calculate metrics for a specific game phase."""
        phase_moves = [m for m in moves if m.get('phase') == phase]
        if not phase_moves:
            return {
                'moves': 0,
                'tactical_moves': 0,
                'critical_moves': 0,
                'average_time': 0.0
            }
            
        return {
            'moves': len(phase_moves),
            'tactical_moves': sum(1 for m in phase_moves if m.get('is_tactical', False)),
            'critical_moves': sum(1 for m in phase_moves if m.get('is_critical', False)),
            'average_time': sum(m.get('time_spent', 0) for m in phase_moves) / len(phase_moves)
        }

    def _calculate_tactical_success_rate(self, moves: List[Dict[str, Any]]) -> float:
        """Calculate the success rate of tactical opportunities."""
        tactical_positions = [m for m in moves if m.get('has_tactic', False)]
        if not tactical_positions:
            return 0.0
        
        successful_tactics = sum(1 for m in tactical_positions if not m.get('missed_tactic', False))
        return (successful_tactics / len(tactical_positions)) * 100

    def _calculate_critical_time_usage(self, moves: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate time usage in critical positions."""
        critical_moves = [m for m in moves if m.get('is_critical', False)]
        if not critical_moves:
            return {
                'average_time': 0,
                'good_decisions': 0,
                'rushed_decisions': 0
            }
        
        avg_time = sum(m.get('time_spent', 0) for m in critical_moves) / len(critical_moves)
        good_decisions = sum(1 for m in critical_moves if m.get('time_spent', 0) >= avg_time)
        
        return {
            'average_time': avg_time,
            'good_decisions': good_decisions,
            'rushed_decisions': len(critical_moves) - good_decisions
        }

    def _process_piece_positions(self, board: chess.Board) -> List[bool]:
        """Process piece positions and return a list of boolean values."""
        piece_positions = []
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece is not None and piece.color is not None:
                piece_positions.append(piece.color == chess.WHITE)
        return piece_positions

    def _calculate_material_count(self, board: chess.Board) -> float:
        """Calculate total material count on the board."""
        try:
            piece_values = {
                chess.PAWN: 1.0,
                chess.KNIGHT: 3.0,
                chess.BISHOP: 3.0,
                chess.ROOK: 5.0,
                chess.QUEEN: 9.0,
                chess.KING: 0.0  # Not counted in material total
            }
            
            total = 0.0
            for piece_type in piece_values:
                total += len(board.pieces(piece_type, chess.WHITE)) * piece_values[piece_type]
                total += len(board.pieces(piece_type, chess.BLACK)) * piece_values[piece_type]
            return total
        except Exception as e:
            logger.error(f"Error calculating material count: {str(e)}")
            return 32.0  # Default to starting material count

    def _is_development_move(self, move: str) -> bool:
        """Check if a move is a development move."""
        try:
            if not move or len(move) < 2:
                return False
            
            # Check for piece development moves
            if move[0] in ['N', 'B', 'Q', 'K'] and move[1] in ['b', 'c', 'd', 'e', 'f', 'g']:
                return True
            
            # Check for pawn moves to central squares
            if move.lower() in ['e4', 'd4', 'e5', 'd5', 'c4', 'f4', 'c5', 'f5']:
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking development move: {str(e)}")
            return False

    def _safe_score_compare(self, score: Optional[int], threshold: int) -> bool:
        """Safely compare a score with a threshold, handling None values."""
        if score is None:
            return False
        return score > threshold

    def _is_tactical_move(self, board: chess.Board, move: chess.Move, eval_change: float, analysis: Optional[Union[Dict[str, Any], chess.engine.InfoDict]]) -> bool:
        """Determine if a move is tactical."""
        try:
            # First check basic tactical features
            if board.is_capture(move) or board.gives_check(move):
                return True
            
            if analysis is None:
                return False
            
            # Get score from analysis
            score = analysis.get('score')
            if score is None:
                return False
            
            # Convert score to centipawns if it's an engine score object
            if isinstance(score, (chess.engine.Score, chess.engine.PovScore)):
                score_value = self._convert_score(score)
            else:
                try:
                    score_value = float(score)
                except (TypeError, ValueError):
                    return False
            
            return (
                abs(eval_change) > 1.0 or
                abs(score_value) > 2.0  # Consider positions with score > 2 pawns as tactical
            )
            
        except Exception as e:
            logger.error(f"Error checking tactical move: {str(e)}")
            return board.is_capture(move) or board.gives_check(move)

    def _get_default_feedback(self) -> Dict[str, Any]:
        """Return default feedback structure."""
        return {
            'source': 'system',
            'feedback': {
                'strengths': ['Analysis not available'],
                'weaknesses': ['Analysis not available'],
            'critical_moments': [],
                'improvement_areas': ['Try analyzing the game again'],
            'opening': {
                    'analysis': 'Analysis not available',
                    'suggestion': 'Try analyzing the game again to get opening insights'
            },
            'middlegame': {
                    'analysis': 'Analysis not available',
                    'suggestion': 'Try analyzing the game again to get middlegame insights'
            },
            'endgame': {
                    'analysis': 'Analysis not available',
                    'suggestion': 'Try analyzing the game again to get endgame insights'
                }
            },
            'metrics': self._get_default_metrics()['overall']
        }

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
