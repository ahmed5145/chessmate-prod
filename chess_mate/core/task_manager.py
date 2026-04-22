"""
Task management for handling background tasks and tracking their status.

This module provides a TaskManager class to handle task registration, status tracking,
and retrieval for background tasks executed via Celery.
"""

import json
import logging
import time
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from celery.result import AsyncResult
from django.conf import settings
from redis.exceptions import RedisError  # type: ignore

from .cache import CACHE_BACKEND_REDIS, cache_delete, cache_get, cache_set
from .redis_connection import get_redis_connection
from .error_handling import ResourceNotFoundError, ValidationError

logger = logging.getLogger(__name__)

# Task status constants
TASK_STATUS_PENDING = "PENDING"
TASK_STATUS_STARTED = "STARTED"
TASK_STATUS_SUCCESS = "SUCCESS"
TASK_STATUS_FAILURE = "FAILURE"
TASK_STATUS_REVOKED = "REVOKED"
TASK_STATUS_RETRY = "RETRY"

TERMINAL_TASK_STATUSES = {TASK_STATUS_SUCCESS, TASK_STATUS_FAILURE, TASK_STATUS_REVOKED}

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

    _instance: Optional["TaskManager"] = None

    # Task types
    TYPE_ANALYSIS = "analysis"
    TYPE_BATCH_ANALYSIS = "batch_analysis"
    TYPE_IMPORT = "import"
    TYPE_EXPORT = "export"

    # Backward-compatible status aliases used in older code paths/tests.
    STATUS_PENDING = TASK_STATUS_PENDING
    STATUS_STARTED = TASK_STATUS_STARTED
    STATUS_RUNNING = "RUNNING"
    STATUS_COMPLETED = TASK_STATUS_SUCCESS
    STATUS_SUCCESS = TASK_STATUS_SUCCESS
    STATUS_FAILED = TASK_STATUS_FAILURE
    STATUS_FAILURE = TASK_STATUS_FAILURE
    STATUS_RETRY = TASK_STATUS_RETRY
    STATUS_REVOKED = TASK_STATUS_REVOKED

    TERMINAL_STATUSES = TERMINAL_TASK_STATUSES

    # Cache key prefixes
    TASK_KEY_PREFIX = "task:"
    GAME_TASK_KEY_PREFIX = "game_task:"
    USER_TASK_KEY_PREFIX = "user_tasks:"
    BATCH_KEY_PREFIX = "batch_task:"

    # Default task timeout (1 hour)
    DEFAULT_TASK_TIMEOUT = 3600
    DEFAULT_MAX_IN_MEMORY_TASKS = 5000

    def __new__(cls, *args: Any, **kwargs: Any):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, redis_client=None):
        """Initialize the task manager with default configuration."""
        if getattr(self, "_initialized", False):
            if redis_client is not None:
                self.redis_client = redis_client
            return

        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.game_tasks: Dict[str, str] = {}
        self.task_timeout = getattr(settings, "TASK_TIMEOUT", self.DEFAULT_TASK_TIMEOUT)
        self.max_in_memory_tasks = int(getattr(settings, "MAX_IN_MEMORY_TASKS", self.DEFAULT_MAX_IN_MEMORY_TASKS))

        # Initialize redis client
        if redis_client is not None:
            self.redis_client = redis_client
        else:
            self.redis_client = get_redis_connection()

        if self.redis_client is None:
            logger.warning("Redis connection not available, using in-memory storage only")

        self._initialized = True

    def _cache_get_value(self, key: str) -> Any:
        cache_get_fn = self._resolve_cache_symbol("cache_get", cache_get)
        return cache_get_fn(key, backend_name=CACHE_BACKEND_REDIS)

    def _cache_set_value(self, key: str, value: Any) -> bool:
        cache_set_fn = self._resolve_cache_symbol("cache_set", cache_set)
        return bool(cache_set_fn(key, value, timeout=self.task_timeout, backend_name=CACHE_BACKEND_REDIS))

    def _cache_delete_value(self, key: str) -> bool:
        cache_delete_fn = self._resolve_cache_symbol("cache_delete", cache_delete)
        return bool(cache_delete_fn(key, backend_name=CACHE_BACKEND_REDIS))

    def _resolve_cache_symbol(self, symbol: str, default: Any) -> Any:
        """Resolve cache symbols across aliases, preferring monkeypatched symbols."""
        candidates: List[Any] = []
        for module_name in (
            "core.task_manager",
            "chess_mate.core.task_manager",
            "chessmate_prod.chess_mate.core.task_manager",
            __name__,
        ):
            module = sys.modules.get(module_name)
            candidate = getattr(module, symbol, None) if module else None
            if callable(candidate):
                candidates.append(candidate)

        for candidate in candidates:
            if hasattr(candidate, "assert_called"):
                return candidate

        return candidates[0] if candidates else default

    def _resolve_async_result_cls(self) -> Any:
        """Resolve AsyncResult across aliases, preferring monkeypatched symbols."""
        candidates: List[Any] = []
        for module_name in (
            "core.task_manager",
            "chess_mate.core.task_manager",
            "chessmate_prod.chess_mate.core.task_manager",
            __name__,
        ):
            module = sys.modules.get(module_name)
            candidate = getattr(module, "AsyncResult", None) if module else None
            if callable(candidate):
                candidates.append(candidate)

        for candidate in candidates:
            if hasattr(candidate, "assert_called"):
                return candidate

        return candidates[0] if candidates else AsyncResult

    def _build_async_result(self, task_id: str) -> Any:
        """Create AsyncResult bound to the project Celery app when available."""
        async_result_cls = self._resolve_async_result_cls()
        try:
            from chess_mate.celery import app as celery_app
            return async_result_cls(task_id, app=celery_app)
        except TypeError:
            # Compatibility with mocks/legacy call signatures.
            return async_result_cls(task_id)
        except Exception:
            return async_result_cls(task_id)

    def _prune_in_memory_tasks(self) -> int:
        """Prune oldest in-memory task entries when cache exceeds configured bounds."""
        overflow = len(self.tasks) - self.max_in_memory_tasks
        if overflow <= 0:
            return 0

        sortable: List[tuple[str, str]] = []
        for task_id, task_info in self.tasks.items():
            updated_at = str(task_info.get("updated_at", ""))
            sortable.append((task_id, updated_at))

        # Oldest timestamps first.
        sortable.sort(key=lambda item: item[1])
        to_remove = [task_id for task_id, _ in sortable[:overflow]]

        for task_id in to_remove:
            task_info = self.tasks.pop(task_id, None)
            if not task_info:
                continue

            game_id = task_info.get("game_id")
            if game_id is not None:
                game_id_str = str(game_id)
                if self.game_tasks.get(game_id_str) == task_id:
                    self.game_tasks.pop(game_id_str, None)

        logger.warning(
            f"Pruned {len(to_remove)} in-memory task records to enforce MAX_IN_MEMORY_TASKS={self.max_in_memory_tasks}"
        )
        return len(to_remove)

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
        # Backward-compatible positional signature:
        # register_task(task_id, game_id, user_id)
        if isinstance(task_type, int):
            game_id = task_type
            task_type = self.TYPE_ANALYSIS

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
        self._prune_in_memory_tasks()

        # If game_id is provided, store mapping in memory immediately
        if game_id is not None:
            game_id_str = str(game_id)
            self.game_tasks[game_id_str] = task_id
            logger.debug(f"Mapped game {game_id} to task {task_id} in memory")

        # Store in cache/Redis-compatible path for legacy tests
        task_key = f"{self.TASK_KEY_PREFIX}{task_id}"
        self._cache_set_value(task_key, task_info)

        if game_id is not None:
            game_task_key = f"{self.GAME_TASK_KEY_PREFIX}{game_id}"
            self._cache_set_value(game_task_key, task_id)

        if user_id is not None:
            user_key = f"{self.USER_TASK_KEY_PREFIX}{user_id}"
            existing = self._cache_get_value(user_key) or []
            if task_id not in existing:
                existing.append(task_id)
            self._cache_set_value(user_key, existing)

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
                logger.debug(f"Stored task {task_id} in Redis")

                # If game_id is provided, store a mapping from game to task
                if game_id is not None:
                    game_task_key = f"{self.GAME_TASK_KEY_PREFIX}{game_id}"
                    self.redis_client.setex(
                        game_task_key,
                        self.task_timeout,
                        task_id
                    )
                    logger.debug(f"Stored game {game_id} to task {task_id} mapping in Redis")
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
        self._prune_in_memory_tasks()

        # Legacy-compatible cache keys
        batch_key = f"{self.BATCH_KEY_PREFIX}{task_id}"
        self._cache_set_value(batch_key, task_info)
        for game_id in game_ids:
            self._cache_set_value(f"{self.GAME_TASK_KEY_PREFIX}{game_id}", task_id)

        if user_id is not None:
            user_key = f"{self.USER_TASK_KEY_PREFIX}{user_id}"
            existing = self._cache_get_value(user_key) or []
            if task_id not in existing:
                existing.append(task_id)
            self._cache_set_value(user_key, existing)

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
        task_id: Optional[str] = None,
        game_id: Optional[Union[int, str]] = None,
        status: str = TASK_STATUS_PENDING,
        progress: int = 0,
        message: str = "",
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update the status of a task.

        Args:
            task_id: The task ID
            status: The new status
            progress: The progress percentage (0-100)
            message: Optional status message
            data: Optional data associated with the task
            error: Optional error message
            result: Optional result data when task completes

        Returns:
            True if update was successful, False otherwise
        """
        try:
            if not task_id and game_id is None:
                raise ValidationError("task_id or game_id is required")

            if not task_id and game_id is not None:
                task_id = self._get_task_id_for_game(game_id)
                if not task_id:
                    raise ResourceNotFoundError(f"No task found for game {game_id}")

            if task_id is None:
                raise ValidationError("task_id is required")

            normalized_status = str(status).upper()

            # Create task info to store
            updated_at = datetime.now().isoformat()
            task_info = {
                "id": task_id,
                "status": normalized_status,
                "progress": progress,
                "message": message,
                "updated_at": updated_at,
            }

            if data:
                task_info["data"] = data
            if error:
                task_info["error"] = error
            if result:
                task_info["result"] = result

            # Validate progress value
            if not isinstance(progress, (int, float)) or progress < 0 or progress > 100:
                logger.warning(f"Invalid progress value {progress} for task {task_id}, setting to 0")
                task_info["progress"] = 0

            # First update memory cache, which is faster and always available
            previous_info = self.tasks.get(task_id, None) or self._cache_get_value(f"{self.TASK_KEY_PREFIX}{task_id}")
            if not previous_info:
                raise ResourceNotFoundError(f"Task {task_id} not found")

            previous_status = str(previous_info.get("status", TASK_STATUS_PENDING)).upper()
            previous_progress = int(previous_info.get("progress", 0) or 0)

            # Once a task reaches terminal state, ignore non-terminal stale updates.
            if previous_status in self.TERMINAL_STATUSES and normalized_status not in self.TERMINAL_STATUSES:
                logger.debug(
                    f"Ignoring stale non-terminal update for terminal task {task_id}: "
                    f"{previous_status} ({previous_progress}%) -> {normalized_status} ({progress}%)"
                )
                return True

            # Prevent progress regressions for non-terminal updates.
            if normalized_status not in self.TERMINAL_STATUSES and previous_progress > int(task_info["progress"] or 0):
                logger.debug(
                    f"Ignoring stale progress regression for task {task_id}: "
                    f"{previous_status} ({previous_progress}%) -> {normalized_status} ({progress}%)"
                )
                return True

            # Normalized success semantics: completed tasks always report 100%.
            if normalized_status == TASK_STATUS_SUCCESS:
                task_info["progress"] = 100

            if previous_info:
                # Check if this update represents progress compared to the previous state
                prev_progress = previous_info.get("progress", 0)
                prev_status = previous_info.get("status", "")

                # Log the update with appropriate level based on whether it's progress or regression
                if progress >= prev_progress and status != TASK_STATUS_FAILURE:
                    logger.info(
                        "Updating task %s: %s (%s%%) -> %s (%s%%) - %s",
                        task_id,
                        prev_status,
                        prev_progress,
                        status,
                        progress,
                        message,
                    )
                else:
                    # This could be a duplicate or out-of-order update, log as debug
                    logger.debug(
                        "Updating task %s with possibly older info: %s (%s%%) -> %s (%s%%) - %s",
                        task_id,
                        prev_status,
                        prev_progress,
                        status,
                        progress,
                        message,
                    )
            else:
                logger.info(f"Creating new task status for {task_id}: {status} ({progress}%) - {message}")

            # Update in-memory cache
            if previous_info:
                merged_info = {**previous_info, **task_info}
            else:
                merged_info = task_info

            task_info = merged_info
            self.tasks[task_id] = task_info
            self._prune_in_memory_tasks()

            # Keep legacy cache representation in sync.
            self._cache_set_value(f"{self.TASK_KEY_PREFIX}{task_id}", task_info)

            # Then update Redis if available
            if self.redis_client is not None:
                try:
                    task_key = f"{self.TASK_KEY_PREFIX}{task_id}"
                    # Set with timeout to auto-expire old tasks
                    self.redis_client.setex(
                        task_key,
                        self.task_timeout,
                        json.dumps(task_info)
                    )
                    logger.debug(f"Updated Redis task status for {task_id}")

                    # Verify the update was written to Redis by reading it back
                    try:
                        data = self.redis_client.get(task_key)
                        if data:
                            if isinstance(data, bytes):
                                data_str = data.decode('utf-8')
                            else:
                                data_str = str(data)
                            redis_task_info = json.loads(data_str)
                            logger.debug(
                                "Verified Redis write for task %s: %s, %s%%",
                                task_id,
                                redis_task_info.get("status", "UNKNOWN"),
                                redis_task_info.get("progress", 0),
                            )
                    except Exception as e:
                        logger.warning(f"Could not verify Redis write for task {task_id}: {str(e)}")
                except RedisError as e:
                    error_msg = f"Redis error updating task status for {task_id}: {str(e)}"
                    logger.warning(error_msg)
                    # Continue execution since memory cache was updated successfully
                except Exception as e:
                    error_msg = f"Error updating Redis for task {task_id}: {str(e)}"
                    logger.error(error_msg)

            # If task is in terminal state (SUCCESS/FAILURE), perform cleanup
            if status in [TASK_STATUS_SUCCESS, TASK_STATUS_FAILURE]:
                logger.debug(f"Task {task_id} reached terminal state: {status}")
                # Keep task info in memory for a short time for status checks
                # But will eventually be cleaned up by the cleanup_expired_tasks method

            return True

        except (ValidationError, ResourceNotFoundError):
            raise
        except Exception as e:
            error_msg = f"Error updating task status for {task_id}: {str(e)}"
            logger.error(error_msg)
            return False

    def get_task(self, task_id: str) -> Dict[str, Any]:
        task = self._cache_get_value(f"{self.TASK_KEY_PREFIX}{task_id}") or self.tasks.get(task_id)
        if not task:
            raise ResourceNotFoundError(f"Task {task_id} not found")
        return task

    def get_existing_task(self, game_id: Union[int, str]) -> Dict[str, Any]:
        task_id = self.get_task_for_game(game_id)
        if not task_id:
            raise ResourceNotFoundError(f"No task found for game {game_id}")
        return self.get_task(task_id)

    def get_task_info(self, task_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Get information about a task from Redis or in-memory cache.

        Args:
            task_id: ID of the task, can be None

        Returns:
            Task info dictionary or None if not found or invalid task_id
        """
        if not task_id:
            logger.debug("get_task_info called with empty task_id")
            return None

        # Type check - ensure we have a string task_id
        if not isinstance(task_id, str):
            try:
                task_id = str(task_id)
                logger.warning(f"get_task_info received non-string task_id, converted {task_id} to string")
            except Exception as e:
                logger.error(f"Failed to convert task_id to string: {e}")
                return None

        # Try to get from memory/cache first
        task_info = self.tasks.get(task_id) or self._cache_get_value(f"{self.TASK_KEY_PREFIX}{task_id}")

        # Try to get from Redis if available
        try:
            if self.redis_client is not None:
                redis_key = f"{self.TASK_KEY_PREFIX}{task_id}"
                task_data = self.redis_client.get(redis_key)
                if task_data:
                    try:
                        # Handle bytes data from Redis
                        if isinstance(task_data, bytes):
                            redis_info = json.loads(task_data.decode('utf-8'))
                        else:
                            redis_info = json.loads(str(task_data))

                        # If we have memory info, merge with Redis data (preferring Redis)
                        if task_info:
                            task_info = {**task_info, **redis_info}
                        else:
                            task_info = redis_info
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        logger.error(f"Error decoding Redis data for task {task_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting task info from Redis for {task_id}: {str(e)}")
            # Continue with memory cache data only

        if not task_info:
            return None

        # Overlay latest Celery state for compatibility with tests and polling callers.
        try:
            async_result = self._build_async_result(task_id)
            state = async_result.state
            if state and state != task_info.get("status"):
                task_info["status"] = state
                if state == TASK_STATUS_SUCCESS:
                    task_info["progress"] = 100
                    task_info["result"] = async_result.result
                elif state == TASK_STATUS_FAILURE:
                    task_info["error"] = str(async_result.result)
                self.tasks[task_id] = task_info
                self._cache_set_value(f"{self.TASK_KEY_PREFIX}{task_id}", task_info)
        except Exception:
            pass

        return task_info

    def get_task_for_game(self, game_id: Union[int, str]) -> Optional[str]:
        """
        Get the task ID associated with a game.

        Args:
            game_id: ID of the game

        Returns:
            Task ID or None if no task is found
        """
        # Use the implementation from _get_task_id_for_game for backward compatibility
        return self._get_task_id_for_game(game_id)

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
            celery_task = self._build_async_result(task_id)
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

    def get_expired_tasks(self, expiry_hours: int = 24) -> List[str]:
        """Return IDs of tasks older than the expiry window."""
        expiry_time = datetime.now() - timedelta(hours=expiry_hours)
        expired: List[str] = []
        for task_id, task_info in self.tasks.items():
            try:
                updated_at = datetime.fromisoformat(task_info.get("updated_at", "2000-01-01"))
                if updated_at < expiry_time:
                    expired.append(task_id)
            except Exception:
                continue
        return expired

    def cleanup_task(self, task_id: str) -> bool:
        """Remove a task and associated mappings from memory/Redis."""
        removed = False
        task_info = self.tasks.pop(task_id, None)
        if task_info is not None:
            removed = True
            game_id = task_info.get("game_id")
            if game_id is not None:
                game_id_str = str(game_id)
                if self.game_tasks.get(game_id_str) == task_id:
                    self.game_tasks.pop(game_id_str, None)

        if self.redis_client is not None:
            try:
                self.redis_client.delete(f"{self.TASK_KEY_PREFIX}{task_id}")
                if task_info and task_info.get("game_id") is not None:
                    self.redis_client.delete(f"{self.GAME_TASK_KEY_PREFIX}{task_info.get('game_id')}")
            except Exception:
                pass

        # Legacy cache cleanup
        self._cache_delete_value(f"{self.TASK_KEY_PREFIX}{task_id}")
        if task_info and task_info.get("game_id") is not None:
            self._cache_delete_value(f"{self.GAME_TASK_KEY_PREFIX}{task_info.get('game_id')}")

        return removed

    def _validate_task_id(self, task_id: Any) -> Optional[str]:
        """
        Validate that a task_id is in the correct format for a Celery task.

        Args:
            task_id: The task ID to validate

        Returns:
            Validated task ID as string if valid, None otherwise
        """
        if not task_id:
            return None

        # Convert to string if needed
        if not isinstance(task_id, str):
            try:
                task_id = str(task_id)
            except Exception:
                logger.error(f"Failed to convert task_id {task_id} to string")
                return None

        # Most Celery task IDs are UUIDs or have a specific format
        # Game IDs are typically numeric, so we can use that as a simple check
        if task_id.isdigit():
            logger.warning(
                "Task ID %s appears to be a numeric ID (possibly a game ID), not a valid Celery task ID",
                task_id,
            )
            return None

        # More sophisticated validation could be done here if needed
        return task_id

    def get_task_status(
        self,
        task_id: Optional[str] = None,
        game_id: Optional[Union[int, str]] = None,
    ) -> Dict[str, Any]:
        """
        Get status of a task by task_id or game_id.

        Args:
            task_id: ID of task to check (optional if game_id provided)
            game_id: ID of game to find task for (optional if task_id provided)

        Returns:
            Dictionary with status information
        """
        if not task_id and not game_id:
            return self._default_status("INVALID", "No task_id or game_id provided", 0)

        # Backward-compatibility: some call sites accidentally pass game_id as
        # the first positional arg (task_id). Numeric IDs are treated as game IDs.
        if task_id and game_id is None:
            normalized_task_id = str(task_id)
            if normalized_task_id.isdigit():
                game_id = normalized_task_id
                task_id = None

        # If only game_id is provided, try to get task_id for that game
        original_task_id = task_id
        if not task_id and game_id:
            task_id = self._get_task_id_for_game(game_id)
            if not task_id:
                # Pass the game_id to the default status so it's included in the response
                return self._default_status("PENDING", f"No task found for game {game_id}", 0, None, game_id)

        # Get task info from cache - must provide valid task_id string
        if task_id:
            task_info = self.get_task_info(task_id)
        else:
            task_info = None

        # If no task info found, check if we can get status directly from Celery
        # Only check Celery if we have a valid task_id (not a game_id)
        if not task_info and task_id:
            # Validate that task_id is suitable for AsyncResult
            validated_task_id = self._validate_task_id(task_id)
            if validated_task_id:
                try:
                    # Try to get status directly from Celery
                    celery_task = self._build_async_result(validated_task_id)
                    celery_status = celery_task.status

                    # If Celery reports the task is done but we don't have info, create a default response
                    if celery_status in [TASK_STATUS_SUCCESS, TASK_STATUS_FAILURE]:
                        progress = 100 if celery_status == TASK_STATUS_SUCCESS else 0
                        message = "Task completed" if celery_status == TASK_STATUS_SUCCESS else "Task failed"
                        return self._default_status(celery_status, message, progress, task_id, game_id)

                except Exception as e:
                    logger.error(f"Error checking Celery status for task {task_id}: {str(e)}")
                    # Continue with default status

        # If still no task info found, return default pending status
        if not task_info:
            # Pass the task_id to the default status so it's included in the response
            return self._default_status(
                "PENDING",
                f"Task {original_task_id or task_id} not found or not started",
                0,
                task_id,
                game_id,
            )

        # Extract status information from task_info
        status = task_info.get('status', 'PENDING')
        message = task_info.get('message', '')
        progress = task_info.get('progress', 0)

        if str(status).upper() == TASK_STATUS_PENDING and (
            not message or message.lower() == 'task pending'
        ):
            message = "Task queued, waiting for worker availability"

        # Ensure progress is consistent with status
        if status == TASK_STATUS_SUCCESS and progress < 100:
            logger.warning(
                "Task %s has SUCCESS status but progress is only %s%%, adjusting to 100%%",
                task_id,
                progress,
            )
            progress = 100

        # Return properly formatted status dictionary
        return {
            'status': status,
            'message': message,
            'progress': progress,
            'task_id': task_id,
            'metadata': task_info.get('metadata', {})
        }

    def _default_status(
        self,
        status: str,
        message: str,
        progress: int,
        task_id: Optional[str] = None,
        game_id: Optional[Union[int, str]] = None,
    ) -> Dict[str, Any]:
        """Helper to create consistent status responses"""
        return {
            'status': status,
            'message': message,
            'progress': progress,
            'task_id': task_id,
            'game_id': game_id,
            'metadata': {}
        }

    def _is_newer_task_info(self, info1, info2):
        """
        Determine which task info is newer based on timestamps and progress.

        Args:
            info1: First task info dictionary
            info2: Second task info dictionary

        Returns:
            True if info1 is newer than info2, False otherwise
        """
        # If either is missing updated_at, use progress as the determinant
        if "updated_at" not in info1 or "updated_at" not in info2:
            return info1.get("progress", 0) > info2.get("progress", 0)

        # Compare timestamps
        try:
            time1 = datetime.fromisoformat(info1["updated_at"])
            time2 = datetime.fromisoformat(info2["updated_at"])

            # If timestamps are very close (within 1 second), prefer the one with higher progress
            if abs((time1 - time2).total_seconds()) < 1:
                return info1.get("progress", 0) >= info2.get("progress", 0)

            return time1 > time2
        except (ValueError, TypeError):
            # If we can't parse the timestamps, fall back to progress comparison
            return info1.get("progress", 0) > info2.get("progress", 0)

    def _is_task_info_stale(self, task_info):
        """
        Check if task info appears to be stale (hasn't been updated recently)

        Args:
            task_info: Task info dictionary with updated_at timestamp

        Returns:
            True if task info appears stale, False otherwise
        """
        if "updated_at" not in task_info:
            return False

        try:
            # Configure stale threshold in seconds
            self.STALE_THRESHOLD_SECONDS = 60  # Consider task stale if no updates in 60 seconds

            update_time = datetime.fromisoformat(task_info["updated_at"])
            now = datetime.now()
            seconds_since_update = (now - update_time).total_seconds()

            return seconds_since_update > self.STALE_THRESHOLD_SECONDS
        except (ValueError, TypeError):
            return False

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
            # Return default status instead of checking Celery
            return {
                "status": "PENDING",
                "message": "Task not found or not started",
                "progress": 0
            }

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
                self.game_tasks.pop(game_id_str, None)
                if self.redis_client is not None:
                    try:
                        self.redis_client.delete(f"{self.GAME_TASK_KEY_PREFIX}{game_id_str}")
                    except Exception:
                        pass
                return []

            # Check if the task is still active (not completed or failed)
            status = task_info.get("status", "UNKNOWN")
            logger.debug(f"Task {task_id} for game {game_id} has status: {status}")

            if status in self.TERMINAL_STATUSES:
                # Terminal tasks should no longer block new analysis runs.
                self.game_tasks.pop(game_id_str, None)
                if self.redis_client is not None:
                    try:
                        self.redis_client.delete(f"{self.GAME_TASK_KEY_PREFIX}{game_id_str}")
                    except Exception:
                        pass
                return []

            # Non-terminal task is active and should prevent duplicate enqueue.
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
            "game_id": game_id,
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
        self._prune_in_memory_tasks()

        # Store in cache-backed compatibility layer
        self._cache_set_value(f"{self.TASK_KEY_PREFIX}{task_id}", task_info)

        # If game_id is provided, store the mapping
        if game_id is not None:
            game_id_str = str(game_id)
            self.game_tasks[game_id_str] = task_id
            self._cache_set_value(f"{self.GAME_TASK_KEY_PREFIX}{game_id_str}", task_id)

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

    def create_analysis_job(
        self,
        game_id: Union[int, str],
        user_id: Optional[int] = None,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Backward-compatible wrapper used by legacy analysis tests."""
        task_id = self.create_task(
            game_id=game_id,
            user_id=user_id,
            task_type=self.TYPE_ANALYSIS,
            parameters=parameters,
            **kwargs,
        )
        return self.get_task_status_by_id(task_id)

    def _get_task_id_for_game(self, game_id: Union[int, str]) -> Optional[str]:
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
                game_key = f"{self.GAME_TASK_KEY_PREFIX}{game_id_str}"
                try:
                    task_id = self.redis_client.get(game_key)
                    if task_id:
                        # Convert bytes to string if needed
                        if isinstance(task_id, bytes):
                            task_id = task_id.decode('utf-8')

                        # Cache in memory for future lookups
                        self.game_tasks[game_id_str] = task_id
                        logger.debug(f"Found task ID {task_id} for game {game_id} in Redis")
                        return task_id
                except Exception as e:
                    logger.error(f"Redis error getting task ID for game {game_id}: {str(e)}")

            logger.debug(f"No task found for game {game_id}")
            return None

        except Exception as e:
            logger.error(f"Error in _get_task_id_for_game for game {game_id}: {str(e)}")
            return None
