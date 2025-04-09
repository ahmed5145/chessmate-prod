"""Tests for the updated GameAnalyzer class."""

import json
from unittest.mock import MagicMock, call, patch

import pytest
from celery.result import AsyncResult
from core.game_analyzer import GameAnalyzer
from core.models import Game, GameAnalysis, Player
from core.task_manager import TaskManager
from django.contrib.auth.models import User
from django.test import TestCase


@pytest.mark.django_db
class TestGameAnalyzer:
    """Tests for the GameAnalyzer class."""

    def setup_method(self):
        """Set up test data before each test method."""
        # Create test user and game
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpassword123")
        self.game = Game.objects.create(
            user=self.user,
            platform="chess.com",
            white="testuser",
            black="opponent",
            pgn='[Event "Test Game"]\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6',
            result="win",
        )

        # Create the GameAnalyzer instance
        self.analyzer = GameAnalyzer()

        # Set up patches
        self.analyze_task_patch = patch("core.game_analyzer.analyze_game")
        self.batch_analyze_task_patch = patch("core.game_analyzer.batch_analyze_games")
        self.task_manager_patch = patch("core.game_analyzer.TaskManager")

        # Start patches
        self.mock_analyze_task = self.analyze_task_patch.start()
        self.mock_batch_analyze_task = self.batch_analyze_task_patch.start()
        self.mock_task_manager = self.task_manager_patch.start()

        # Set up return values
        self.mock_task = MagicMock()
        self.mock_task.id = "test_task_id"
        self.mock_analyze_task.delay.return_value = self.mock_task
        self.mock_batch_analyze_task.delay.return_value = self.mock_task

        # Mock task manager instance
        self.mock_tm_instance = MagicMock()
        self.mock_task_manager.return_value = self.mock_tm_instance

    def teardown_method(self):
        """Clean up after each test method."""
        self.analyze_task_patch.stop()
        self.batch_analyze_task_patch.stop()
        self.task_manager_patch.stop()

    @patch("core.game_analyzer.settings")
    def test_analyze_game_async(self, mock_settings):
        """Test asynchronously analyzing a game."""
        # Set up mock settings
        mock_settings.ANALYSIS_DEPTH = 20
        mock_settings.STOCKFISH_PATH = "/path/to/stockfish"

        # Call the method
        task = self.analyzer.analyze_game_async(game_id=self.game.id, user_id=self.user.id, use_ai=True)

        # Check that the Celery task was called with the correct arguments
        self.mock_analyze_task.delay.assert_called_once()
        args, kwargs = self.mock_analyze_task.delay.call_args
        assert kwargs["game_id"] == self.game.id
        assert kwargs["user_id"] == self.user.id
        assert kwargs["use_ai"] is True
        assert "stockfish_path" in kwargs
        assert "depth" in kwargs

        # Check that the task was returned
        assert task == self.mock_task

    @patch("core.game_analyzer.settings")
    def test_analyze_game_async_with_custom_parameters(self, mock_settings):
        """Test analyzing a game with custom parameters."""
        # Set up mock settings
        mock_settings.ANALYSIS_DEPTH = 20
        mock_settings.STOCKFISH_PATH = "/path/to/stockfish"

        # Call the method with custom parameters
        task = self.analyzer.analyze_game_async(
            game_id=self.game.id,
            user_id=self.user.id,
            use_ai=False,
            depth=30,
            stockfish_path="/custom/path/to/stockfish",
        )

        # Check that the Celery task was called with the correct arguments
        args, kwargs = self.mock_analyze_task.delay.call_args
        assert kwargs["game_id"] == self.game.id
        assert kwargs["user_id"] == self.user.id
        assert kwargs["use_ai"] is False
        assert kwargs["depth"] == 30
        assert kwargs["stockfish_path"] == "/custom/path/to/stockfish"

    def test_analyze_game_async_nonexistent_game(self):
        """Test analyzing a game that doesn't exist."""
        # Call the method with a non-existent game ID
        with pytest.raises(Exception):
            self.analyzer.analyze_game_async(game_id=999999, user_id=self.user.id)

    @patch("core.game_analyzer.settings")
    def test_batch_analyze_games_async(self, mock_settings):
        """Test asynchronously analyzing multiple games."""
        # Set up mock settings
        mock_settings.ANALYSIS_DEPTH = 20
        mock_settings.STOCKFISH_PATH = "/path/to/stockfish"

        # Create another game
        game2 = Game.objects.create(
            user=self.user,
            platform="lichess",
            white="testuser",
            black="opponent2",
            pgn='[Event "Test Game 2"]\n1. d4 d5 2. c4 e6',
            result="loss",
        )

        # Call the method with both game IDs
        game_ids = [self.game.id, game2.id]
        task = self.analyzer.batch_analyze_games_async(game_ids=game_ids, user_id=self.user.id, use_ai=True)

        # Check that the Celery task was called with the correct arguments
        self.mock_batch_analyze_task.delay.assert_called_once()
        args, kwargs = self.mock_batch_analyze_task.delay.call_args
        assert kwargs["game_ids"] == game_ids
        assert kwargs["user_id"] == self.user.id
        assert kwargs["use_ai"] is True
        assert "stockfish_path" in kwargs
        assert "depth" in kwargs

        # Check that the task was returned
        assert task == self.mock_task

    @patch("core.game_analyzer.settings")
    def test_batch_analyze_games_async_with_custom_parameters(self, mock_settings):
        """Test batch analyzing games with custom parameters."""
        # Set up mock settings
        mock_settings.ANALYSIS_DEPTH = 20
        mock_settings.STOCKFISH_PATH = "/path/to/stockfish"

        # Create another game
        game2 = Game.objects.create(
            user=self.user,
            platform="lichess",
            white="testuser",
            black="opponent2",
            pgn='[Event "Test Game 2"]\n1. d4 d5 2. c4 e6',
            result="loss",
        )

        # Call the method with custom parameters
        game_ids = [self.game.id, game2.id]
        task = self.analyzer.batch_analyze_games_async(
            game_ids=game_ids, user_id=self.user.id, use_ai=False, depth=15, stockfish_path="/custom/path/to/stockfish"
        )

        # Check that the Celery task was called with the correct arguments
        args, kwargs = self.mock_batch_analyze_task.delay.call_args
        assert kwargs["game_ids"] == game_ids
        assert kwargs["user_id"] == self.user.id
        assert kwargs["use_ai"] is False
        assert kwargs["depth"] == 15
        assert kwargs["stockfish_path"] == "/custom/path/to/stockfish"

    def test_batch_analyze_games_async_empty_list(self):
        """Test batch analyzing with an empty list of game IDs."""
        # Call the method with an empty list
        with pytest.raises(ValueError):
            self.analyzer.batch_analyze_games_async(game_ids=[], user_id=self.user.id)

    def test_batch_analyze_games_async_nonexistent_games(self):
        """Test batch analyzing with non-existent game IDs."""
        # Call the method with non-existent game IDs
        with pytest.raises(Exception):
            self.analyzer.batch_analyze_games_async(game_ids=[999999, 888888], user_id=self.user.id)

    @patch("core.game_analyzer.settings")
    def test_analyze_game_async_with_openai_integration(self, mock_settings):
        """Test analyzing a game with OpenAI integration."""
        # Set up mock settings
        mock_settings.ANALYSIS_DEPTH = 20
        mock_settings.STOCKFISH_PATH = "/path/to/stockfish"
        mock_settings.USE_OPENAI = True
        mock_settings.OPENAI_API_KEY = "test-api-key"

        # Create the OpenAI mock
        with patch("core.game_analyzer.OpenAI") as mock_openai_class:
            # Set up the mock instance
            mock_openai_instance = MagicMock()
            mock_openai_class.return_value = mock_openai_instance

            # Create a new analyzer with OpenAI
            analyzer = GameAnalyzer()

            # Call the method
            task = analyzer.analyze_game_async(game_id=self.game.id, user_id=self.user.id, use_ai=True)

            # Check that OpenAI was initialized
            mock_openai_class.assert_called_once()

            # Check that the task was returned
            assert task == self.mock_task
