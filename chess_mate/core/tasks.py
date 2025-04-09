"""
Celery tasks for game analysis.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import redis
from celery import Task, shared_task
from celery.utils.log import get_task_logger
from celery.exceptions import MaxRetriesExceededError
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from openai import OpenAI, OpenAIError
import traceback

from .ai_feedback import AIFeedbackGenerator
from .cache import cache_delete, cache_get, cache_set, cacheable
from .error_handling import (
    ExternalServiceError,
    ResourceNotFoundError,
    TaskError,
    ValidationError,
)
from .game_analyzer import GameAnalyzer, AnalysisError
from .analysis.metrics_calculator import MetricsError
from .models import Game, GameAnalysis, Profile
from .task_manager import (
    TaskManager, 
    TASK_STATUS_PENDING,
    TASK_STATUS_STARTED,
    TASK_STATUS_SUCCESS,
    TASK_STATUS_FAILURE,
    TASK_STATUS_REVOKED,
    TASK_STATUS_RETRY
)

logger = get_task_logger(__name__)


class BaseAnalysisTask(Task):
    """Base class for analysis tasks."""

    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Task {task_id} failed: {str(exc)}", exc_info=einfo)
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        logger.info(f"Task {task_id} completed successfully")
        super().on_success(retval, task_id, args, kwargs)

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Cleanup after task completion."""
        logger.info(f"Task {task_id} finished with status: {status}")
        super().after_return(status, retval, task_id, args, kwargs, einfo)


@shared_task(bind=True)
def analyze_game_task(self, game_id, user_id=None, depth=20, use_ai=True):
    """
    Task to analyze a chess game and generate insights.

    Args:
        self: Task instance
        game_id: ID of the game to analyze
        user_id: ID of the user who requested the analysis (unused)
        depth: Depth for the engine analysis
        use_ai: Whether to use AI to enhance the analysis

    Returns:
        Dict containing analysis results and status
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Analyze game task started for game {game_id}")

    # Initialize task manager
    task_manager = TaskManager()
    
    # First, check if there's already an active task for this game
    existing_tasks = task_manager.get_active_tasks_for_game(game_id)
    if existing_tasks and existing_tasks[0] != task_id:
        logger.warning(f"[{task_id}] Found existing task {existing_tasks[0]} for game {game_id}")
        # Return existing task ID
        return {
            "status": "already_running",
            "message": "Analysis already in progress",
            "task_id": existing_tasks[0],
            "game_id": game_id
        }

    # Get the game from the database
    logger.info(f"[{task_id}] Retrieving game {game_id}")
    try:
        game = Game.objects.get(id=game_id)
    except Game.DoesNotExist:
        logger.error(f"[{task_id}] Game {game_id} not found")
        return {
            "status": "error",
            "message": f"Game {game_id} not found",
            "error": f"Game {game_id} not found"
        }

    # Create a task entry
    logger.info(f"[{task_id}] Creating task entry for game {game_id}")
    task_manager.create_task(game_id=game_id, task_type=task_manager.TYPE_ANALYSIS)

    # Initialize progress tracker
    def update_progress(progress, message=None):
        """Update task progress."""
        logger.debug(f"[{task_id}] Progress update: {progress}%")
        task_manager.update_task_status(
            task_id=task_id,
            status="PROCESSING",
            progress=progress,
            message=message
        )
        # Also update the game's analysis status
        try:
            game.analysis_status = f"in_progress:{progress}"
            game.save(update_fields=["analysis_status"])
        except Exception as e:
            logger.error(f"[{task_id}] Error updating game status: {str(e)}")

    try:
        # Create game analyzer
        game_analyzer = GameAnalyzer()
        logger.info(f"[{task_id}] Starting analysis for game {game_id} (depth={depth}, use_ai={use_ai})")
        
        # Update progress to indicate we're starting
        update_progress(5, "Starting analysis...")
        
        # Run the analysis
        logger.info(f"[{task_id}] Running analysis with progress callback")
        analysis_result = game_analyzer.analyze_game(
            game=game, 
            depth=depth, 
            use_ai=use_ai, 
            progress_callback=update_progress,
            task_id=task_id
        )
        
        # Ensure we have valid results
        if not analysis_result or not hasattr(analysis_result, 'id'):
            logger.error(f"[{task_id}] Analysis failed: No valid results returned")
            # Update task status to failure
            task_manager.update_task_status(
                task_id=task_id,
                status="FAILURE",
                progress=0,
                message="Analysis failed: No valid results returned",
                error="No valid results returned"
            )
            # Update game status
            game.analysis_status = "failed"
            game.save(update_fields=["analysis_status"])
            return {
                "status": "error",
                "message": "Analysis failed: No valid results returned",
                "error": "No valid results returned",
                "game_id": game_id
            }
        
        # Clear cached data for this game
        try:
            cache_delete(f"game_{game.id}")
            cache_delete(f"analysis_{game.id}")
            logger.info(f"[{task_id}] Cache cleared for game {game.id}")
        except Exception as cache_error:
            logger.warning(f"[{task_id}] Cache invalidation error: {str(cache_error)}")
        
        # Update task status to success
        task_manager.update_task_status(
            task_id=task_id,
            status="SUCCESS",
            progress=100,
            message="Analysis completed successfully",
            result={"analysis_id": analysis_result.id}
        )
        
        # Update game status
        game.analysis_status = "completed"
        game.save(update_fields=["analysis_status"])
        
        # Return success response
        logger.info(f"[{task_id}] Analysis for game {game_id} completed successfully")
        return {
            "status": "success",
            "message": "Analysis completed successfully",
            "analysis_id": analysis_result.id,
            "game_id": game_id
        }
        
    except Exception as e:
        logger.exception(f"[{task_id}] Error analyzing game {game_id}: {str(e)}")
        
        error_message = str(e)
        error_type = type(e).__name__
        
        # Update task status to failure
        task_manager.update_task_status(
            task_id=task_id,
            status="FAILURE",
            progress=0,
            message=f"Analysis failed: {error_type}",
            error=error_message
        )
        
        # Update game status
        game.analysis_status = "failed"
        game.save(update_fields=["analysis_status"])
        
        # Return error response
        return {
            "status": "error",
            "message": f"Analysis failed: {error_type}",
            "error": error_message,
            "game_id": game_id
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=60, autoretry_for=(Exception,), retry_backoff=True)
def batch_analyze_games_task(self, game_ids: List[int], depth: int = 20, use_ai: bool = True) -> Dict[str, Any]:
    """Analyze multiple games in batch."""
    task_manager = TaskManager()
    game_analyzer = GameAnalyzer()

    try:
        # Validate batch size
        if len(game_ids) > settings.MAX_BATCH_SIZE:
            raise ValidationError(f"Batch size exceeds limit of {settings.MAX_BATCH_SIZE}")

        # Create batch task entry
        batch_id = task_manager.create_task(
            task_type=TaskManager.TYPE_BATCH_ANALYSIS,
            parameters={"game_ids": game_ids, "depth": depth, "use_ai": use_ai},
        )

        # Use the analyze_batch method from GameAnalyzer
        results = game_analyzer.analyze_batch(game_ids, depth, use_ai)

        # Update batch task status
        task_manager.update_task_status(task_id=batch_id, status=TaskManager.STATUS_COMPLETED, result=results)

        return results

    except Exception as e:
        # Update task status if task was created
        try:
            if "batch_id" in locals():
                task_manager.update_task_status(task_id=batch_id, status=TaskManager.STATUS_FAILED, error=str(e))
        except Exception as update_err:
            logger.error(f"Failed to update batch task status: {str(update_err)}")

        raise TaskError(f"Batch analysis failed: {str(e)}")


@shared_task(bind=True, max_retries=3, default_retry_delay=60, autoretry_for=(Exception,), retry_backoff=True)
def cleanup_expired_tasks(self) -> Dict[str, Any]:
    """Clean up expired tasks."""
    task_manager = TaskManager()

    try:
        # Get expired tasks
        expired_tasks = task_manager.get_expired_tasks()

        # Clean up each task
        for task_id in expired_tasks:
            task_manager.cleanup_task(task_id)

        return {"status": "success", "cleaned_tasks": len(expired_tasks)}

    except Exception as e:
        raise TaskError(f"Task cleanup failed: {str(e)}")


@shared_task(base=BaseAnalysisTask)
def cleanup_analysis_cache() -> None:
    """Clean up analysis cache."""
    try:
        cache.clear()
        logger.info("Successfully cleaned up analysis cache")
    except Exception as e:
        logger.error(f"Error cleaning up analysis cache: {str(e)}")


@shared_task(base=BaseAnalysisTask)
def update_user_stats_task(user_id: int) -> None:
    """Update user statistics."""
    try:
        profile = Profile.objects.get(user_id=user_id)
        profile.update_ratings_for_existing_games()
    except Profile.DoesNotExist:
        logger.error(f"Profile not found for user {user_id}")
    except Exception as e:
        logger.error(f"Error updating user stats: {str(e)}")


@shared_task(base=BaseAnalysisTask)
def update_ratings_for_linked_account(profile_id: int) -> None:
    """Update ratings for linked chess platform account."""
    try:
        profile = Profile.objects.get(id=profile_id)
        profile.update_ratings_for_existing_games()
        logger.info(f"Successfully updated ratings for profile {profile_id}")
    except Profile.DoesNotExist:
        logger.error(f"Profile not found: {profile_id}")
    except Exception as e:
        logger.error(f"Error updating ratings: {str(e)}")


@shared_task(name="chess_mate.core.tasks.health_check_task")
def health_check_task() -> str:
    """
    Simple task to test if Celery is working.

    This task can be used by health checks to verify that Celery
    workers are operational and can process tasks.

    Returns:
        "ok" string to indicate success
    """
    logger.debug("Health check task executed")
    return "ok"


@shared_task(
    name="chess_mate.core.tasks.batch_analyze_games_task",
    bind=True,
    ignore_result=False,
    max_retries=1,
    soft_time_limit=3600,  # 1 hour time limit
    time_limit=3900,  # 1 hour 5 minutes hard limit
)
def batch_analyze_games_task(self, game_ids: List[int], depth: int = 20, use_ai: bool = True) -> Dict[str, Any]:
    """
    Analyze multiple games in a batch.

    Args:
        self: Task instance (provided by bind=True)
        game_ids: List of game IDs to analyze
        depth: Depth of analysis
        use_ai: Whether to use AI for feedback

    Returns:
        Dictionary with batch analysis results
    """
    logger.info(f"Starting batch analysis for {len(game_ids)} games")

    results = {"total": len(game_ids), "completed": 0, "failed": 0, "skipped": 0, "results": {}}

    # Process each game
    for i, game_id in enumerate(game_ids):
        try:
            # Update progress
            progress = int((i / len(game_ids)) * 100)
            self.update_state(
                state="STARTED",
                meta={
                    "game_ids": game_ids,
                    "current_game": game_id,
                    "progress": progress,
                    "completed": results["completed"],
                    "failed": results["failed"],
                    "skipped": results["skipped"],
                    "message": f"Analyzing game {i+1} of {len(game_ids)}",
                },
            )

            # Launch subtask for each game
            subtask = analyze_game_task.delay(game_id, depth, use_ai)

            # Wait for result (in a real implementation, this would be more asynchronous)
            subtask_result = subtask.get(timeout=1800)  # 30 minute timeout per game

            # Store result
            results["results"][game_id] = subtask_result

            # Update counters
            if subtask_result.get("status") == "success":
                results["completed"] += 1
            else:
                results["failed"] += 1

        except Exception as e:
            logger.error(f"Error processing game {game_id} in batch: {str(e)}")
            results["failed"] += 1
            results["results"][game_id] = {
                "status": "error",
                "message": f"Failed to process: {str(e)}",
            }

    # Final summary
    results["status"] = "completed"
    results["message"] = (
        f"Batch analysis completed: {results['completed']} succeeded, {results['failed']} failed, {results['skipped']} skipped"
    )

    return results


@shared_task(name="chess_mate.core.tasks.cleanup_task", ignore_result=True)
def cleanup_task() -> None:
    """
    Perform routine cleanup operations.

    This task is designed to be scheduled periodically to clean up
    temporary files, expired sessions, and other maintenance tasks.
    """
    from django.core.management import call_command

    logger.info("Starting cleanup task")

    try:
        # Clean up expired sessions
        call_command("clearsessions")
        logger.info("Expired sessions cleaned up")

        # Clean up expired task information
        from .task_manager import TaskManager

        task_manager = TaskManager()
        cleaned_count = task_manager.cleanup_expired_tasks(expiry_hours=24)
        logger.info(f"Cleaned up {cleaned_count} expired tasks")

        # Clean up temp files
        import os
        import tempfile
        from datetime import datetime, timedelta

        temp_dir = getattr(settings, "TEMP_DIR", tempfile.gettempdir())
        threshold = datetime.now() - timedelta(days=1)

        count = 0
        for filename in os.listdir(temp_dir):
            if filename.startswith("chessmate-"):
                file_path = os.path.join(temp_dir, filename)
                if os.path.isfile(file_path):
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_time < threshold:
                        os.remove(file_path)
                        count += 1

        logger.info(f"Cleaned up {count} temporary files")

    except Exception as e:
        logger.error(f"Error during cleanup task: {str(e)}")


@shared_task(name="chess_mate.core.tasks.monitor_system_task", ignore_result=True)
def monitor_system_task() -> None:
    """
    Monitor system health and performance.

    This task is designed to be scheduled periodically to collect
    system metrics and alert on issues.
    """
    from .health_checks import run_all_checks

    logger.info("Starting system monitoring task")

    try:
        # Run health checks
        health_results = run_all_checks()

        # Log overall status
        status = health_results.get("status", "unknown")
        logger.info(f"System health status: {status}")

        # Check for critical issues
        checks = health_results.get("checks", {})
        critical_issues = []

        for component, check in checks.items():
            if check.get("status") == "critical":
                critical_issues.append(f"{component}: {check.get('message', 'Unknown issue')}")

        if critical_issues:
            logger.error(f"Critical system issues detected: {', '.join(critical_issues)}")

            # Optional: Send alerts via email, Slack, etc.
            # This would be implemented based on your alerting system
            if getattr(settings, "ENABLE_SYSTEM_ALERTS", False):
                from django.core.mail import mail_admins

                mail_admins(
                    subject=f"[ChessMate] Critical system issues detected",
                    message=f"The following critical issues were detected:\n\n" + "\n".join(critical_issues),
                )

    except Exception as e:
        logger.error(f"Error during system monitoring task: {str(e)}")
