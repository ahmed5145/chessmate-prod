"""Task manager for handling analysis jobs."""
import json
import time
import logging
from typing import Dict, Any, Optional, List
from celery.result import AsyncResult
from django.core.cache import cache
from django.conf import settings
from datetime import datetime, timedelta
from .models import Game
from .constants import (
    STATUS_PENDING, STATUS_STARTED, STATUS_IN_PROGRESS, STATUS_SUCCESS,
    STATUS_FAILURE, STATUS_FAILED, CACHE_TTL, LOCK_TTL, TASK_EXPIRY,
    MAX_BATCH_SIZE, CACHE_TASK_PREFIX, CACHE_LOCK_PREFIX, CACHE_BATCH_PREFIX,
    QUEUE_ANALYSIS, QUEUE_BATCH_ANALYSIS
)

logger = logging.getLogger(__name__)

def log_job_event(job_id: str, event: str, details: Optional[dict] = None):
    """Log job events with consistent formatting."""
    logger.info(f"[Job {job_id}] {event} - {details if details else ''}")

class TaskManager:
    """Manages Celery tasks and their status."""
    
    STATUS_PENDING = STATUS_PENDING
    STATUS_STARTED = STATUS_STARTED
    STATUS_IN_PROGRESS = STATUS_IN_PROGRESS
    STATUS_SUCCESS = STATUS_SUCCESS
    STATUS_FAILURE = STATUS_FAILURE
    STATUS_FAILED = STATUS_FAILED
    
    VALID_STATUSES = {STATUS_PENDING, STATUS_STARTED, STATUS_IN_PROGRESS, STATUS_SUCCESS, STATUS_FAILURE}
    
    CELERY_STATUS_MAP = {
        'PENDING': STATUS_PENDING,
        'STARTED': STATUS_IN_PROGRESS,
        'PROGRESS': STATUS_IN_PROGRESS,
        'SUCCESS': 'completed',
        'COMPLETED': 'completed',
        'completed': 'completed',
        'FAILURE': STATUS_FAILURE,
        'REVOKED': STATUS_FAILURE,
        'RETRY': STATUS_IN_PROGRESS
    }

    _instance = None
    _CACHE_TTL = CACHE_TTL
    _LOCK_TTL = LOCK_TTL
    _MAX_BATCH_SIZE = MAX_BATCH_SIZE
    _TASK_EXPIRY = TASK_EXPIRY

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize task manager."""
        self.logger = logging.getLogger(__name__)

    def create_task(self, game_id: int, task_id: str) -> Dict[str, Any]:
        """Create a new task entry."""
        task_key = f"{CACHE_TASK_PREFIX}{game_id}"
        lock_key = f"{CACHE_LOCK_PREFIX}{game_id}"
        
        task_data = {
            'task_id': task_id,
            'status': STATUS_PENDING,
            'game_id': game_id,
            'details': {}
        }
        
        # Set task data with TTL
        cache.set(task_key, task_data, self._CACHE_TTL)
        # Set lock with shorter TTL
        cache.set(lock_key, task_id, self._LOCK_TTL)
        
        return task_data

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status with proper error handling and state management."""
        try:
            result = AsyncResult(task_id)
            state = result.state
            info = result.info or {}
            
            # Map Celery status to our status
            mapped_status = self.CELERY_STATUS_MAP.get(state, state)
            
            # Handle different states
            if state == 'SUCCESS':
                return {
                    'status': mapped_status,
                    'info': info
                }
            elif state in ['STARTED', 'PROGRESS']:
                return {
                    'status': mapped_status,
                    'info': info
                }
            elif state == 'PENDING':
                return {
                    'status': mapped_status,
                    'info': {'message': 'Task pending...'}
                }
            else:  # FAILURE or other states
                error_msg = str(result.result) if result.result else 'Task failed'
                return {
                    'status': self.STATUS_FAILURE,
                    'info': {'error': error_msg}
                }
                
        except Exception as e:
            self.logger.error(f"Error getting task status: {str(e)}")
            return {
                'status': self.STATUS_FAILURE,
                'info': {'error': str(e)}
            }

    # Alias for backward compatibility
    get_job_status = get_task_status

    def get_existing_task(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Get existing task data if any."""
        task_key = f"{CACHE_TASK_PREFIX}{game_id}"
        return cache.get(task_key)

    def update_task_status(self, game_id: int, status: str, details: Optional[Dict] = None) -> None:
        """Update task status with proper validation."""
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}")
            
        task_key = f"{CACHE_TASK_PREFIX}{game_id}"
        task_data = cache.get(task_key)
        
        if task_data:
            task_data['status'] = status
            if details:
                task_data['details'] = details
            cache.set(task_key, task_data, self._CACHE_TTL)
            log_job_event(str(game_id), f"Status updated to {status}", details)

    def cleanup_task(self, game_id: int) -> None:
        """Clean up task data and locks."""
        task_key = f"{CACHE_TASK_PREFIX}{game_id}"
        lock_key = f"{CACHE_LOCK_PREFIX}{game_id}"
        
        cache.delete(task_key)
        cache.delete(lock_key)
        
        logger.info(f"Cleaned up task data for game {game_id}")

    def create_analysis_job(self, game_id: int, depth: int = 20, use_ai: bool = True) -> Dict[str, Any]:
        """Create a new analysis job with proper concurrency control."""
        try:
            # Check if game exists and is not already analyzed
            game = Game.objects.get(id=game_id)
            if game.status == 'analyzed':
                return {'status': 'completed', 'game_id': game_id, 'message': 'Game already analyzed'}

            # Clean up any stale tasks first
            self.cleanup_task(game_id)

            # Check for existing task after cleanup
            existing_task = self.get_existing_task(game_id)
            if existing_task and not self._is_lock_expired(game_id):
                return {'status': 'in_progress', 'game_id': game_id, 'message': 'Game is already being analyzed'}

            # Try to acquire lock
            if not self._acquire_lock(game_id):
                return {'status': 'in_progress', 'game_id': game_id, 'message': 'Game is locked for analysis'}

            # Create new task
            task = self._create_celery_task('analyze_game_task', [game_id, depth, use_ai], QUEUE_ANALYSIS)

            # Store task information
            task_data = {
                'task_id': task.id,
                'game_id': game_id,
                'status': self.STATUS_PENDING,
                'created_at': datetime.now().isoformat(),
                'depth': depth,
                'use_ai': use_ai
            }
            
            task_key = f"{CACHE_TASK_PREFIX}{game_id}"
            cache.set(task_key, task_data, self._CACHE_TTL)
            
            log_job_event(task.id, "Analysis job created", {'game_id': game_id})
            return task_data

        except Game.DoesNotExist:
            self.logger.error(f"Game {game_id} not found")
            return {'status': 'error', 'game_id': game_id, 'message': 'Game not found'}
        except Exception as e:
            self.logger.error(f"Error creating analysis job for game {game_id}: {str(e)}")
            self._release_lock(game_id)
            return {'status': 'error', 'game_id': game_id, 'message': str(e)}

    def _create_celery_task(self, task_name: str, args: List[Any], queue: str):
        """Create a Celery task with the given name and arguments."""
        from celery import current_app
        task = current_app.tasks[f'core.tasks.{task_name}']
        return task.apply_async(args=args, queue=queue)

    def cleanup_expired_tasks(self) -> None:
        """Clean up expired tasks and their locks."""
        try:
            # This is a placeholder. In a real implementation, you would:
            # 1. Scan for expired tasks in cache
            # 2. Clean up associated locks
            # 3. Update game status if needed
            pass
        except Exception as e:
            self.logger.error(f"Error cleaning up expired tasks: {str(e)}")

    def create_batch_analysis_job(self, game_ids: List[int], depth: int = 20, use_ai: bool = True) -> Dict[str, Any]:
        """Create a batch analysis job with proper validation and limits."""
        try:
            # Validate batch size
            if len(game_ids) > self._MAX_BATCH_SIZE:
                return {
                    'status': 'error',
                    'message': f'Batch size exceeds maximum limit of {self._MAX_BATCH_SIZE} games'
                }

            # Filter out games that are already being analyzed
            available_games = []
            for game_id in game_ids:
                if not self.get_existing_task(game_id):
                    available_games.append(game_id)

            if not available_games:
                return {
                    'status': 'error',
                    'message': 'All selected games are already being analyzed'
                }
            
            # Create batch task
            task = self._create_celery_task('analyze_batch_games_task', [available_games, depth, use_ai], QUEUE_BATCH_ANALYSIS)

            # Store batch task information
            task_data = {
                'task_id': task.id,
                'game_ids': available_games,
                'status': self.STATUS_PENDING,
                'created_at': datetime.now().isoformat(),
                'depth': depth,
                'use_ai': use_ai,
                'total_games': len(available_games)
            }

            batch_key = f"{CACHE_BATCH_PREFIX}{task.id}"
            cache.set(batch_key, task_data, self._CACHE_TTL)

            log_job_event(task.id, "Batch analysis job created", 
                         {'games': len(available_games)})
            return task_data
            
        except Exception as e:
            self.logger.error(f"Error creating batch analysis job: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def _acquire_lock(self, game_id: int) -> bool:
        """Acquire a lock for game analysis with proper error handling."""
        try:
            lock_key = f"{CACHE_LOCK_PREFIX}{game_id}"
            # Use add() for atomic operation
            acquired = cache.add(lock_key, datetime.now().isoformat(), self._LOCK_TTL)
            if acquired:
                log_job_event(str(game_id), "Lock acquired")
            return acquired
        except Exception as e:
            self.logger.error(f"Error acquiring lock for game {game_id}: {str(e)}")
            return False

    def _release_lock(self, game_id: int) -> None:
        """Release the lock for game analysis with proper error handling."""
        try:
            lock_key = f"{CACHE_LOCK_PREFIX}{game_id}"
            cache.delete(lock_key)
            log_job_event(str(game_id), "Lock released")
        except Exception as e:
            self.logger.error(f"Error releasing lock for game {game_id}: {str(e)}")

    def _is_lock_expired(self, game_id: int) -> bool:
        """Check if a lock has expired."""
        try:
            lock_key = f"{CACHE_LOCK_PREFIX}{game_id}"
            lock_time = cache.get(lock_key)
            if not lock_time:
                return True
            lock_datetime = datetime.fromisoformat(lock_time)
            return (datetime.now() - lock_datetime).total_seconds() > self._LOCK_TTL
        except Exception as e:
            self.logger.error(f"Error checking lock expiry for game {game_id}: {str(e)}")
            return True

# Removed __del__ method since we're using context managers now
# def __del__(self):
#     """Cleanup when the instance is destroyed."""
#     if self._redis_client:
#         try:
#             self._redis_client.close()
#         except Exception as e:
#             logger.error(f"Error closing Redis client: {e}") 