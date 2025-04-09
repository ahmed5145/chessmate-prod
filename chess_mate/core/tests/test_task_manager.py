"""Tests for the TaskManager class."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest
from celery.result import AsyncResult
from core.error_handling import ResourceNotFoundError, TaskError, ValidationError
from core.task_manager import TaskManager
from django.test import TestCase, override_settings


@pytest.mark.django_db
class TestTaskManager:
    """Tests for the TaskManager class."""

    def setup_method(self):
        """Set up test data before each test method."""
        self.task_manager = TaskManager()

        # Mock redis cache functions
        self.cache_data = {}
        self.cache_expiry = {}

        # Apply patches
        self.cache_get_patch = patch("core.task_manager.cache_get")
        self.cache_set_patch = patch("core.task_manager.cache_set")
        self.cache_delete_patch = patch("core.task_manager.cache_delete")

        self.mock_cache_get = self.cache_get_patch.start()
        self.mock_cache_set = self.cache_set_patch.start()
        self.mock_cache_delete = self.cache_delete_patch.start()

        # Make the mocks store and retrieve data
        def mock_cache_get_func(key, **kwargs):
            return self.cache_data.get(key)

        def mock_cache_set_func(key, value, **kwargs):
            self.cache_data[key] = value
            # Store expiry if provided
            if "timeout" in kwargs:
                self.cache_expiry[key] = time.time() + kwargs["timeout"]
            return True

        def mock_cache_delete_func(key, **kwargs):
            if key in self.cache_data:
                del self.cache_data[key]
                if key in self.cache_expiry:
                    del self.cache_expiry[key]
                return True
            return False

        self.mock_cache_get.side_effect = mock_cache_get_func
        self.mock_cache_set.side_effect = mock_cache_set_func
        self.mock_cache_delete.side_effect = mock_cache_delete_func

    def teardown_method(self):
        """Clean up after each test method."""
        self.cache_get_patch.stop()
        self.cache_set_patch.stop()
        self.cache_delete_patch.stop()

        # Clear cache data
        self.cache_data = {}
        self.cache_expiry = {}

    def test_singleton_pattern(self):
        """Test that TaskManager follows the singleton pattern."""
        task_manager1 = TaskManager()
        task_manager2 = TaskManager()
        assert task_manager1 is task_manager2

    def test_create_task(self):
        """Test creating a new task."""
        # Create a task
        game_id = 123
        task_id = self.task_manager.create_task(
            game_id=game_id, task_type=TaskManager.TYPE_ANALYSIS, parameters={"depth": 20}
        )

        # Verify task was created
        assert task_id is not None
        assert isinstance(task_id, str)

        # Verify task data was stored in cache
        key = f"{TaskManager.TASK_KEY_PREFIX}{task_id}"
        assert key in self.cache_data

        # Verify task data structure
        task_data = self.cache_data[key]
        assert task_data["id"] == task_id
        assert task_data["game_id"] == game_id
        assert task_data["type"] == TaskManager.TYPE_ANALYSIS
        assert task_data["status"] == TaskManager.STATUS_PENDING
        assert task_data["parameters"] == {"depth": 20}
        assert "created_at" in task_data
        assert "updated_at" in task_data

        # Verify game to task mapping
        game_key = f"{TaskManager.GAME_TASK_KEY_PREFIX}{game_id}"
        assert game_key in self.cache_data
        assert self.cache_data[game_key] == task_id

    def test_create_task_without_game_id(self):
        """Test creating a task without a game ID."""
        # Create a task without game_id
        task_id = self.task_manager.create_task(
            task_type=TaskManager.TYPE_BATCH_ANALYSIS, parameters={"game_ids": [1, 2, 3]}
        )

        # Verify task was created
        assert task_id is not None

        # Verify task data
        key = f"{TaskManager.TASK_KEY_PREFIX}{task_id}"
        task_data = self.cache_data[key]
        assert task_data["game_id"] is None

    def test_get_task(self):
        """Test retrieving a task by ID."""
        # Create a task
        task_id = self.task_manager.create_task(game_id=123)

        # Get the task
        task = self.task_manager.get_task(task_id)

        # Verify task data
        assert task["id"] == task_id
        assert task["game_id"] == 123

    def test_get_nonexistent_task(self):
        """Test retrieving a non-existent task."""
        with pytest.raises(ResourceNotFoundError):
            self.task_manager.get_task("nonexistent_task_id")

    def test_get_task_for_game(self):
        """Test retrieving a task ID for a game."""
        # Create a task for a game
        game_id = 456
        task_id = self.task_manager.create_task(game_id=game_id)

        # Get task ID for the game
        retrieved_task_id = self.task_manager.get_task_for_game(game_id)

        # Verify task ID
        assert retrieved_task_id == task_id

    def test_get_task_for_nonexistent_game(self):
        """Test retrieving a task for a non-existent game."""
        # Should return None, not raise an exception
        result = self.task_manager.get_task_for_game(999)
        assert result is None

    def test_get_existing_task(self):
        """Test retrieving an existing task for a game."""
        # Create a task for a game
        game_id = 789
        task_id = self.task_manager.create_task(game_id=game_id)

        # Get existing task for the game
        task = self.task_manager.get_existing_task(game_id)

        # Verify task data
        assert task["id"] == task_id
        assert task["game_id"] == game_id

    def test_update_task_status(self):
        """Test updating a task's status."""
        # Create a task
        task_id = self.task_manager.create_task(game_id=123)

        # Update task status
        self.task_manager.update_task_status(task_id=task_id, status=TaskManager.STATUS_RUNNING)

        # Get the updated task
        task = self.task_manager.get_task(task_id)

        # Verify status was updated
        assert task["status"] == TaskManager.STATUS_RUNNING

    def test_update_task_status_with_game_id(self):
        """Test updating a task's status using game ID."""
        # Create a task
        game_id = 123
        task_id = self.task_manager.create_task(game_id=game_id)

        # Update task status using game_id
        self.task_manager.update_task_status(game_id=game_id, status=TaskManager.STATUS_COMPLETED, result={"score": 95})

        # Get the updated task
        task = self.task_manager.get_task(task_id)

        # Verify status and result were updated
        assert task["status"] == TaskManager.STATUS_COMPLETED
        assert task["result"] == {"score": 95}

    def test_update_task_status_with_error(self):
        """Test updating a task's status with an error."""
        # Create a task
        task_id = self.task_manager.create_task(game_id=123)

        # Update task status with error
        self.task_manager.update_task_status(
            task_id=task_id, status=TaskManager.STATUS_FAILED, error="Analysis failed due to invalid PGN"
        )

        # Get the updated task
        task = self.task_manager.get_task(task_id)

        # Verify status and error were updated
        assert task["status"] == TaskManager.STATUS_FAILED
        assert task["error"] == "Analysis failed due to invalid PGN"

    def test_update_nonexistent_task(self):
        """Test updating a non-existent task."""
        with pytest.raises(ResourceNotFoundError):
            self.task_manager.update_task_status(task_id="nonexistent_task_id", status=TaskManager.STATUS_RUNNING)

    def test_update_task_without_id_or_game_id(self):
        """Test updating a task without providing task_id or game_id."""
        with pytest.raises(ValidationError):
            self.task_manager.update_task_status(status=TaskManager.STATUS_RUNNING)

    def test_cleanup_task(self):
        """Test cleaning up a task."""
        # Create a task
        game_id = 123
        task_id = self.task_manager.create_task(game_id=game_id)

        # Verify task and mapping exist
        task_key = f"{TaskManager.TASK_KEY_PREFIX}{task_id}"
        game_key = f"{TaskManager.GAME_TASK_KEY_PREFIX}{game_id}"
        assert task_key in self.cache_data
        assert game_key in self.cache_data

        # Clean up the task
        self.task_manager.cleanup_task(task_id)

        # Verify task and mapping were removed
        assert task_key not in self.cache_data
        assert game_key not in self.cache_data

    def test_register_task(self):
        """Test registering a task for a game and user."""
        # Register a task
        game_id = 123
        user_id = 456
        task_id = "test_task_1"
        task_type = TaskManager.TYPE_ANALYSIS

        self.task_manager.register_task(game_id=game_id, task_id=task_id, task_type=task_type, user_id=user_id)

        # Verify game to task mapping
        game_key = f"{TaskManager.GAME_TASK_KEY_PREFIX}{game_id}"
        assert self.cache_data[game_key] == task_id

        # Verify user to tasks mapping
        user_key = f"{TaskManager.USER_TASK_KEY_PREFIX}{user_id}"
        assert task_id in self.cache_data[user_key]

    def test_register_task_without_user(self):
        """Test registering a task without a user ID."""
        # Register a task without user_id
        game_id = 123
        task_id = "test_task_2"
        task_type = TaskManager.TYPE_ANALYSIS

        self.task_manager.register_task(game_id=game_id, task_id=task_id, task_type=task_type)

        # Verify game to task mapping
        game_key = f"{TaskManager.GAME_TASK_KEY_PREFIX}{game_id}"
        assert self.cache_data[game_key] == task_id

    def test_register_batch_task(self):
        """Test registering a batch task for multiple games."""
        # Register a batch task
        game_ids = [1, 2, 3]
        user_id = 456
        task_id = "batch_task_1"

        self.task_manager.register_batch_task(task_id=task_id, game_ids=game_ids, user_id=user_id)

        # Verify batch task data
        batch_key = f"{TaskManager.BATCH_KEY_PREFIX}{task_id}"
        assert batch_key in self.cache_data
        batch_data = self.cache_data[batch_key]
        assert batch_data["id"] == task_id
        assert batch_data["game_ids"] == game_ids
        assert batch_data["user_id"] == user_id

        # Verify individual game mappings
        for game_id in game_ids:
            game_key = f"{TaskManager.GAME_TASK_KEY_PREFIX}{game_id}"
            assert self.cache_data[game_key] == task_id

    @patch("core.task_manager.AsyncResult")
    def test_get_task_info(self, mock_async_result):
        """Test retrieving task info including Celery status."""
        # Create a task
        game_id = 123
        task_id = self.task_manager.create_task(game_id=game_id)

        # Mock Celery AsyncResult
        mock_result = MagicMock()
        mock_result.state = "SUCCESS"
        mock_result.result = {"analysis": "completed"}
        mock_async_result.return_value = mock_result

        # Get task info
        task_info = self.task_manager.get_task_info(task_id)

        # Verify task info
        assert task_info["id"] == task_id
        assert task_info["status"] == "SUCCESS"
        assert task_info["game_id"] == game_id
        assert task_info["result"] == {"analysis": "completed"}

    @patch("core.task_manager.AsyncResult")
    def test_get_task_info_failed(self, mock_async_result):
        """Test retrieving info for a failed task."""
        # Create a task
        task_id = self.task_manager.create_task()

        # Mock Celery AsyncResult for a failed task
        mock_result = MagicMock()
        mock_result.state = "FAILURE"
        mock_result.result = Exception("Task failed")
        mock_async_result.return_value = mock_result

        # Get task info
        task_info = self.task_manager.get_task_info(task_id)

        # Verify task info
        assert task_info["id"] == task_id
        assert task_info["status"] == "FAILURE"
        assert "error" in task_info

    @patch("core.task_manager.AsyncResult")
    def test_get_task_info_nonexistent(self, mock_async_result):
        """Test retrieving info for a non-existent task."""
        # Mock Celery AsyncResult
        mock_result = MagicMock()
        mock_result.state = "PENDING"
        mock_async_result.return_value = mock_result

        # Get task info for a non-existent task
        task_info = self.task_manager.get_task_info("nonexistent_task_id")

        # Should return None, not raise an exception
        assert task_info is None
