"""
This module provides functionality for analyzing chess games using the Stockfish engine.
It includes classes and methods to analyze single or multiple games, save analysis results to the
database, and generate feedback based on the analysis.
"""

import io
import json
import logging
import os
import random
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict, Union, cast

import chess
import chess.engine
import chess.pgn
from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError, models, transaction
from django.utils import timezone
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .analysis.feedback_generator import FeedbackGenerator
from .analysis.metrics_calculator import MetricsCalculator, MetricsError
from .analysis.stockfish_analyzer import StockfishAnalyzer
from .cache import CACHE_BACKEND_REDIS, cache_delete, cache_get, cache_set
from .error_handling import (
    ExternalServiceError,
    ResourceNotFoundError,
    TaskError,
    ValidationError,
    AnalysisError,
    MetricsError
)
from .models import Game, GameAnalysis
from .task_manager import (TASK_STATUS_FAILURE, TASK_STATUS_SUCCESS, TaskManager)

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
            self.engine_analyzer = StockfishAnalyzer()
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.feedback_generator = FeedbackGenerator()
            self.metrics_calculator = MetricsCalculator()
            self.task_manager = TaskManager()
            logger.info("Successfully initialized game analyzer components")
        except Exception as e:
            logger.error("Failed to initialize game analyzer: %s", str(e))
            raise

    def __del__(self):
        """Ensure engine is properly closed."""
        self.cleanup()

    def cleanup(self):
        """Cleanup resources."""
        try:
            if hasattr(self, "engine_analyzer"):
                self.engine_analyzer.cleanup()
                logger.info("Successfully cleaned up Stockfish analyzer")
        except Exception as e:
            logger.error("Error cleaning up game analyzer: %s", str(e))

    def analyze_game(self, game: Game, depth=20, use_ai=True, progress_callback=None, task_id=None):
        """
        Analyze a chess game and save the results.
        
        Args:
            game: Game instance to analyze
            depth: Stockfish analysis depth
            use_ai: Whether to use AI for feedback generation
            progress_callback: Optional callback function to report progress
            task_id: Optional task ID for tracking in the task manager
            
        Returns:
            GameAnalysis model instance with the analysis results
        """
        analysis_result = None
        
        try:
            # Init progress tracking
            if progress_callback:
                progress_callback(10, "Parsing game data")
            
            # Extract game details
            pgn = game.pgn
            if not pgn:
                raise ValidationError("Game has no PGN data")
                
            # If we have a task ID, update its status
            if task_id and self.task_manager:
                self.task_manager.update_task_status(
                    task_id=task_id, 
                    status="PROCESSING",
                    progress=15,
                    message="Analyzing game"
                )
            
            # Check if we already have an analysis for this game
            try:
                existing_analysis = GameAnalysis.objects.get(game=game)
                logger.info(f"Found existing analysis for game {game.id}")
                
                # Check if analysis is complete by looking at analysis_data
                if (existing_analysis.analysis_data.get('status') == 'complete' and 
                    existing_analysis.moves):
                    if progress_callback:
                        progress_callback(100, "Using existing analysis")
                    # Update task if we have one
                    if task_id and self.task_manager:
                        self.task_manager.update_task_status(
                            task_id=task_id, 
                            status="SUCCESS",
                            progress=100,
                            message="Analysis complete (cached)"
                        )
                    return existing_analysis
                    
                # Otherwise, continue with new analysis
                logger.info(f"Existing analysis is incomplete, recreating for game {game.id}")
                analysis_result = existing_analysis
                # Mark as in progress
                analysis_result.analysis_data['status'] = 'in_progress'
                analysis_result.save(update_fields=["analysis_data"])
            except GameAnalysis.DoesNotExist:
                # Create a new analysis
                logger.info(f"Creating new analysis for game {game.id}")
                analysis_result = GameAnalysis.objects.create(
                    game=game,
                    analysis_data={'status': 'in_progress'}
                )
            
            # Initialize Stockfish analyzer
            if progress_callback:
                progress_callback(15, "Initializing chess engine")
                
            if task_id and self.task_manager:
                self.task_manager.update_task_status(
                    task_id=task_id,
                    status="PROCESSING",
                    progress=20,
                    message="Initializing chess engine"
                )
            
            # Analyze the game with Stockfish
            if progress_callback:
                progress_callback(20, "Analyzing moves with Stockfish")
                
            analyzed_moves = self.engine_analyzer.analyze_pgn_game(
                pgn, depth=depth, callback=lambda p, m: progress_callback(20 + int(p * 0.5), m) if progress_callback else None
            )
            
            if progress_callback:
                progress_callback(70, "Calculating metrics")
                
            if task_id and self.task_manager:
                self.task_manager.update_task_status(
                    task_id=task_id,
                    status="PROCESSING",
                    progress=70,
                    message="Calculating metrics"
                )
                
            # Calculate metrics
            time_data = []  # Extract time data if available
            try:
                metrics = self.metrics_calculator.calculate_game_metrics(analyzed_moves, time_data)
            except MetricsError as me:
                logger.warning(f"Error calculating metrics: {str(me)}")
                # Provide default metrics structure with error information
                metrics = {
                    "overall": {"accuracy": 0.0, "error": str(me)},
                    "phases": {"opening": {}, "middlegame": {}, "endgame": {}},
                    "tactics": {},
                    "time_management": {},
                    "positional": {},
                    "advantage": {},
                    "resourcefulness": {},
                    "calculation_error": str(me)
                }
                if progress_callback:
                    progress_callback(75, f"Using fallback metrics due to calculation error: {str(me)}")
                
                if task_id and self.task_manager:
                    self.task_manager.update_task_status(
                        task_id=task_id,
                        status="PROCESSING",
                        progress=75,
                        message=f"Using fallback metrics due to calculation error"
                    )
            
            # Generate feedback with AI if requested
            feedback = {}
            if use_ai and self.feedback_generator:
                if progress_callback:
                    progress_callback(80, "Generating AI feedback")
                
                if task_id and self.task_manager:
                    self.task_manager.update_task_status(
                        task_id=task_id,
                        status="PROCESSING",
                        progress=80,
                        message="Generating AI feedback"
                    )
                
                try:
                    # Create a combined analysis result dict to match the expected format
                    analysis_data = {
                        "moves": analyzed_moves,
                        "metrics": {
                            "summary": metrics
                        }
                    }
                    
                    # Call with a single argument (the combined analysis result)
                    feedback = self.feedback_generator.generate_feedback(analysis_data)
                except Exception as e:
                    logger.error(f"Error generating AI feedback: {str(e)}")
                    # Continue without AI feedback
                    feedback = {"error": f"Failed to generate AI feedback: {str(e)}"}
            
            if progress_callback:
                progress_callback(90, "Saving analysis results")
                
            if task_id and self.task_manager:
                self.task_manager.update_task_status(
                    task_id=task_id,
                    status="PROCESSING",
                    progress=90,
                    message="Saving analysis results"
                )
                
            # Save the analysis data
            analysis_data = analysis_result.analysis_data
            analysis_data['metrics'] = metrics
            analysis_data['status'] = 'complete'
            analysis_data['completed_at'] = timezone.now().isoformat()
            analysis_data['engine_version'] = self.engine_analyzer.get_engine_version()
            
            analysis_result.analysis_data = analysis_data
            analysis_result.feedback = feedback.get('feedback', '') if isinstance(feedback, dict) else str(feedback)
            
            # Save moves separately using moves property
            analysis_result.analysis_data['moves'] = analyzed_moves
            
            # If the model has accuracy fields, update them
            if hasattr(analysis_result, 'accuracy_white') and 'overall' in metrics:
                analysis_result.accuracy_white = metrics.get('overall', {}).get('white_accuracy', 0)
            if hasattr(analysis_result, 'accuracy_black') and 'overall' in metrics:
                analysis_result.accuracy_black = metrics.get('overall', {}).get('black_accuracy', 0)
                
            analysis_result.save()
            
            if progress_callback:
                progress_callback(100, "Analysis complete")
                
            if task_id and self.task_manager:
                self.task_manager.update_task_status(
                    task_id=task_id,
                    status="SUCCESS",
                    progress=100,
                    message="Analysis complete"
                )

            return analysis_result

        except Exception as e:
            logger.exception(f"Error during game analysis: {str(e)}")
            
            # Update the analysis status if we created one
            if analysis_result:
                try:
                    # Mark analysis as failed
                    analysis_data = analysis_result.analysis_data
                    analysis_data['status'] = 'failed'
                    analysis_data['error'] = str(e)
                    analysis_result.analysis_data = analysis_data
                    analysis_result.save()
                except Exception as save_error:
                    logger.error(f"Error updating analysis status: {str(save_error)}")
            
            # Update task status if we have a task ID
            if task_id and self.task_manager:
                self.task_manager.update_task_status(
                    task_id=task_id,
                    status="FAILURE",
                    progress=0,
                    message=f"Analysis failed: {str(e)}",
                    error=str(e)
                )
            
            # Re-raise as AnalysisError
            raise AnalysisError(f"Game analysis failed: {str(e)}")
            
        finally:
            # Always clean up resources
            try:
                self.cleanup()
            except Exception as cleanup_error:
                logger.error(f"Error during cleanup: {str(cleanup_error)}")
                # Don't raise here to avoid masking the original error

    def _perform_analysis(self, game: Game, depth: int, progress_callback=None) -> Dict[str, Any]:
        """
        Perform the actual game analysis.
        
        Args:
            game: The game to analyze
            depth: Stockfish analysis depth
            progress_callback: Optional callback function to report progress
        
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Extract game data
            if progress_callback:
                progress_callback(15, "Extracting game data")
                
            game_data = self._get_game_data(game.pgn)
            if not game_data:
                raise AnalysisError("Failed to extract game data from PGN")

            # Analyze moves
            if progress_callback:
                progress_callback(30, "Analyzing moves")
                
            moves_analysis = self._analyze_moves(game_data["moves"], depth, progress_callback)
            if not moves_analysis:
                raise AnalysisError("Failed to analyze moves")

            # Analyze positions
            if progress_callback:
                progress_callback(60, "Analyzing positions")
                
            positions_analysis = self._analyze_positions(game_data["positions"], depth, progress_callback)
            if not positions_analysis:
                raise AnalysisError("Failed to analyze positions")

            # Calculate metrics
            if progress_callback:
                progress_callback(80, "Calculating metrics")
            
            try:    
                metrics = self.metrics_calculator.calculate_game_metrics(
                    moves=moves_analysis,
                    time_data=game_data.get("time_data", [])
                )
            except MetricsError as e:
                logger.error(f"Metrics calculation error: {str(e)}")
                # Create default metrics if calculation fails
                metrics = MetricsCalculator._get_default_metrics()
                logger.info("Using default metrics due to calculation error")

            # Compile results
            analysis_result = {
                "analysis_results": {
                    "moves": moves_analysis,
                    "positions": positions_analysis,
                    "metrics": metrics
                },
                "metadata": {
                "game_id": game.id,
                    "analysis_depth": depth,
                    "analysis_timestamp": timezone.now().isoformat(),
                    "engine_version": self.engine_analyzer.get_engine_version()
                }
            }

            return analysis_result

        except MetricsError as e:
            logger.error(f"Metrics error: {str(e)}")
            raise AnalysisError(f"Analysis failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error during analysis: {str(e)}")
            raise AnalysisError(f"Analysis failed: {str(e)}")

    def _get_game_data(self, pgn: str) -> Dict[str, Any]:
        """
        Extract game data from the PGN.

        Args:
            pgn: The PGN string to analyze

        Returns:
            Dict containing game data including moves and positions
        """
        try:
            # Parse PGN
            pgn_io = io.StringIO(pgn)
            chess_game = chess.pgn.read_game(pgn_io)

            if not chess_game:
                raise ValidationError("Invalid PGN format")

            # Initialize board
            board = chess_game.board()

            # Extract game data
            moves = []
            positions = []

            # Add initial position
            positions.append({"fen": board.fen(), "move_number": 0, "move": None, "is_white": board.turn})

            # Process moves
            for node in chess_game.mainline():
                move = node.move
                is_white = not board.turn  # The side that just moved

                # Push move to board
                san = board.san(move)
                board.push(move)

                # Store move data
                moves.append({"move_number": len(moves) + 1, "move": move.uci(), "san": san, "is_white": is_white})

                # Store position data
                positions.append(
                    {"fen": board.fen(), "move_number": len(moves), "move": move.uci(), "is_white": board.turn}
                )

            return {"moves": moves, "positions": positions}

        except (chess.pgn.InvalidGameError, ValueError) as e:
            raise ValidationError(f"Invalid PGN format: {str(e)}")
        except Exception as e:
            raise TaskError(f"Failed to extract game data: {str(e)}")

    def _analyze_moves(self, moves: List[Dict[str, Any]], depth: int, progress_callback=None) -> List[Dict[str, Any]]:
        """
        Analyze each move in the game.

        Args:
            moves: List of move data dictionaries
            depth: Stockfish analysis depth
            progress_callback: Optional callback function to report progress

        Returns:
            List of move analysis results
        """
        try:
            results = []
            board = chess.Board()

            total_moves = len(moves)
            progress_base = 30  # Starting progress percentage
            progress_range = 40  # Progress range allocated to move analysis

            for i, move_data in enumerate(moves):
                # Calculate progress percentage for this move
                if progress_callback and total_moves > 0:
                    move_progress = progress_base + (progress_range * i) // total_moves
                    progress_callback(move_progress, f"Analyzing move {i+1}/{total_moves}")
                
                move_number = move_data["move_number"]
                move_uci = move_data["move"]
                is_white = move_data["is_white"]

                # Get the move object
                move = chess.Move.from_uci(move_uci)

                # Analyze position before move
                position_before = self.engine_analyzer.analyze_position(board, depth)

                # Apply move
                board.push(move)

                # Analyze position after move
                position_after = self.engine_analyzer.analyze_position(board, depth)

                # Calculate evaluation change
                eval_before = position_before.get("score", 0)
                eval_after = position_after.get("score", 0)
                eval_change = eval_after - eval_before if is_white else eval_before - eval_after

                # Determine move classification
                classification = self._classify_move(eval_change)

                # Store result
                result = {
                    "move_number": move_number,
                    "move": move_uci,
                    "is_white": is_white,
                    "eval_before": eval_before,
                    "eval_after": eval_after,
                    "eval_change": eval_change,
                    "classification": classification,
                    "position_metrics": position_after.get("position_metrics", {}),
                }

                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Failed to analyze moves: {str(e)}")
            raise TaskError(f"Failed to analyze moves: {str(e)}")

    def _analyze_positions(self, positions: List[Dict[str, Any]], depth: int, progress_callback=None) -> List[Dict[str, Any]]:
        """
        Analyze chess positions.

        Args:
            positions: List of position data
            depth: Stockfish analysis depth
            progress_callback: Optional callback function to report progress

        Returns:
            List of position analysis results
        """
        try:
            results = []
            total_positions = len(positions)
            progress_base = 60   # Starting progress percentage
            progress_range = 20  # Progress range allocated to position analysis

            for i, position_data in enumerate(positions):
                # Calculate progress percentage for this position
                if progress_callback and total_positions > 0:
                    position_progress = progress_base + (progress_range * i) // total_positions
                    progress_callback(position_progress, f"Analyzing position {i+1}/{total_positions}")
                
                fen = position_data["fen"]
                move_number = position_data["move_number"]

                # Create board from FEN
                board = chess.Board(fen)

                # Analyze position
                analysis = self.engine_analyzer.analyze_position(board, depth)

                # Store result
                result = {
                    "move_number": move_number,
                    "fen": fen,
                    "score": analysis.get("score", 0),
                    "best_move": analysis.get("pv", [])[0] if analysis.get("pv") else None,
                    "position_metrics": analysis.get("position_metrics", {}),
                }

                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Failed to analyze positions: {str(e)}")
            raise TaskError(f"Failed to analyze positions: {str(e)}")

    def _classify_move(self, eval_change: float) -> str:
        """
        Classify a move based on evaluation change.

        Args:
            eval_change: The change in evaluation

        Returns:
            Classification string
        """
        if eval_change < -300:
            return "blunder"
        elif eval_change < -100:
            return "mistake"
        elif eval_change < -50:
            return "inaccuracy"
        elif eval_change > 100:
            return "good_move"
        elif eval_change > 300:
            return "excellent_move"
        else:
            return "neutral"

    def analyze_batch(self, game_ids: List[int], depth: int = 20, use_ai: bool = True) -> Dict[int, Dict[str, Any]]:
        """
        Analyze a batch of games.

        Args:
            game_ids: List of game IDs to analyze
            depth: Analysis depth
            use_ai: Whether to use AI feedback

        Returns:
            Dict mapping game IDs to analysis results
        """
        results = {}

        for game_id in game_ids:
            try:
                # Get game
                game = Game.objects.get(id=game_id)

                # Create task in task manager
                task_id = self.task_manager.create_task(
                    game_id=game_id,
                    task_type=self.task_manager.TYPE_ANALYSIS,
                    parameters={"depth": depth, "use_ai": use_ai},
                )

                # Analyze game - pass the task_id
                analysis_result = self.analyze_game(
                    game, 
                    depth, 
                    use_ai, 
                    task_id=task_id
                )

                # Task status already updated in analyze_game

                # Store result
                results[game_id] = analysis_result

            except Game.DoesNotExist:
                logger.error(f"Game {game_id} not found")
                results[game_id] = {"error": f"Game {game_id} not found"}
            except Exception as e:
                logger.error(f"Error analyzing game {game_id}: {str(e)}")
                results[game_id] = {"error": str(e)}

        return results
