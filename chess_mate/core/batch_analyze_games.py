"""
Batch analysis module for chess games.
"""

import logging

from django.utils import timezone

from .tasks import analyze_game_task
from .task_manager import TaskManager

logger = logging.getLogger(__name__)
task_manager = TaskManager()

# Define constants to avoid settings dependency
DEFAULT_ANALYSIS_DEPTH = 20
DEFAULT_USE_AI = True
TASK_START_EXCEPTIONS = (ValueError, TypeError, RuntimeError, OSError)


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
                "timestamp": timezone.now().isoformat(),
            }

        # Convert parameters to appropriate types to avoid type errors
        try:
            game_id = int(game_id)
            depth = int(depth) if depth is not None else DEFAULT_ANALYSIS_DEPTH
            use_ai = bool(use_ai) if use_ai is not None else DEFAULT_USE_AI
        except (ValueError, TypeError) as err:
            logger.error("Parameter type conversion error: %s", err)
            return {
                "status": "error",
                "message": f"Invalid parameter format: {err}",
                "game_id": game_id,
                "timestamp": timezone.now().isoformat(),
            }

        lock = None
        lock_acquired = False
        if task_manager.redis_client is not None:
            lock = task_manager.redis_client.lock(
                f"analysis_lock:game:{game_id}", timeout=15, blocking_timeout=3
            )

        try:
            if lock is not None:
                lock_acquired = lock.acquire(blocking=True)

            # Avoid duplicate task enqueue for the same game.
            active_tasks = task_manager.get_active_tasks_for_game(game_id)
            if active_tasks:
                existing_task_id = active_tasks[0]
                logger.warning("Found existing task %s for game %s", existing_task_id, game_id)
                return {
                    "status": "already_running",
                    "message": "Analysis already in progress",
                    "task_id": existing_task_id,
                    "game_id": game_id,
                    "timestamp": timezone.now().isoformat(),
                }

            # Start a new analysis task
            try:
                # Pass only parameters that the task accepts: game_id, depth, use_ai
                task = analyze_game_task.delay(game_id, depth=depth, use_ai=use_ai)
                task_id = task.id
                task_manager.register_task(
                    task_id=task_id,
                    task_type=TaskManager.TYPE_ANALYSIS,
                    user_id=user_id,
                    game_id=game_id,
                )
            except TASK_START_EXCEPTIONS as task_error:
                logger.error("Failed to create task for game %s: %s", game_id, task_error, exc_info=True)
                return {
                    "status": "error",
                    "message": f"Task creation failed: {task_error}",
                    "game_id": game_id,
                    "timestamp": timezone.now().isoformat(),
                }
        finally:
            if lock is not None and lock_acquired:
                try:
                    lock.release()
                except (RuntimeError, OSError):
                    logger.debug("Failed to release analysis lock", exc_info=True)

        logger.info("Analysis task %s started for game %s", task_id, game_id)

        return {
            "status": "success",
            "message": "Analysis started",
            "task_id": task_id,
            "game_id": game_id,
            "timestamp": timezone.now().isoformat(),
        }
    except TASK_START_EXCEPTIONS as err:
        logger.error("Error starting analysis for game %s: %s", game_id, err, exc_info=True)
        return {
            "status": "error",
            "message": f"Error starting analysis: {err}",
            "game_id": game_id,
            "timestamp": timezone.now().isoformat(),
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
        "timestamp": timezone.now().isoformat(),
    }
