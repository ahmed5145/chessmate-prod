"""Tests for analysis tasks."""

import json
from unittest.mock import MagicMock, call, patch

import pytest
from core.models import Game, GameAnalysis, Player, Profile
from core.task_manager import TaskManager
from core.tasks import analyze_game, batch_analyze_games
from django.contrib.auth.models import User
from django.utils import timezone


@pytest.fixture
def test_user(db):
    """Create test user with profile."""
    user = User.objects.create(username="testuser", email="test@example.com")
    profile = Profile.objects.create(user=user, chess_com_username="testuser", lichess_username="testuser", credits=100)
    return user


@pytest.fixture
def test_game(db, test_user):
    """Create a test game."""
    game = Game.objects.create(
        user=test_user,
        platform="lichess",
        white="testuser",
        black="opponent",
        pgn='[Event "Test Game"]\n[Site "https://lichess.org"]\n[White "testuser"]\n[Black "opponent"]\n[Result "1-0"]\n\n1.e4 e5 2.Nf3 Nc6 3.Bb5 a6 4.Ba4 Nf6 5.O-O Be7 6.d3 d6 7.c3 O-O 8.Re1 Nb8 9.Nbd2 Nbd7 10.Nf1 c6 11.Bc2 Qc7 12.Ng3 Re8 13.d4 Bf8 14.Nh4 g6 15.f4 Bg7 16.f5 1-0',
        result="1-0",
    )
    return game


@pytest.mark.django_db
class TestAnalysisTasks:
    """Tests for analysis tasks."""

    def setup_method(self):
        """Set up test data and patches."""
        # Set up patches
        self.stockfish_analyzer_patch = patch("core.tasks.StockfishAnalyzer")
        self.feedback_generator_patch = patch("core.tasks.FeedbackGenerator")
        self.task_manager_patch = patch("core.tasks.TaskManager")
        self.settings_patch = patch("core.tasks.settings")

        # Start patches
        self.mock_stockfish_analyzer = self.stockfish_analyzer_patch.start()
        self.mock_feedback_generator = self.feedback_generator_patch.start()
        self.mock_task_manager = self.task_manager_patch.start()
        self.mock_settings = self.settings_patch.start()

        # Set up mock instances
        self.mock_stockfish_instance = MagicMock()
        self.mock_feedback_instance = MagicMock()
        self.mock_task_manager_instance = MagicMock()

        # Configure mock returns
        self.mock_stockfish_analyzer.return_value = self.mock_stockfish_instance
        self.mock_feedback_generator.return_value = self.mock_feedback_instance
        self.mock_task_manager.return_value = self.mock_task_manager_instance

        # Configure mock settings
        self.mock_settings.ANALYSIS_DEPTH = 20
        self.mock_settings.STOCKFISH_PATH = "/path/to/stockfish"
        self.mock_settings.MAX_POSITIONS_PER_GAME = 300
        self.mock_settings.USE_OPENAI = True

        # Configure stockfish analysis result
        self.mock_analysis_result = {
            "moves": {
                "1": {"move": "e4", "eval": 0.3, "best_move": "e4"},
                "2": {"move": "e5", "eval": 0.2, "best_move": "e5"},
            },
            "positions": {},
            "summary": {
                "accuracy": 95.5,
                "best_move_count": 10,
                "inaccuracies": 1,
                "mistakes": 0,
                "blunders": 0,
            },
        }
        self.mock_stockfish_instance.analyze_game.return_value = self.mock_analysis_result

        # Configure feedback result
        self.mock_feedback_result = {
            "summary": {
                "evaluation": "Strong play with minimal errors",
                "strengths": ["Solid opening", "Good tactical awareness"],
                "weaknesses": ["Time management"],
            },
            "improvement_plan": {
                "tactics": "Practice tactical puzzles",
                "openings": "Study Ruy Lopez variations",
                "endgames": "Focus on rook endgames",
            },
        }
        self.mock_feedback_instance.generate_feedback.return_value = self.mock_feedback_result

    def teardown_method(self):
        """Clean up patches."""
        self.stockfish_analyzer_patch.stop()
        self.feedback_generator_patch.stop()
        self.task_manager_patch.stop()
        self.settings_patch.stop()

    def test_analyze_game_successful(self, test_game, test_user):
        """Test successful game analysis."""
        # Call the task
        result = analyze_game(
            game_id=test_game.id, user_id=test_user.id, stockfish_path="/path/to/stockfish", depth=20, use_ai=True
        )

        # Check that StockfishAnalyzer was initialized and used
        self.mock_stockfish_analyzer.assert_called_once()
        self.mock_stockfish_instance.analyze_game.assert_called_once()

        # Check that FeedbackGenerator was initialized and used
        self.mock_feedback_generator.assert_called_once()
        self.mock_feedback_instance.generate_feedback.assert_called_once()

        # Check that TaskManager was used to update status
        self.mock_task_manager_instance.update_task_status.assert_called()

        # Check the result
        assert result["status"] == "success"
        assert "analysis" in result
        assert "feedback" in result
        assert result["analysis"] == self.mock_analysis_result
        assert result["feedback"] == self.mock_feedback_result

        # Check that GameAnalysis was created
        analysis = GameAnalysis.objects.filter(game=test_game).first()
        assert analysis is not None
        assert analysis.moves_analysis == self.mock_analysis_result["moves"]
        assert analysis.summary == self.mock_analysis_result["summary"]
        assert analysis.feedback == self.mock_feedback_result

    def test_analyze_game_nonexistent_game(self, test_user):
        """Test analysis with non-existent game ID."""
        # Call the task with a non-existent game ID
        result = analyze_game(game_id=999999, user_id=test_user.id, stockfish_path="/path/to/stockfish", depth=20)

        # Check that the result indicates failure
        assert result["status"] == "error"
        assert "error" in result
        assert "Game not found" in result["error"]

        # Check that task status was updated
        self.mock_task_manager_instance.update_task_status.assert_called()

    def test_analyze_game_with_stockfish_error(self, test_game, test_user):
        """Test analysis with Stockfish error."""
        # Configure Stockfish to raise an exception
        self.mock_stockfish_instance.analyze_game.side_effect = Exception("Stockfish error")

        # Call the task
        result = analyze_game(game_id=test_game.id, user_id=test_user.id, stockfish_path="/path/to/stockfish", depth=20)

        # Check that the result indicates failure
        assert result["status"] == "error"
        assert "error" in result
        assert "Stockfish error" in result["error"]

        # Check that task status was updated
        self.mock_task_manager_instance.update_task_status.assert_called()

    def test_analyze_game_without_ai(self, test_game, test_user):
        """Test analysis without AI feedback."""
        # Call the task with use_ai=False
        result = analyze_game(
            game_id=test_game.id, user_id=test_user.id, stockfish_path="/path/to/stockfish", depth=20, use_ai=False
        )

        # Check that StockfishAnalyzer was used
        self.mock_stockfish_instance.analyze_game.assert_called_once()

        # Check that FeedbackGenerator was NOT used
        self.mock_feedback_instance.generate_feedback.assert_not_called()

        # Check the result
        assert result["status"] == "success"
        assert "analysis" in result
        assert "feedback" not in result

    def test_batch_analyze_games(self, test_game, test_user):
        """Test batch analysis of multiple games."""
        # Create a second game
        game2 = Game.objects.create(
            user=test_user,
            platform="chess.com",
            white="testuser",
            black="opponent2",
            pgn='[Event "Test Game 2"]\n1. d4 d5 2. c4 e6',
            result="draw",
        )

        # Mock analyze_game to return success for both games
        with patch("core.tasks.analyze_game") as mock_analyze_game:
            mock_analyze_game.side_effect = [
                {"status": "success", "game_id": test_game.id, "analysis": {}},
                {"status": "success", "game_id": game2.id, "analysis": {}},
            ]

            # Call the batch task
            result = batch_analyze_games(
                game_ids=[test_game.id, game2.id], user_id=test_user.id, stockfish_path="/path/to/stockfish", depth=20
            )

            # Check that analyze_game was called for each game
            assert mock_analyze_game.call_count == 2

            # Check the result
            assert result["status"] == "success"
            assert "results" in result
            assert len(result["results"]) == 2
            assert result["results"][0]["status"] == "success"
            assert result["results"][1]["status"] == "success"

    def test_batch_analyze_games_with_errors(self, test_game, test_user):
        """Test batch analysis with some errors."""
        # Create a second game
        game2 = Game.objects.create(
            user=test_user,
            platform="chess.com",
            white="testuser",
            black="opponent2",
            pgn='[Event "Test Game 2"]\n1. d4 d5 2. c4 e6',
            result="draw",
        )

        # Mock analyze_game to succeed for first game but fail for second
        with patch("core.tasks.analyze_game") as mock_analyze_game:
            mock_analyze_game.side_effect = [
                {"status": "success", "game_id": test_game.id, "analysis": {}},
                {"status": "error", "game_id": game2.id, "error": "Analysis failed"},
            ]

            # Call the batch task
            result = batch_analyze_games(
                game_ids=[test_game.id, game2.id], user_id=test_user.id, stockfish_path="/path/to/stockfish", depth=20
            )

            # Check that analyze_game was called for each game
            assert mock_analyze_game.call_count == 2

            # Check the result
            assert result["status"] == "partial_success"
            assert "results" in result
            assert len(result["results"]) == 2
            assert result["results"][0]["status"] == "success"
            assert result["results"][1]["status"] == "error"

    def test_batch_analyze_empty_game_list(self, test_user):
        """Test batch analysis with empty game list."""
        # Call the batch task with an empty list
        result = batch_analyze_games(game_ids=[], user_id=test_user.id, stockfish_path="/path/to/stockfish", depth=20)

        # Check the result
        assert result["status"] == "error"
        assert "error" in result
        assert "No games specified" in result["error"]
