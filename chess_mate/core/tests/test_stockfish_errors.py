from unittest.mock import MagicMock, patch

import chess
import pytest
from core.analysis.stockfish_analyzer import StockfishAnalyzer
from core.game_analyzer import GameAnalyzer


@pytest.mark.django_db
class TestStockfishErrors:
    @pytest.fixture(autouse=True)
    def setup(self, stockfish_mock):
        self.stockfish_mock = stockfish_mock
        self.analyzer = StockfishAnalyzer()

    def test_missing_evaluate_position(self, mocker):
        """Test handling of missing evaluate_position method."""
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")

        # Mock the engine to raise AttributeError for evaluate_position
        mock_engine = MagicMock()
        mock_engine.evaluate_position = MagicMock(
            side_effect=AttributeError("'SimpleEngine' object has no attribute 'evaluate_position'")
        )

        with patch("chess.engine.SimpleEngine.popen_uci", return_value=mock_engine):
            # The analyzer should handle this gracefully
            result = self.analyzer.analyze_position(board)
            assert "error" in result
            assert result.get("score", 0) == 0  # Should provide default score

    def test_missing_score_key(self, mocker):
        """Test handling of missing score key in analysis result."""
        board = chess.Board()
        move = chess.Move.from_uci("e2e4")

        # Mock engine to return result without score
        mock_engine = MagicMock()
        mock_engine.analyse.return_value = {"pv": [move], "depth": 20, "nodes": 1000}  # Missing 'score' key

        with patch("chess.engine.SimpleEngine.popen_uci", return_value=mock_engine):
            result = self.analyzer.analyze_position(board)
            assert "error" not in result
            assert result.get("score", 0) == 0  # Should provide default score

    def test_invalid_score_format(self, mocker):
        """Test handling of invalid score format."""
        board = chess.Board()

        # Mock engine to return invalid score format
        mock_engine = MagicMock()
        mock_engine.analyse.return_value = {"score": "invalid", "pv": [], "depth": 20}  # Invalid score format

        with patch("chess.engine.SimpleEngine.popen_uci", return_value=mock_engine):
            result = self.analyzer.analyze_position(board)
            assert result.get("score", 0) == 0  # Should provide default score

    def test_engine_cleanup(self):
        """Test proper engine cleanup."""
        # Create a new analyzer instance
        analyzer = StockfishAnalyzer()

        # Mock the engine
        mock_engine = MagicMock()
        analyzer._engine = mock_engine

        # Call cleanup
        analyzer.cleanup()

        # Verify engine was quit
        mock_engine.quit.assert_called_once()
        assert analyzer._engine is None

    def test_engine_initialization_error(self, mocker):
        """Test handling of engine initialization error."""
        # Mock popen_uci to raise an error
        mock_popen = mocker.patch(
            "chess.engine.SimpleEngine.popen_uci", side_effect=Exception("Failed to initialize engine")
        )

        # Create analyzer - should handle error gracefully
        analyzer = StockfishAnalyzer()
        assert analyzer._engine is None

        # Attempt to analyze should return neutral evaluation
        board = chess.Board()
        result = analyzer.analyze_position(board)
        assert result.get("score", 0) == 0
        assert "error" in result
