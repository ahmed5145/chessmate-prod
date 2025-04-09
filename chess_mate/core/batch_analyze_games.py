"""
Batch analysis module for chess games.
"""

import logging
from datetime import datetime
from django.conf import settings
from django.utils import timezone

from .tasks import analyze_game_task

logger = logging.getLogger(__name__)

# Define constants to avoid settings dependency
DEFAULT_ANALYSIS_DEPTH = 20
DEFAULT_USE_AI = True

def analyze_game_safely(game_id, user_id=None, depth=DEFAULT_ANALYSIS_DEPTH, use_ai=DEFAULT_USE_AI):
    """
    A safer version of game analysis that doesn't rely on existing GameAnalysis table.
    
    Args:
        game_id: ID of the game to analyze
        user_id: ID of the user requesting the analysis
        depth: Analysis depth (default: 20)
        use_ai: Whether to use AI for analysis (default: True)
        
    Returns:
        Dictionary with task info
    """
    try:
        # Validate inputs
        if not game_id:
            logger.error("No game_id provided")
            return {
                "status": "error",
                "message": "Game ID is required",
                "game_id": None,
                "timestamp": timezone.now().isoformat()
            }
        
        # Convert parameters to appropriate types to avoid type errors
        try:
            game_id = int(game_id)
            depth = int(depth) if depth is not None else DEFAULT_ANALYSIS_DEPTH
            use_ai = bool(use_ai) if use_ai is not None else DEFAULT_USE_AI
        except (ValueError, TypeError) as e:
            logger.error(f"Parameter type conversion error: {str(e)}")
            return {
                "status": "error",
                "message": f"Invalid parameter format: {str(e)}",
                "game_id": game_id,
                "timestamp": timezone.now().isoformat()
            }
            
        # Start a new analysis task
        try:
            # Pass only parameters that the task accepts: game_id, depth, use_ai
            task = analyze_game_task.delay(game_id, depth=depth, use_ai=use_ai)
            task_id = task.id
        except Exception as task_error:
            logger.error(f"Failed to create task for game {game_id}: {str(task_error)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Task creation failed: {str(task_error)}",
                "game_id": game_id,
                "timestamp": timezone.now().isoformat()
            }
        
        logger.info(f"Analysis task {task_id} started for game {game_id}")
        
        return {
            "status": "success",
            "message": "Analysis started",
            "task_id": task_id,
            "game_id": game_id,
            "timestamp": timezone.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error starting analysis for game {game_id}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Error starting analysis: {str(e)}",
            "game_id": game_id,
            "timestamp": timezone.now().isoformat()
        }

def batch_analyze_games_safely(game_ids, user_id=None, depth=DEFAULT_ANALYSIS_DEPTH, use_ai=DEFAULT_USE_AI):
    """
    Safely analyze multiple games without relying on GameAnalysis table.
    
    Args:
        game_ids: List of game IDs to analyze
        user_id: ID of the user requesting the analysis
        depth: Analysis depth (default: 20)
        use_ai: Whether to use AI for analysis (default: True)
        
    Returns:
        Dictionary with task info for each game
    """
    results = {}
    
    for game_id in game_ids:
        results[game_id] = analyze_game_safely(game_id, user_id, depth, use_ai)
    
    return {
        "status": "success",
        "message": f"Started analysis for {len(game_ids)} games",
        "results": results,
        "timestamp": timezone.now().isoformat()
    } 