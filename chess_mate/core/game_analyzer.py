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
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential
import random
from openai import OpenAI
from .ai_feedback import AIFeedbackGenerator
import json
import re
from .analysis.metrics_calculator import MetricsCalculator
import time

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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def analyze_move(self, board: chess.Board, move: chess.Move, time_spent: float = 0, total_time: float = 900, increment: float = 0) -> Dict[str, Any]:
        """
        Analyze a single move with enhanced tactical and time management analysis.
        
        Args:
            board: Current board position
            move: The move to analyze
            time_spent: Time spent on the move in seconds
            total_time: Total time allocated for the game in seconds
            increment: Time increment per move in seconds
            
        Returns:
            Dictionary containing move analysis details
        """
        try:
            # Get evaluation before move
            evaluation_before = self.engine.evaluate_position(board)
            
            # Make the move and get evaluation after
            board.push(move)
            evaluation_after = self.engine.evaluate_position(board)
            
            # Validate time metrics
            time_metrics = self._validate_time_metrics([time_spent], total_time, increment)
            
            # Get tactical analysis
            tactical_analysis = self._is_tactical_move(board, move, evaluation_before, evaluation_after)
            
            # Determine move phase
            phase = self._determine_game_phase(board)
            
            # Calculate move accuracy
            accuracy = self._calculate_move_accuracy(evaluation_before, evaluation_after)
            
            # Determine if it's a critical move
            is_critical = self._is_critical_move(board, evaluation_before, evaluation_after)
            
            return {
                'move': move.uci(),
                'phase': phase,
                'evaluation_before': round(evaluation_before, 2),
                'evaluation_after': round(evaluation_after, 2),
                'accuracy': round(accuracy, 2),
                'is_tactical': tactical_analysis['is_tactical'],
                'tactical_features': tactical_analysis['features'],
                'tactical_score': tactical_analysis['score'],
                'position_complexity': tactical_analysis['complexity'],
                'is_critical': is_critical,
                'time_spent': time_metrics['normalized_times'][0] if time_metrics['normalized_times'] else 0,
                'time_pressure': time_metrics['time_pressure_moves'] > 0,
                'time_management_score': time_metrics['time_management_score']
            }
            
        except Exception as e:
            logger.error(f"Error analyzing move: {str(e)}")
            return {
                'move': move.uci() if move else '',
                'error': str(e)
            }

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
        """Convert a chess engine score to a float value from player's perspective."""
        try:
            if score is None:
                return 0.0
            
            # Convert to float first
            if isinstance(score, (int, float)):
                raw_score = float(score)
            elif isinstance(score, chess.engine.Cp):
                raw_score = float(score.score()) / 100.0
            elif isinstance(score, chess.engine.Mate):
                mate_score = score.score()
                if mate_score is None:
                    return 0.0
                raw_score = 10000.0 if mate_score > 0 else -10000.0
            else:
                return 0.0
            
            # Adjust for player perspective
            return raw_score if is_white else -raw_score
            
        except Exception as e:
            logger.error(f"Error converting score: {str(e)}")
            return 0.0

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def analyze_single_game(self, game: Game, depth: int = 20) -> List[Dict[str, Any]]:
        """Analyze a single game with retry logic."""
        if not game.pgn:
            raise ValueError("No PGN data provided for analysis")

        try:
            # Parse PGN and determine player color
            pgn_io = io.StringIO(game.pgn)
            game_node: Optional[chess.pgn.Game] = chess.pgn.read_game(pgn_io)
            if not game_node:
                raise ValueError("Invalid PGN data: Could not parse game")
            
            # Determine if the user is playing as white
            is_white = game.white == game.user.username
            
            # Get moves from PGN
            moves: List[chess.Move] = []
            board = chess.Board()
            node: chess.pgn.GameNode = game_node
            while node.variations:
                next_node: chess.pgn.ChildNode = node.variations[0]
                if next_node.move:
                    moves.append(next_node.move)
                node = next_node
            
            # Analyze moves with proper color perspective
            analysis = self._analyze_moves(moves, depth, is_white)
            
            # Cache the analysis results
            if hasattr(game, 'id'):
                cache_key = f"game_analysis_{game.id}"
                cache.set(cache_key, analysis, timeout=3600)  # Cache for 1 hour
            
            return analysis
            
        except Exception as e:
            if hasattr(game, 'id'):
                logger.error(f"Error analyzing game {game.id}: {str(e)}")
            else:
                logger.error(f"Error analyzing game: {str(e)}")
            raise

    def _parse_pgn(self, game: Game) -> List[chess.Move]:
        """Parse PGN data into a list of moves."""
        if not game.pgn:
            raise ValueError("Empty PGN data")
            
        try:
            pgn_str = game.pgn.strip()
        except (AttributeError, TypeError):
            raise ValueError("Invalid PGN data format")

        if not pgn_str:
            raise ValueError("Empty PGN data")

        pgn_game: Optional[chess.pgn.Game] = chess.pgn.read_game(io.StringIO(pgn_str))
        if not pgn_game:
            raise ValueError("Invalid PGN data: Could not parse game")

        moves: List[chess.Move] = []
        board = chess.Board()
        current_node: chess.pgn.GameNode = pgn_game

        while current_node and current_node.variations:
            next_node: chess.pgn.ChildNode = current_node.variations[0]
            if next_node.move:
                moves.append(next_node.move)
            current_node = next_node

        if not moves:
            raise ValueError("Invalid PGN data: No moves found")

        return moves

    def _analyze_moves(self, moves: List[chess.Move], depth: int, is_white: bool = True) -> List[Dict[str, Any]]:
        """Analyze a list of moves."""
        board = chess.Board()
        analysis = []
        last_score = 0
        move_number = 1
        current_is_white = True  # Track whose move it is

        for move in moves:
            try:
                # Analyze move from current player's perspective
                move_analysis = self.analyze_move(board, move, depth, is_white)
                current_score = move_analysis["score"]
                
                # Calculate evaluation drop from player's perspective
                eval_drop = (last_score - current_score) if current_is_white == is_white else (current_score - last_score)
                eval_improvement = max(0, -eval_drop)  # Positive when position improves

                # Determine game phase
                total_pieces = len(board.piece_map())
                phase = 'opening' if move_number <= 10 else ('endgame' if total_pieces <= 12 else 'middlegame')

                # Add additional analysis data
                move_analysis.update({
                "move_number": move_number,
                "evaluation_drop": eval_drop,
                    "evaluation_improvement": eval_improvement,
                    "is_mistake": eval_drop > 200,
                    "is_blunder": eval_drop > 400,
                    "is_critical": abs(current_score) > 150 or abs(eval_drop) > 150,
                    "is_tactical": board.is_capture(move) or board.gives_check(move) or abs(eval_drop) > 150,
                    "phase": phase,
                    "is_white": current_is_white == is_white  # Add player color information
                })

                analysis.append(move_analysis)
                last_score = current_score
                move_number += 1
                
                # Make the move on the board
                board.push(move)
                current_is_white = not current_is_white  # Toggle player color
            
            except Exception as e:
                logger.error(f"Error analyzing move: {str(e)}")
                # Create neutral evaluation on error
                analysis.append(self._create_neutral_evaluation(board, move, depth, 0.0))
                board.push(move)
                current_is_white = not current_is_white

        return analysis

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
                'timestamp': datetime.now().isoformat()
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

    def generate_feedback(self, analysis_results: Dict[str, Any], game: Any) -> Dict[str, Any]:
        """Generate structured feedback from analysis results."""
        try:
            # Extract moves from the structured results
            moves = analysis_results.get('moves', [])
            if not moves:
                raise ValueError("No moves found in analysis results")
            
            # Calculate metrics
            metrics = self._calculate_metrics({'moves': moves})
            
            # Convert GameMetrics to Dict for the feedback generators
            metrics_dict: Dict[str, Any] = {
                'overall': metrics['overall'],
                'phases': metrics['phases'],
                'tactics': metrics['tactics'],
                'time_management': metrics['time_management'],
                'positional': metrics['positional'],
                'advantage': metrics['advantage'],
                'resourcefulness': metrics['resourcefulness']
            }
            
            # Generate structured feedback
            feedback = {
                'analysis_complete': True,
                'analysis_results': {
                    'summary': metrics_dict,
                    'strengths': self._identify_strengths(metrics_dict),
                    'weaknesses': self._identify_weaknesses(metrics_dict),
                    'critical_moments': self._identify_critical_moments(moves),
                    'improvement_areas': self._generate_overall_assessment(metrics_dict)
                },
                'depth': analysis_results.get('depth', 20),
                'source': 'stockfish',
                'timestamp': datetime.now().isoformat()
            }
            
            return feedback

        except Exception as e:
            logger.error(f"Error generating feedback: {str(e)}")
            return {
                'analysis_complete': True,
                'analysis_results': {
                    'summary': {
                        'overall': {'accuracy': 0.0, 'mistakes': 0, 'blunders': 0},
            'phases': {},
            'tactics': {},
            'time_management': {},
                        'positional': {},
                        'advantage': {},
                        'resourcefulness': None
                    },
                    'strengths': [],
                    'weaknesses': [],
                    'critical_moments': [],
                    'improvement_areas': "Analysis failed"
                },
                'depth': 20,
                'source': 'stockfish',
                'timestamp': datetime.now().isoformat()
            }

    def _generate_overall_assessment(self, metrics: Dict[str, Any]) -> str:
        """Generate an overall assessment based on metrics."""
        accuracy = metrics['overall']['accuracy']
        if accuracy >= 90:
            return "Excellent performance with very few mistakes"
        elif accuracy >= 80:
            return "Strong play with some minor inaccuracies"
        elif accuracy >= 70:
            return "Solid performance with room for improvement"
        elif accuracy >= 60:
            return "Several mistakes affected the game outcome"
        else:
            return "Significant improvements needed in key areas"

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

            feedback_text = response.choices[0].message.content
            if not feedback_text:
                logger.error("Empty response from OpenAI")
                return None
                
            try:
                # Parse the response as JSON
                feedback_data = json.loads(feedback_text)
                
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
        """Identify areas for improvement based on analysis metrics."""
        weaknesses = []
        
        # Check accuracy thresholds
        if metrics['overall']['accuracy'] < 60:
            weaknesses.append("Overall accuracy needs improvement")
        
        # Check mistakes and blunders
        if metrics['overall']['blunders'] > 2:
            weaknesses.append("Critical mistakes in key positions")
        
        # Check tactical performance
        if metrics['tactics']['success_rate'] < 50:
            weaknesses.append("Missed tactical opportunities")
        
        # Check time management
        if metrics['time_management']['time_pressure_moves'] > 10:
            weaknesses.append("Time management under pressure")
        
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

    def _calculate_resourcefulness(self, moves: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate resourcefulness metrics."""
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
            
            return {
            'defensive_moves': defensive_moves,
            'winning_conversions': winning_conversions,
            'resourcefulness_score': round((defensive_moves + winning_conversions) / total_positions * 100 if total_positions > 0 else 0, 2)
        }

    def _calculate_advantage_metrics(self, moves: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate metrics related to advantage handling."""
        winning_positions = 0
        converted_advantages = 0
        
        for move in moves:
            eval_before = self._convert_score(move.get('eval_before', 0))
            eval_after = self._convert_score(move.get('eval_after', 0))
            
            # Count positions where player had significant advantage
            if eval_before > 1.5:
                winning_positions += 1
                if eval_after > eval_before:
                    converted_advantages += 1
        
        return {
            'winning_positions': winning_positions,
            'converted_advantages': converted_advantages,
            'conversion_rate': round(converted_advantages / winning_positions * 100 if winning_positions > 0 else 0, 2)
        }

    def _analyze_position_quality(self, moves: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the quality of positions throughout the game."""
        if not moves:
            return {
                'winning_positions': 0,
                'losing_positions': 0,
                'critical_positions': 0,
                'average_position_score': 0.0
            }
        
        winning_positions = 0
        losing_positions = 0
        critical_positions = 0
        total_score = 0.0
        
        for move in moves:
            eval_after = self._convert_score(move.get('eval_after', 0))
            total_score += eval_after
            
            if eval_after > 1.5:
                winning_positions += 1
            elif eval_after < -1.5:
                losing_positions += 1
            
            if abs(eval_after) > 2.0:
                critical_positions += 1
        
        return {
            'winning_positions': winning_positions,
            'losing_positions': losing_positions,
            'critical_positions': critical_positions,
            'average_position_score': round(total_score / len(moves), 2)
        }

    def _calculate_metrics(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive metrics with proper frontend integration."""
        try:
            moves = analysis_data.get('moves', [])
            is_white = analysis_data.get('is_white', True)
            
            # Calculate base metrics using enhanced calculator
            metrics = MetricsCalculator.calculate_game_metrics(moves, is_white)
            
            # Enhance the response structure for frontend
            enhanced_metrics = {
                'overall': {
                    'accuracy': metrics['overall']['accuracy'],
                    'consistency': metrics['overall']['consistency_score'],
                    'mistakes': metrics['overall']['mistakes'],
                    'blunders': metrics['overall']['blunders'],
                    'inaccuracies': metrics['overall']['inaccuracies'],
                    'quality_moves': metrics['overall']['quality_moves'],
                    'critical_positions': metrics['overall']['critical_positions'],
                    'position_quality': metrics['overall']['position_quality']
                },
                'phases': {
                    'opening': {
                        'accuracy': metrics['phases']['opening']['accuracy'],
                        'moves': len(metrics['phases']['opening']['moves']),
                        'mistakes': metrics['phases']['opening']['mistakes'],
                        'blunders': metrics['phases']['opening']['blunders'],
                        'critical_moves': metrics['phases']['opening']['critical_moves'],
                        'average_complexity': metrics['phases']['opening']['average_complexity'],
                        'time_management': metrics['phases']['opening']['time_management']
                    },
                    'middlegame': {
                        'accuracy': metrics['phases']['middlegame']['accuracy'],
                        'moves': len(metrics['phases']['middlegame']['moves']),
                        'mistakes': metrics['phases']['middlegame']['mistakes'],
                        'blunders': metrics['phases']['middlegame']['blunders'],
                        'critical_moves': metrics['phases']['middlegame']['critical_moves'],
                        'average_complexity': metrics['phases']['middlegame']['average_complexity'],
                        'time_management': metrics['phases']['middlegame']['time_management']
                    },
                    'endgame': {
                        'accuracy': metrics['phases']['endgame']['accuracy'],
                        'moves': len(metrics['phases']['endgame']['moves']),
                        'mistakes': metrics['phases']['endgame']['mistakes'],
                        'blunders': metrics['phases']['endgame']['blunders'],
                        'critical_moves': metrics['phases']['endgame']['critical_moves'],
                        'average_complexity': metrics['phases']['endgame']['average_complexity'],
                        'time_management': metrics['phases']['endgame']['time_management']
                    }
                },
                'tactics': {
                    'opportunities': metrics['tactics']['opportunities'],
                    'successful': metrics['tactics']['successful'],
                    'missed': metrics['tactics']['missed'],
                    'success_rate': metrics['tactics']['success_rate'],
                    'tactical_score': metrics['tactics']['tactical_score']
                },
                'time_management': {
                    'average_time': metrics['time_management']['average_time'],
                    'time_pressure_moves': metrics['time_management']['time_pressure_moves'],
                    'time_pressure_percentage': metrics['time_management']['time_pressure_percentage'],
                    'time_variance': metrics['time_management']['time_variance'],
                    'critical_time_average': metrics['time_management']['critical_time_average'],
                    'total_time': metrics['time_management']['total_time']
                },
                'advantage': {
                    'winning_positions': metrics['advantage']['winning_positions'],
                    'conversion_rate': metrics['advantage']['conversion_rate'],
                    'average_advantage': metrics['advantage']['average_advantage'],
                    'max_advantage': metrics['advantage']['max_advantage'],
                    'advantage_retention': metrics['advantage']['advantage_retention']
                },
                'resourcefulness': {
                    'defensive_score': metrics['resourcefulness']['defensive_score'],
                    'counter_play': metrics['resourcefulness']['counter_play'],
                    'recovery_rate': metrics['resourcefulness']['recovery_rate'],
                    'critical_defense': metrics['resourcefulness']['critical_defense'],
                    'best_move_finding': metrics['resourcefulness']['best_move_finding']
                }
            }

            return enhanced_metrics

        except Exception as e:
            logger.error(f"Error calculating metrics: {str(e)}")
            return self._get_default_metrics()

    def _get_default_metrics(self) -> Dict[str, Any]:
        """Return default metrics structure matching frontend requirements."""
        return {
            'overall': {
                'accuracy': 0.0,
                'consistency': 0.0,
                'mistakes': 0,
                'blunders': 0,
                'inaccuracies': 0,
                'quality_moves': 0,
                'critical_positions': 0,
                'position_quality': 0.0
            },
            'phases': {
                'opening': self._get_default_phase_metrics(),
                'middlegame': self._get_default_phase_metrics(),
                'endgame': self._get_default_phase_metrics()
            },
            'tactics': {
                'opportunities': 0,
                'successful': 0,
                'missed': 0,
                'success_rate': 0.0,
                'tactical_score': 0.0
            },
            'time_management': {
                'average_time': 0.0,
                'time_pressure_moves': 0,
                'time_pressure_percentage': 0.0,
                'time_variance': 0.0,
                'critical_time_average': 0.0,
                'total_time': 0.0
            },
            'advantage': {
                'winning_positions': 0,
                'conversion_rate': 0.0,
                'average_advantage': 0.0,
                'max_advantage': 0.0,
                'advantage_retention': 0.0
            },
            'resourcefulness': {
                'defensive_score': 0.0,
                'counter_play': 0.0,
                'recovery_rate': 0.0,
                'critical_defense': 0.0,
                'best_move_finding': 0.0
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
            'average_complexity': 0.0,
            'time_management': {
                'average_time': 0.0,
                'time_pressure_moves': 0,
                'time_pressure_percentage': 0.0,
                'time_variance': 0.0,
                'critical_time_average': 0.0,
                'total_time': 0.0
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

    def _is_tactical_move(self, board: chess.Board, move: chess.Move, evaluation_before: float, evaluation_after: float) -> Dict[str, Any]:
        """
        Enhanced tactical move classification with detailed analysis.
        
        Args:
            board: Current board position
            move: The move to analyze
            evaluation_before: Position evaluation before the move
            evaluation_after: Position evaluation after the move
        
        Returns:
            Dictionary containing tactical analysis details
        """
        is_tactical = False
        tactical_features = []
        tactical_score = 0.0
        
        # Get move details
        moving_piece = board.piece_at(move.from_square)
        captured_piece = board.piece_at(move.to_square)
        
        if not moving_piece:
            return {
                'is_tactical': False,
                'features': [],
                'score': 0.0,
                'complexity': 0.0
            }
        
        # 1. Material gain analysis
        if captured_piece:
            piece_values = {
                chess.PAWN: 1,
                chess.KNIGHT: 3,
                chess.BISHOP: 3,
                chess.ROOK: 5,
                chess.QUEEN: 9
            }
            
            attacker_value = piece_values.get(moving_piece.piece_type, 0)
            captured_value = piece_values.get(captured_piece.piece_type, 0)
            
            if captured_value > attacker_value:
                is_tactical = True
                tactical_features.append('winning_capture')
                tactical_score += min(1.0, (captured_value - attacker_value) / 4)
            elif captured_value == attacker_value:
                tactical_features.append('equal_capture')
                tactical_score += 0.3
        
        # 2. Check analysis
        if board.is_check():
            is_tactical = True
            tactical_features.append('check')
            tactical_score += 0.4
            
            # Check if it's checkmate
            if board.is_checkmate():
                tactical_features.append('checkmate')
                tactical_score = 1.0
        
        # 3. Position improvement analysis
        eval_improvement = evaluation_after - evaluation_before
        if abs(eval_improvement) >= 1.5:  # Significant improvement
            is_tactical = True
            tactical_features.append('major_improvement')
            tactical_score += min(1.0, abs(eval_improvement) / 3)
        elif abs(eval_improvement) >= 0.8:  # Moderate improvement
            is_tactical = True
            tactical_features.append('moderate_improvement')
            tactical_score += min(0.7, abs(eval_improvement) / 3)
        
        # 4. Piece activity analysis
        to_square_attacks = len(board.attackers(moving_piece.color, move.to_square))
        if to_square_attacks >= 2:
            tactical_features.append('multiple_attacks')
            tactical_score += 0.3
            is_tactical = True
        
        # 5. Calculate position complexity
        complexity = self._calculate_position_complexity(board)
        
        # Normalize tactical score
        tactical_score = min(1.0, tactical_score)
            
        return {
            'is_tactical': is_tactical,
            'features': tactical_features,
            'score': round(tactical_score, 3),
            'complexity': round(complexity, 3)
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
