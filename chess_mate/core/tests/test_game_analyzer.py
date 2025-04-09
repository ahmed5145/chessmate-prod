"""Tests for the GameAnalyzer class."""

import json
from unittest.mock import MagicMock, patch

import pytest
from core.game_analyzer import GameAnalyzer
from core.models import Game, GameAnalysis, Profile, User


@pytest.fixture
def test_user(db):
    """Create a test user with profile."""
    user = User.objects.create(username="testuser", email="test@example.com")
    profile = Profile.objects.create(user=user, chess_com_username="testuser", lichess_username="testuser", credits=100)
    return user


@pytest.fixture
def test_game(db, test_user):
    """Create a test game."""
    return Game.objects.create(
        user=test_user,
        platform="lichess",
        white="testuser",
        black="opponent",
        pgn="""
[Event "Test Game"]
[Site "https://lichess.org"]
[White "testuser"]
[Black "opponent"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O
9. h3 Nb8 10. d4 Nbd7 11. c4 c6 12. Nc3 exd4 13. Nxd4 Nc5 14. Bc2 Qb6 1-0
""",
        result="1-0",
    )


@pytest.mark.django_db
class TestGameAnalyzer:
    """Tests for the GameAnalyzer class."""

    def setup_method(self):
        """Set up test data and mocks."""
        # Mock the StockfishAnalyzer
        self.stockfish_patch = patch("core.analysis.stockfish_analyzer.StockfishAnalyzer")
        self.mock_stockfish_class = self.stockfish_patch.start()
        self.mock_stockfish = MagicMock()
        self.mock_stockfish_class.get_instance.return_value = self.mock_stockfish

        # Mock the FeedbackGenerator
        self.feedback_patch = patch("core.analysis.feedback_generator.FeedbackGenerator")
        self.mock_feedback_class = self.feedback_patch.start()
        self.mock_feedback = MagicMock()
        self.mock_feedback_class.return_value = self.mock_feedback

        # Mock TaskManager
        self.task_manager_patch = patch("core.task_manager.TaskManager")
        self.mock_task_manager_class = self.task_manager_patch.start()
        self.mock_task_manager = MagicMock()
        self.mock_task_manager_class.return_value = self.mock_task_manager

        # Mock OpenAI
        self.openai_patch = patch("core.game_analyzer.OpenAI")
        self.mock_openai_class = self.openai_patch.start()
        self.mock_openai = MagicMock()
        self.mock_openai_class.return_value = self.mock_openai

        # Set up expected results
        self.analysis_result = {
            "moves": {
                "1": {"move": "e4", "eval": 0.3, "best_move": "e4"},
                "2": {"move": "e5", "eval": 0.2, "best_move": "e5"},
            },
            "summary": {
                "accuracy": 95.5,
                "best_move_count": 10,
                "inaccuracies": 1,
                "mistakes": 0,
                "blunders": 0,
            },
        }

        self.feedback_result = {
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

        # Configure mocks to return expected results
        self.mock_stockfish.analyze_game.return_value = self.analysis_result
        self.mock_feedback.generate_feedback.return_value = self.feedback_result

    def teardown_method(self):
        """Clean up patches."""
        self.stockfish_patch.stop()
        self.feedback_patch.stop()
        self.task_manager_patch.stop()
        self.openai_patch.stop()

    def test_initialization(self):
        """Test that GameAnalyzer is initialized correctly."""
        analyzer = GameAnalyzer()

        # Check that dependencies were properly initialized
        self.mock_stockfish_class.get_instance.assert_called_once()
        self.mock_feedback_class.assert_called_once()
        self.mock_task_manager_class.assert_called_once()
        self.mock_openai_class.assert_called_once()

        # Check that dependencies are properly assigned
        assert analyzer.engine == self.mock_stockfish
        assert analyzer.feedback_generator == self.mock_feedback
        assert analyzer.task_manager == self.mock_task_manager

    def test_analyze_game_with_ai(self, test_game):
        """Test analyzing a game with AI feedback."""
        analyzer = GameAnalyzer()

        # Call the method
        result = analyzer.analyze_game(test_game, depth=20, use_ai=True)

        # Check that the engine was called correctly
        self.mock_stockfish.analyze_game.assert_called_once_with(test_game.pgn, depth=20)

        # Check that the feedback generator was called correctly
        self.mock_feedback.generate_feedback.assert_called_once()

        # Check the result
        assert result["analysis"] == self.analysis_result
        assert result["feedback"] == self.feedback_result

    def test_analyze_game_without_ai(self, test_game):
        """Test analyzing a game without AI feedback."""
        analyzer = GameAnalyzer()

        # Call the method
        result = analyzer.analyze_game(test_game, depth=20, use_ai=False)

        # Check that the engine was called
        self.mock_stockfish.analyze_game.assert_called_once()

        # Check that the feedback generator was not called
        self.mock_feedback.generate_feedback.assert_not_called()

        # Check the result
        assert result["analysis"] == self.analysis_result
        assert "feedback" not in result

    def test_analyze_game_handles_errors(self, test_game):
        """Test that analyze_game handles errors gracefully."""
        # Configure the engine to raise an exception
        self.mock_stockfish.analyze_game.side_effect = Exception("Test error")

        analyzer = GameAnalyzer()

        # Call the method
        result = analyzer.analyze_game(test_game)

        # Check the result
        assert "error" in result
        assert "Test error" in result["error"]

    def test_save_analysis(self, test_game):
        """Test saving analysis results to the database."""
        analyzer = GameAnalyzer()

        # Call the method
        analysis = analyzer.save_analysis(test_game, self.analysis_result, self.feedback_result)

        # Check that a GameAnalysis was created with the correct data
        assert isinstance(analysis, GameAnalysis)
        assert analysis.game == test_game
        assert analysis.moves_analysis == self.analysis_result["moves"]
        assert analysis.summary == self.analysis_result["summary"]
        assert analysis.feedback == self.feedback_result

        # Verify it was saved to the database
        saved_analysis = GameAnalysis.objects.get(game=test_game)
        assert saved_analysis == analysis

    def test_get_analysis_existing(self, test_game):
        """Test retrieving analysis for a game that has already been analyzed."""
        # Create an analysis record
        analysis = GameAnalysis.objects.create(
            game=test_game,
            moves_analysis=self.analysis_result["moves"],
            summary=self.analysis_result["summary"],
            feedback=self.feedback_result,
        )

        analyzer = GameAnalyzer()

        # Call the method
        result = analyzer.get_analysis(test_game)

        # Check the result
        assert result is not None
        assert result["analysis"]["moves"] == self.analysis_result["moves"]
        assert result["analysis"]["summary"] == self.analysis_result["summary"]
        assert result["feedback"] == self.feedback_result

    def test_get_analysis_nonexistent(self, test_game):
        """Test retrieving analysis for a game that hasn't been analyzed."""
        analyzer = GameAnalyzer()

        # Call the method
        result = analyzer.get_analysis(test_game)

        # Check the result
        assert result is None

    def test_analyze_batch_games(self, test_game, test_user):
        """Test analyzing multiple games in batch."""
        # Create a second game
        game2 = Game.objects.create(
            user=test_user,
            platform="chess.com",
            white="testuser",
            black="opponent2",
            pgn='[Event "Test Game 2"]\n1. d4 d5 2. c4 e6',
            result="draw",
        )

        analyzer = GameAnalyzer()

        # Mock analyze_game to track calls and return predetermined results
        with patch.object(analyzer, "analyze_game") as mock_analyze_game:
            mock_analyze_game.side_effect = [
                {"analysis": self.analysis_result, "feedback": self.feedback_result},
                {"analysis": {"summary": {"accuracy": 85.0}}, "feedback": {}},
            ]

            # Call the method
            results = analyzer.analyze_batch_games([test_game, game2], depth=20, use_ai=True)

            # Check that analyze_game was called for each game
            assert mock_analyze_game.call_count == 2
            mock_analyze_game.assert_any_call(test_game, depth=20, use_ai=True)
            mock_analyze_game.assert_any_call(game2, depth=20, use_ai=True)

            # Check the results
            assert len(results) == 2
            assert results[0]["analysis"] == self.analysis_result
            assert results[0]["feedback"] == self.feedback_result
            assert results[1]["analysis"]["summary"]["accuracy"] == 85.0
