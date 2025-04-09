"""
Task management for handling background tasks and tracking their status.

This module provides a TaskManager class to handle task registration, status tracking,
and retrieval for background tasks executed via Celery.
"""

import json
import logging
import time
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, cast

from celery.result import AsyncResult  # type: ignore
from django.conf import settings
from redis.exceptions import RedisError  # type: ignore
from redis import Redis

from .cache import CACHE_BACKEND_REDIS, cache_delete, cache_get, cache_set
from .redis_connection import get_redis_connection

logger = logging.getLogger(__name__)

# Task status constants
TASK_STATUS_PENDING = "PENDING"
TASK_STATUS_STARTED = "STARTED"
TASK_STATUS_SUCCESS = "SUCCESS"
TASK_STATUS_FAILURE = "FAILURE"
TASK_STATUS_REVOKED = "REVOKED"
TASK_STATUS_RETRY = "RETRY"

# Task type constants
TASK_TYPE_ANALYSIS = "analysis"
TASK_TYPE_BATCH_ANALYSIS = "batch_analysis"
TASK_TYPE_IMPORT = "import"
TASK_TYPE_EXPORT = "export"


class TaskManager:
    """
    Manages task tracking, status updates, and retrieval.

    This class provides a centralized way to manage Celery tasks and their status,
    with Redis-based persistence for task information to survive application restarts.
    """

    # Task types
    TYPE_ANALYSIS = "analysis"
    TYPE_BATCH_ANALYSIS = "batch_analysis"
    TYPE_IMPORT = "import"
    TYPE_EXPORT = "export"

    # Cache key prefixes
    TASK_KEY_PREFIX = "task:"
    GAME_TASK_KEY_PREFIX = "game_task:"

    # Default task timeout (1 hour)
    DEFAULT_TASK_TIMEOUT = 3600

    def __init__(self, redis_client=None):
        """Initialize the task manager with default configuration."""
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.game_tasks: Dict[str, str] = {}
        self.task_timeout = getattr(settings, "TASK_TIMEOUT", self.DEFAULT_TASK_TIMEOUT)
        
        # Initialize redis client
        if redis_client is not None:
            self.redis_client = redis_client
        else:
            self.redis_client = get_redis_connection()
        
        if self.redis_client is None:
            logger.warning("Redis connection not available, using in-memory storage only")

    def register_task(
        self, task_id: str, task_type: str, user_id: Optional[int] = None, game_id: Optional[int] = None
    ) -> None:
        """
        Register a new task for tracking.

        Args:
            task_id: The ID of the Celery task
            task_type: Type of task (analysis, import, etc.)
            user_id: ID of the user who initiated the task (optional)
            game_id: ID of the game associated with the task (optional)
        """
        task_info = {
            "id": task_id,
            "type": task_type,
            "status": TASK_STATUS_PENDING,
            "progress": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "user_id": user_id,
            "game_id": game_id,
            "message": "Task pending",
        }

        # Store in memory
        self.tasks[task_id] = task_info

        # Store in Redis if available
        if self.redis_client is not None:
            try:
                # Store task info
                task_key = f"{self.TASK_KEY_PREFIX}{task_id}"
                self.redis_client.setex(
                    task_key,
                    self.task_timeout,
                    json.dumps(task_info)
                )

                # If game_id is provided, store a mapping from game to task
                if game_id:
                    game_task_key = f"{self.GAME_TASK_KEY_PREFIX}{game_id}"
                    self.redis_client.setex(
                        game_task_key,
                        self.task_timeout,
                        task_id
                    )
                    self.game_tasks[str(game_id)] = task_id
            except Exception as e:
                logger.error(f"Error registering task {task_id} in Redis: {str(e)}")
        else:
            logger.warning(f"Redis not available, task {task_id} stored in memory only")

    def register_batch_task(self, task_id: str, game_ids: List[int], user_id: Optional[int] = None) -> None:
        """
        Register a batch task that processes multiple games.

        Args:
            task_id: The ID of the Celery task
            game_ids: List of game IDs associated with the task
            user_id: ID of the user who initiated the task
        """
        task_info = {
            "id": task_id,
            "type": self.TYPE_BATCH_ANALYSIS,
            "status": TASK_STATUS_PENDING,
            "progress": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "user_id": user_id,
            "game_ids": game_ids,
            "games_count": len(game_ids),
            "completed_games": 0,
            "message": "Batch analysis pending",
        }

        # Store in memory
        self.tasks[task_id] = task_info

        # Store in Redis if available
        if self.redis_client is not None:
            try:
                # Store task info
                task_key = f"{self.TASK_KEY_PREFIX}{task_id}"
                self.redis_client.setex(
                    task_key,
                    self.task_timeout,
                    json.dumps(task_info)
                )

                # Store mappings from each game to the task
                for game_id in game_ids:
                    game_task_key = f"{self.GAME_TASK_KEY_PREFIX}{game_id}"
                    self.redis_client.setex(
                        game_task_key,
                        self.task_timeout,
                        task_id
                    )
                    self.game_tasks[str(game_id)] = task_id
            except Exception as e:
                logger.error(f"Error registering batch task {task_id} in Redis: {str(e)}")
        else:
            logger.warning(f"Redis not available, batch task {task_id} stored in memory only")

    def update_task_status(
        self,
        task_id: str,
        status: str,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Update the status of a task.

        Args:
            task_id: The ID of the Celery task
            status: New status of the task
            progress: Current progress percentage (0-100)
            message: Status message
            result: Optional result data
            error: Error message if any
        """
        # Get existing task info
        task_info = self.get_task_info(task_id)
        if not task_info:
            logger.warning(f"Attempted to update unknown task: {task_id}, creating new task record")
            task_info = {"id": task_id}

        # Update task info
        if status:
            task_info["status"] = status
            # If task is complete, ensure progress is 100%
            if status == TASK_STATUS_SUCCESS:
                progress = 100
                if not message:
                    message = "Task completed successfully"
                
        if progress is not None:
            task_info["progress"] = progress
        if message:
            task_info["message"] = message
        if result is not None:
            task_info["result"] = result
        if error:
            task_info["error"] = error

        task_info["updated_at"] = datetime.now().isoformat()

        # Store in memory
        self.tasks[task_id] = task_info

        # Store in Redis with retry for resilience
        if self.redis_client is not None:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    task_key = f"{self.TASK_KEY_PREFIX}{task_id}"
                    serialized_task = json.dumps(task_info)
                    
                    # Ensure timeout is an integer and positive
                    timeout = max(1, int(self.task_timeout))
                    
                    # Set the key with TTL
                    result = self.redis_client.setex(
                        task_key,
                        timeout,
                        serialized_task
                    )
                    
                    if not result:
                        logger.warning(f"Redis setex returned False for task {task_id} (attempt {attempt+1}/{max_retries})")
                        if attempt < max_retries - 1:
                            time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                            continue
                    
                    # Verify the data was stored correctly
                    try:
                        stored_data = self.redis_client.get(task_key)
                        if not stored_data:
                            logger.warning(f"Verification check failed - Task data not found in Redis after write for {task_id} (attempt {attempt+1}/{max_retries})")
                            if attempt < max_retries - 1:
                                time.sleep(0.1 * (attempt + 1))
                                continue
                        else:
                            # Data successfully stored and verified
                            # If this is a task completion (SUCCESS or FAILURE status),
                            # set a longer timeout to ensure it stays in Redis longer
                            if status in [TASK_STATUS_SUCCESS, TASK_STATUS_FAILURE, TASK_STATUS_REVOKED]:
                                try:
                                    # Set a longer TTL for completed tasks (3x normal timeout)
                                    self.redis_client.expire(task_key, timeout * 3)
                                    
                                    # Also update the game->task mapping with the same extended TTL
                                    game_id = task_info.get("game_id")
                                    if game_id:
                                        game_task_key = f"{self.GAME_TASK_KEY_PREFIX}{game_id}"
                                        self.redis_client.setex(
                                            game_task_key,
                                            timeout * 3,
                                            task_id
                                        )
                                except Exception as e:
                                    logger.error(f"Error extending TTL for completed task {task_id}: {str(e)}")
                            
                            # Success, break the retry loop
                            logger.debug(f"Task {task_id} status updated to {status} (progress: {progress}%)")
                            break
                    except Exception as e:
                        logger.error(f"Error verifying Redis data for task {task_id}: {str(e)}")
                        if attempt < max_retries - 1:
                            time.sleep(0.1 * (attempt + 1))
                            continue
                        # On last attempt, continue without verification
                except RedisError as e:
                    logger.warning(f"Redis error updating task {task_id} (attempt {attempt+1}/{max_retries}): {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(0.1 * (attempt + 1))
                        continue
                except Exception as e:
                    logger.error(f"Unexpected error updating task {task_id} in Redis: {str(e)}")
                    break  # Exit loop on other errors
        else:
            logger.warning(f"Redis not available, task {task_id} status updated in memory only")

        # Special handling for task completion
        if status in [TASK_STATUS_SUCCESS, TASK_STATUS_FAILURE, TASK_STATUS_REVOKED]:
            logger.info(f"Task {task_id} completed with status {status} and progress {progress}%")
            # Log extra details for completed tasks
            if status == TASK_STATUS_SUCCESS:
                logger.info(f"Task {task_id} completed successfully: {message}")
            elif status == TASK_STATUS_FAILURE:
                logger.error(f"Task {task_id} failed: {error}")
            elif status == TASK_STATUS_REVOKED:
                logger.warning(f"Task {task_id} was revoked: {message}")

    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a task.

        Args:
            task_id: The ID of the Celery task

        Returns:
            Task information dictionary or None if not found
        """
        try:
            # First check in-memory cache
            if task_id in self.tasks:
                return self.tasks[task_id]

            # Then check Redis
            if self.redis_client is not None:
                try:
                    task_key = f"{self.TASK_KEY_PREFIX}{task_id}"
                    data = self.redis_client.get(task_key)
                    if data:
                        # Ensure data is bytes before decoding
                        if isinstance(data, bytes):
                            data_str = data.decode('utf-8')
                        else:
                            data_str = str(data)
                        
                        try:
                            task_info = json.loads(data_str)
                            # Update in-memory cache
                            self.tasks[task_id] = task_info
                            return task_info
                        except json.JSONDecodeError as e:
                            logger.error(f"Error decoding task info for {task_id}: {str(e)}")
                            return None
                except Exception as e:
                    logger.error(f"Redis error getting task info for {task_id}: {str(e)}")
                    # Continue with Celery check as fallback

            # If not found, check Celery task status as a fallback
            try:
                celery_task = AsyncResult(task_id)
                if celery_task.state:
                    # Create basic task info from Celery
                    task_info = {
                        "id": task_id,
                        "status": celery_task.state,
                        "result": celery_task.result,
                        "updated_at": datetime.now().isoformat(),
                    }

                    # Update in-memory cache
                    self.tasks[task_id] = task_info
                    
                    # Try to update Redis if available
                    if self.redis_client is not None:
                        try:
                            task_key = f"{self.TASK_KEY_PREFIX}{task_id}"
                            self.redis_client.setex(
                                task_key,
                                self.task_timeout,
                                json.dumps(task_info)
                            )
                        except Exception as e:
                            logger.error(f"Redis error updating task info for {task_id}: {str(e)}")

                    return task_info
            except Exception as e:
                logger.error(f"Error checking Celery task status for {task_id}: {str(e)}")
                return None

        except Exception as e:
            logger.error(f"Error getting task info for {task_id}: {str(e)}")
            return None

    def get_task_for_game(self, game_id: Union[int, str]) -> Optional[str]:
        """
        Get the task ID associated with a game.

        Args:
            game_id: ID of the game

        Returns:
            Task ID or None if no task is found
        """
        try:
            # Convert to string for consistent lookup
            game_id_str = str(game_id)
            
            # First check in-memory cache
            if game_id_str in self.game_tasks:
                task_id = self.game_tasks[game_id_str]
                logger.debug(f"Found task ID {task_id} for game {game_id} in memory cache")
                return task_id
            
            # Try in Redis
            if self.redis_client is not None:
                # Check both formats of the key for compatibility with older versions
                for game_key in [
                    f"{self.GAME_TASK_KEY_PREFIX}{game_id_str}",
                    f"game_task:{game_id_str}",
                    f"game:{game_id_str}:task"
                ]:
                    try:
                        task_id = self.redis_client.get(game_key)
                        if task_id:
                            # Convert bytes to string if needed
                            if isinstance(task_id, bytes):
                                task_id = task_id.decode('utf-8')
                            
                            # Cache in memory for future lookups
                            self.game_tasks[game_id_str] = task_id
                            logger.debug(f"Found task ID {task_id} for game {game_id} in Redis using key {game_key}")
                            return task_id
                    except Exception as e:
                        logger.error(f"Redis error getting task ID for game {game_id} with key {game_key}: {str(e)}")
            
            # Additional lookup by scanning tasks for this game_id
            for task_id, task_info in self.tasks.items():
                if task_info.get("game_id") == game_id or str(task_info.get("game_id", "")) == game_id_str:
                    logger.debug(f"Found task ID {task_id} for game {game_id} by scanning tasks")
                    
                    # Cache the mapping for future lookups
                    self.game_tasks[game_id_str] = task_id
                    
                    # Also store in Redis if available
                    if self.redis_client is not None:
                        try:
                            game_task_key = f"{self.GAME_TASK_KEY_PREFIX}{game_id_str}"
                            self.redis_client.setex(
                                game_task_key,
                                self.task_timeout,
                                task_id
                            )
                        except Exception as e:
                            logger.error(f"Redis error storing task ID for game {game_id}: {str(e)}")
                    
                    return task_id
            
            # If we have Redis, scan through all task keys as a last resort
            if self.redis_client is not None:
                try:
                    # This is expensive, but a last resort
                    for key in self.redis_client.scan_iter(f"{self.TASK_KEY_PREFIX}*"):
                        try:
                            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                            task_data = self.redis_client.get(key)
                            if task_data:
                                try:
                                    task_info = json.loads(task_data.decode('utf-8') if isinstance(task_data, bytes) else task_data)
                                    if task_info.get("game_id") == game_id or str(task_info.get("game_id", "")) == game_id_str:
                                        task_id = task_info.get("id") or key_str.replace(self.TASK_KEY_PREFIX, "")
                                        
                                        # Cache for future lookups
                                        self.game_tasks[game_id_str] = task_id
                                        
                                        # Store mapping in Redis
                                        game_task_key = f"{self.GAME_TASK_KEY_PREFIX}{game_id_str}"
                                        self.redis_client.setex(
                                            game_task_key,
                                            self.task_timeout,
                                            task_id
                                        )
                                        
                                        logger.debug(f"Found task ID {task_id} for game {game_id} by scanning Redis tasks")
                                        return task_id
                                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                                    logger.error(f"Error decoding task data from Redis for key {key_str}: {str(e)}")
                                    # Skip this key and continue with the next one
                        except Exception as e:
                            logger.error(f"Error processing Redis key {key}: {str(e)}")
                            # Skip this key and continue with the next one
                except Exception as e:
                    logger.error(f"Error scanning Redis for tasks: {str(e)}")
            
            logger.debug(f"No task found for game {game_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error in get_task_for_game for game {game_id}: {str(e)}")
            return None

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.

        Args:
            task_id: The ID of the Celery task

        Returns:
            True if task was cancelled, False otherwise
        """
        try:
            # Try to revoke the Celery task
            celery_task = AsyncResult(task_id)
            celery_task.revoke(terminate=True)

            # Update task status
            self.update_task_status(
                task_id=task_id,
                status=TASK_STATUS_REVOKED,
                message="Task cancelled",
            )

            return True
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {str(e)}")
            return False

    def cleanup_expired_tasks(self, expiry_hours: int = 24) -> int:
        """
        Clean up expired tasks from the cache.

        Args:
            expiry_hours: Age in hours after which tasks are considered expired

        Returns:
            Number of tasks cleaned up
        """
        cleaned_count = 0
        expiry_time = datetime.now() - timedelta(hours=expiry_hours)

        for task_id, task_info in list(self.tasks.items()):
            try:
                updated_at = datetime.fromisoformat(task_info.get("updated_at", "2000-01-01"))
                if updated_at < expiry_time:
                    # Remove from memory
                    del self.tasks[task_id]

                    # Remove from Redis if available
                    if self.redis_client is not None:
                        try:
                            task_key = f"{self.TASK_KEY_PREFIX}{task_id}"
                            self.redis_client.delete(task_key)
                        except Exception as e:
                            logger.error(f"Error cleaning up task {task_id} from Redis: {str(e)}")

                    # Remove game mappings
                    game_id = task_info.get("game_id")
                    if game_id:
                        game_key = f"{self.GAME_TASK_KEY_PREFIX}{game_id}"
                        if self.redis_client is not None:
                            self.redis_client.delete(game_key)
                        if str(game_id) in self.game_tasks:
                            del self.game_tasks[str(game_id)]

                    cleaned_count += 1
            except Exception as e:
                logger.error(f"Error cleaning up task {task_id}: {str(e)}")

        return cleaned_count

    def get_task_status(self, game_id: Union[int, str]) -> Optional[Dict[str, Any]]:
        """
        Get the status of a task associated with a game.

        Args:
            game_id: The ID of the game

        Returns:
            Task status information or None if no task is found
        """
        try:
            # Get task ID associated with the game
            task_id = self.get_task_for_game(game_id)
            if not task_id:
                logger.debug(f"No task ID found for game {game_id}")
                return {"status": "not_found", "message": "No analysis task found"}

            logger.debug(f"Retrieved task ID {task_id} for game {game_id}")

            # Get task info from memory cache first
            task_info = None
            if task_id in self.tasks:
                task_info = self.tasks[task_id]
                if task_info is not None:
                    logger.debug(f"Found task {task_id} in memory cache: {task_info.get('status', 'UNKNOWN')}, {task_info.get('progress', 0)}%")
                
            # If not in memory cache, try Redis
            if task_info is None and self.redis_client is not None:
                try:
                    task_key = f"{self.TASK_KEY_PREFIX}{task_id}"
                    data = self.redis_client.get(task_key)
                    if data:
                        try:
                            if isinstance(data, bytes):
                                data_str = data.decode('utf-8')
                            else:
                                data_str = str(data)
                            task_info = json.loads(data_str)
                            # Update in-memory cache
                            self.tasks[task_id] = task_info
                            if task_info is not None:
                                logger.debug(f"Found task {task_id} in Redis: {task_info.get('status', 'UNKNOWN')}, {task_info.get('progress', 0)}%")
                        except json.JSONDecodeError as e:
                            logger.error(f"Error decoding task info for {task_id}: {str(e)}")
                except Exception as e:
                    logger.error(f"Redis error getting task info for {task_id}: {str(e)}")

            # If still not found, check with Celery directly as last resort
            if task_info is None:
                try:
                    celery_task = AsyncResult(task_id)
                    task_state = celery_task.state
                    logger.debug(f"Celery task {task_id} state from AsyncResult: {task_state}")
                    
                    if task_state:
                        # Create basic task info from Celery
                        task_info = {
                            "id": task_id,
                            "status": task_state,
                            "progress": 100 if task_state == TASK_STATUS_SUCCESS else 0,
                            "message": f"Task status from Celery: {task_state}",
                            "updated_at": datetime.now().isoformat(),
                        }
                        
                        # Update in-memory cache
                        self.tasks[task_id] = task_info
                        
                        # Try to update Redis
                        if self.redis_client is not None:
                            try:
                                task_key = f"{self.TASK_KEY_PREFIX}{task_id}"
                                self.redis_client.setex(
                                    task_key,
                                    self.task_timeout,
                                    json.dumps(task_info)
                                )
                                logger.debug(f"Updated Redis with Celery task status for {task_id}")
                            except Exception as e:
                                logger.error(f"Redis error updating task info for {task_id}: {str(e)}")
                except Exception as e:
                    logger.error(f"Error checking Celery task state for {task_id}: {str(e)}")

            # If task info is now available, check if it's stale
            if task_info is not None:
                # Check if task status is stale (task is STARTED but hasn't updated in more than 30 seconds)
                if task_info.get("status") == TASK_STATUS_STARTED:
                    try:
                        updated_at = datetime.fromisoformat(task_info.get("updated_at", "2000-01-01"))
                        staleness = datetime.now() - updated_at
                        logger.debug(f"Task {task_id} staleness: {staleness.total_seconds()} seconds")
                        
                        if staleness > timedelta(seconds=30):
                            # Task might be stale - check with Celery directly
                            try:
                                celery_task = AsyncResult(task_id)
                                logger.debug(f"Checking potentially stale task {task_id} with Celery, state: {celery_task.state}")
                                
                                if celery_task.state == TASK_STATUS_SUCCESS:
                                    # Update Redis with SUCCESS status
                                    logger.info(f"Updating stale task {task_id} from STARTED to SUCCESS based on Celery state")
                                    self.update_task_status(
                                        task_id=task_id,
                                        status=TASK_STATUS_SUCCESS,
                                        progress=100,
                                        message="Task completed successfully (status updated from Celery)",
                                    )
                                    # Refresh task_info
                                    task_info = self.get_task_info(task_id)
                            except Exception as e:
                                logger.warning(f"Error checking Celery task state for stale task {task_id}: {str(e)}")
                    except Exception as e:
                        logger.warning(f"Error checking task staleness for {task_id}: {str(e)}")
                
                # Return task_info directly, don't wrap it in another response object
                if task_info is not None:
                    logger.debug(f"Returning task info for {task_id}: {task_info.get('status', 'UNKNOWN')}, {task_info.get('progress', 0)}%")
                    return task_info
            
            # If we get here, no task info was found
            logger.debug(f"No task info found for task {task_id}")
            return {"status": "not_found", "message": "No analysis task found"}
                
        except RedisError as e:
            error_msg = f"Redis error in get_task_status for game {game_id}: {str(e)}"
            logger.warning(error_msg)
            return {"status": "error", "message": "Task status unavailable due to cache error"}
        except Exception as e:
            error_msg = f"Error getting task status for game {game_id}: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": f"Error retrieving task status: {str(e)}"}

    def get_task_status_by_id(self, task_id: str) -> Dict[str, Any]:
        """
        Get the status of a task by its ID.

        Args:
            task_id: ID of the task

        Returns:
            Task status dictionary (empty dict if not found)
        """
        task_info = self.get_task_info(task_id)
        if not task_info:
            # Check with Celery directly
            try:
                celery_task = AsyncResult(task_id)
                return {
                    "status": celery_task.state,
                    "result": celery_task.result if celery_task.ready() and celery_task.successful() else None,
                    "error": str(celery_task.result) if celery_task.ready() and not celery_task.successful() else None,
                }
            except Exception as e:
                logger.error(f"Error getting Celery task status for {task_id}: {str(e)}")
                return {"status": "UNKNOWN", "error": "Task not found"}

        return task_info

    def get_active_tasks_for_game(self, game_id: Union[int, str]) -> List[str]:
        """
        Get all active tasks associated with a game.

        Args:
            game_id: The ID of the game

        Returns:
            List of active task IDs for the game (empty list if none found)
        """
        try:
            # Convert game_id to string for consistency
            game_id_str = str(game_id)
            
            # Get the task ID for this game from in-memory cache
            task_id = None
            if game_id_str in self.game_tasks:
                task_id = self.game_tasks[game_id_str]
                logger.debug(f"Found task for game {game_id} in memory: {task_id}")
            
            # If not found in memory, try Redis
            if not task_id and self.redis_client is not None:
                try:
                    game_task_key = f"{self.GAME_TASK_KEY_PREFIX}{game_id}"
                    task_id = self.redis_client.get(game_task_key)
                    if task_id:
                        # Decode bytes to string if returned from Redis
                        if isinstance(task_id, bytes):
                            task_id = task_id.decode('utf-8')
                        logger.debug(f"Found task for game {game_id} in Redis: {task_id}")
                        # Update in-memory cache
                        self.game_tasks[game_id_str] = task_id
                except Exception as e:
                    logger.error(f"Redis error in get_active_tasks_for_game for game {game_id}: {str(e)}")
                    # Continue with the flow even if Redis fails
            
            if not task_id:
                logger.debug(f"No task found for game {game_id}")
                return []
            
            # Check if the task exists and get its status
            task_info = self.get_task_info(task_id)
            if not task_info:
                logger.debug(f"Task {task_id} for game {game_id} not found in task info")
                return []
            
            # Check if the task is still active (not completed or failed)
            status = task_info.get("status", "UNKNOWN")
            logger.debug(f"Task {task_id} for game {game_id} has status: {status}")
            
            # Return the task ID regardless of status to prevent duplicates
            # This ensures we don't create multiple tasks for the same game
            return [task_id]
        except Exception as e:
            logger.error(f"Error in get_active_tasks_for_game for game {game_id}: {str(e)}")
            return []

    def get_user_tasks(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all tasks associated with a user.

        Args:
            user_id: ID of the user

        Returns:
            List of task dictionaries
        """
        # Collect all tasks for the user
        user_tasks = []
        for task_id, task_info in self.tasks.items():
            if task_info.get("user_id") == user_id:
                user_tasks.append(task_info)

        # Try to find more in Redis (for tasks not in memory)
        if self.redis_client is not None:
            try:
                # TODO: Implement this
                # This would require scanning Redis which might be inefficient
                # In a real-world scenario, we would need a user-to-tasks index
                pass
            except Exception as e:
                logger.error(f"Error getting user tasks for user {user_id}: {str(e)}")

        return user_tasks

    def clear_all_tasks(self) -> int:
        """
        Clear all tasks from memory and Redis.

        Returns:
            Number of tasks cleared
        """
        count = len(self.tasks)

        try:
            # Clear memory
            self.tasks.clear()
            self.game_tasks.clear()

            # We would need Redis scan to clear all keys with prefix
            # This is not implemented for simplicity
        except Exception as e:
            logger.error(f"Error clearing all tasks: {str(e)}")

        return count

    def create_task(
        self,
        game_id: Optional[Union[int, str]] = None,
        user_id: Optional[int] = None,
        task_type: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Create a new task with initial pending status.

        Args:
            game_id: Optional ID of the game associated with the task
            user_id: Optional ID of the user who initiated the task
            task_type: Type of task (analysis, batch_analysis, import, export)
            parameters: Optional parameters for the task
            **kwargs: Additional task metadata

        Returns:
            The task ID
        """
        # Generate a unique task ID if not provided
        task_id = kwargs.get("task_id")
        if not task_id:
            current_time = int(time.time())
            random_suffix = os.urandom(4).hex()
            # Create a task ID including the type for easier identification
            task_prefix = task_type or "task"
            task_id = f"{task_prefix}_{current_time}_{random_suffix}"

        # Create task info
        task_info = {
            "id": task_id,
            "status": TASK_STATUS_PENDING,
            "progress": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "type": task_type,
        }

        # Add optional fields
        if game_id is not None:
            task_info["game_id"] = game_id
        if user_id is not None:
            task_info["user_id"] = user_id
        if parameters is not None:
            task_info["parameters"] = parameters
        
        # Add any additional kwargs
        for key, value in kwargs.items():
            if key != "task_id":  # Skip task_id as it's already set
                task_info[key] = value

        # Store in memory
        self.tasks[task_id] = task_info
        
        # If game_id is provided, store the mapping
        if game_id is not None:
            game_id_str = str(game_id)
            self.game_tasks[game_id_str] = task_id
            
            # Log the mapping
            logger.debug(f"Mapped game {game_id} to task {task_id} in memory")

        # Store in Redis with retry for resilience
        if self.redis_client is not None:
            max_retries = 3
            retry_delay = 0.1  # seconds
            
            task_key = f"{self.TASK_KEY_PREFIX}{task_id}"
            task_json = json.dumps(task_info)
            
            # Store the task info
            for attempt in range(max_retries):
                try:
                    self.redis_client.setex(
                        task_key,
                        self.task_timeout,
                        task_json
                    )
                    # Store succeeded, break the retry loop
                    logger.debug(f"Stored task {task_id} in Redis (attempt {attempt+1})")
                    break
                except Exception as e:
                    logger.error(f"Redis error storing task (attempt {attempt+1}): {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
            
            # Store game_id to task_id mapping in Redis if game_id is provided
            if game_id is not None:
                game_id_str = str(game_id)
                game_task_key = f"{self.GAME_TASK_KEY_PREFIX}{game_id_str}"
                
                for attempt in range(max_retries):
                    try:
                        self.redis_client.setex(
                            game_task_key,
                            self.task_timeout,
                            task_id
                        )
                        # Store succeeded, break the retry loop
                        logger.debug(f"Stored game {game_id} to task {task_id} mapping in Redis (attempt {attempt+1})")
                        break
                    except Exception as e:
                        logger.error(f"Redis error storing game-task mapping (attempt {attempt+1}): {str(e)}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)

        return task_id
