"""
Tests for batch analysis serializers.
"""

from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from core.models import BatchAnalysisReport
from core.serializers_batches import (
    BatchAnalysisReportSerializer,
    BatchCreateSerializer,
    BatchStatusSerializer,
)
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIRequestFactory


class TestBatchCreateSerializer(TestCase):
    """Test BatchCreateSerializer validation and processing."""

    def test_rejects_fewer_than_5_games(self):
        """Batch with < 5 games rejected with specific message."""
        pgn_data = [
            '[Event "Test 1"]\n1.e4 e5',
            '[Event "Test 2"]\n1.d4 d5',
            '[Event "Test 3"]\n1.c4 c5',
            '[Event "Test 4"]\n1.Nf3 Nf6',
        ]

        with patch("core.serializers_batches.chess.pgn.read_game") as mock_parse:
            # Mock successful parsing for all games
            mock_parse.return_value = Mock()

            serializer = BatchCreateSerializer(data={"games": pgn_data})

            assert not serializer.is_valid()
            assert "Batch analysis requires at least 5 games to detect patterns." in str(serializer.errors)

    def test_rejects_more_than_30_games(self):
        """Batch with > 30 games rejected with specific message."""
        pgn_data = [f'[Event "Test {i}"]\n1.e4 e5' for i in range(31)]

        with patch("core.serializers_batches.chess.pgn.read_game") as mock_parse:
            mock_parse.return_value = Mock()

            serializer = BatchCreateSerializer(data={"games": pgn_data})

            assert not serializer.is_valid()
            assert "Batch analysis supports a maximum of 30 games." in str(serializer.errors)

    def test_rejects_invalid_pgn_with_index(self):
        """Invalid PGN rejected with index information."""
        pgn_data = [
            '[Event "Test 1"]\n1.e4 e5',
            '[Event "Test 2"]\n1.d4 d5',
            '[Event "Test 3"]\n1.c4 c5',  # This one will fail
            '[Event "Test 4"]\n1.Nf3 Nf6',
            '[Event "Test 5"]\n1.g4 g5',
        ]

        with patch("core.serializers_batches.chess.pgn.read_game") as mock_parse:
            # Parse succeeds for indices 0, 1, fails at 2, succeeds for 3, 4
            def parse_side_effect(pgn_io):
                content = pgn_io.read()
                if "Test 3" in content:
                    return None  # Simulate invalid PGN
                return Mock()

            mock_parse.side_effect = parse_side_effect

            serializer = BatchCreateSerializer(data={"games": pgn_data})

            assert not serializer.is_valid()
            error_str = str(serializer.errors)
            assert "index 2" in error_str
            assert "Invalid or empty PGN" in error_str

    def test_accepts_valid_batch_of_5_games(self):
        """Valid batch of exactly 5 games accepted."""
        pgn_data = [f'[Event "Test {i}"]\n1.e4 e5' for i in range(5)]

        with patch("core.serializers_batches.chess.pgn.read_game") as mock_parse:
            mock_parse.return_value = Mock()

            serializer = BatchCreateSerializer(data={"games": pgn_data})

            assert serializer.is_valid(), serializer.errors
            assert len(serializer.validated_data["pgn_list"]) == 5
            assert serializer.validated_data["pgn_list"] == pgn_data

    def test_accepts_valid_batch_of_30_games(self):
        """Valid batch of exactly 30 games accepted."""
        pgn_data = [f'[Event "Test {i}"]\n1.e4 e5' for i in range(30)]

        with patch("core.serializers_batches.chess.pgn.read_game") as mock_parse:
            mock_parse.return_value = Mock()

            serializer = BatchCreateSerializer(data={"games": pgn_data})

            assert serializer.is_valid(), serializer.errors
            assert len(serializer.validated_data["pgn_list"]) == 30

    def test_accepts_file_upload(self):
        """Batch accepts PGN files."""
        pgn_content = b'[Event "Test 1"]\n1.e4 e5'
        files = [Mock(read=Mock(return_value=pgn_content)) for _ in range(5)]

        with patch("core.serializers_batches.chess.pgn.read_game") as mock_parse:
            mock_parse.return_value = Mock()

            serializer = BatchCreateSerializer(data={"files": files})

            assert serializer.is_valid(), serializer.errors
            assert len(serializer.validated_data["pgn_list"]) == 5

    def test_rejects_invalid_pgn_parse_error(self):
        """Invalid PGN causing parse exception rejected with index."""
        pgn_data = [
            '[Event "Test 1"]\n1.e4 e5',
            '[Event "Test 2"]\n1.d4 d5',
            '[Event "Bad PGN"]',  # This one will fail to parse
            '[Event "Test 4"]\n1.Nf3 Nf6',
            '[Event "Test 5"]\n1.g4 g5',
        ]

        with patch("core.serializers_batches.chess.pgn.read_game") as mock_parse:

            def parse_side_effect(pgn_io):
                content = pgn_io.read()
                if "Bad PGN" in content:
                    raise ValueError("Invalid PGN format")
                return Mock()

            mock_parse.side_effect = parse_side_effect

            serializer = BatchCreateSerializer(data={"games": pgn_data})

            assert not serializer.is_valid()
            error_str = str(serializer.errors)
            assert "index 2" in error_str
            assert "Failed to parse PGN" in error_str


class TestBatchStatusSerializer(TestCase):
    """Test BatchStatusSerializer read-only serialization."""

    def test_serializes_batch_status(self):
        """BatchStatusSerializer serializes status correctly."""
        batch_data = {
            "id": 123,
            "batch_id": "batch_001",
            "task_id": "celery_task_123",
            "status": "completed",
            "games_count": 10,
            "completed_games": ["game_1", "game_2", "game_3", "game_4", "game_5"],
            "failed_games": [
                {"game_id": "game_6", "error": "Analysis timeout"},
                {"game_id": "game_7", "error": "Invalid PGN"},
            ],
        }

        serializer = BatchStatusSerializer(batch_data)
        result = serializer.data

        assert result["batch_id"] == 123
        assert result["task_id"] == "celery_task_123"
        assert result["status"] == "completed"
        assert result["games_count"] == 10
        assert result["completed_games"] == 5  # Count, not list
        assert result["failed_games"] == 2  # Count, not list
        assert result["progress"] == "5/10 games analyzed"

    def test_generates_error_list(self):
        """BatchStatusSerializer generates error list from failed_games."""
        batch_data = {
            "id": 456,
            "task_id": "celery_task_456",
            "status": "partial",
            "games_count": 8,
            "completed_games": ["game_1", "game_2"],
            "failed_games": [
                {"game_id": "game_3", "error": "Timeout"},
                {"game_id": "game_4", "error": "Invalid move"},
                {"game_id": "game_5", "error": "Engine crash"},
            ],
        }

        serializer = BatchStatusSerializer(batch_data)
        result = serializer.data

        assert len(result["errors"]) == 3
        assert result["errors"][0]["game_id"] == "game_3"
        assert result["errors"][0]["message"] == "Timeout"
        assert result["errors"][1]["game_id"] == "game_4"
        assert result["errors"][2]["message"] == "Engine crash"

    def test_handles_empty_failed_games(self):
        """BatchStatusSerializer handles empty failed_games list."""
        batch_data = {
            "id": 789,
            "task_id": "celery_task_789",
            "status": "completed",
            "games_count": 5,
            "completed_games": ["g1", "g2", "g3", "g4", "g5"],
            "failed_games": [],
        }

        serializer = BatchStatusSerializer(batch_data)
        result = serializer.data

        assert result["failed_games"] == 0
        assert result["errors"] == []
        assert result["progress"] == "5/5 games analyzed"


class TestBatchAnalysisReportSerializer(TestCase):
    """Test BatchAnalysisReportSerializer read-only serialization."""

    def setUp(self):
        """Create test user and batch report."""
        self.user = User.objects.create_user(username="testuser", password="testpass")

    def test_serializes_batch_report(self):
        """BatchAnalysisReportSerializer serializes report correctly."""
        batch_summary = {"games_analyzed": 5, "overall_accuracy": 0.88}
        per_game_results = [
            {"game_id": "g1", "total_moves": 40},
            {"game_id": "g2", "total_moves": 35},
        ]
        coaching_report = {
            "executive_summary": "Good performance",
            "coaching_narrative": {
                "opening": "Strong",
                "middlegame": "OK",
                "endgame": "Weak",
            },
        }

        batch_report = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="batch_001",
            status="completed",
            games_count=5,
            batch_summary=batch_summary,
            per_game_results=per_game_results,
            coaching_report=coaching_report,
        )

        serializer = BatchAnalysisReportSerializer(batch_report)
        result = serializer.data

        assert result["id"] == batch_report.id
        assert result["task_id"] == "batch_001"
        assert result["status"] == "completed"
        assert result["games_count"] == 5
        assert result["batch_summary"] == batch_summary
        assert result["per_game_results"] == per_game_results
        assert result["coaching_report"] == coaching_report
        assert "created_at" in result
        assert "updated_at" in result

    def test_serializes_failed_games_and_errors(self):
        """Report serializer exposes failure reasons for the frontend."""
        failed_games = [
            {"game_id": "game_1", "error": "Engine crash"},
            {"game_id": "game_4", "error": "Invalid PGN"},
        ]
        batch_report = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="batch_failures",
            status="partial",
            games_count=6,
            failed_games=failed_games,
        )

        result = BatchAnalysisReportSerializer(batch_report).data

        assert result["failed_games"] == failed_games
        assert len(result["errors"]) == 2
        assert result["errors"][0]["message"] == "Engine crash"
        assert result["errors"][1]["game_id"] == "game_4"

    def test_jsonfield_passthrough(self):
        """JSONFields pass through as-is (dict objects)."""
        complex_summary = {
            "nested": {
                "data": {
                    "with_arrays": [1, 2, 3],
                    "with_strings": "test",
                }
            }
        }

        batch_report = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="batch_002",
            status="completed",
            games_count=5,
            batch_summary=complex_summary,
        )

        serializer = BatchAnalysisReportSerializer(batch_report)
        result = serializer.data

        assert result["batch_summary"] == complex_summary
        assert result["batch_summary"]["nested"]["data"]["with_arrays"] == [1, 2, 3]

    def test_handles_null_jsonfields(self):
        """Serializer handles null JSONFields."""
        batch_report = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="batch_003",
            status="pending",
            games_count=0,
            batch_summary=None,
            per_game_results=None,
            coaching_report=None,
        )

        serializer = BatchAnalysisReportSerializer(batch_report)
        result = serializer.data

        assert result["batch_summary"] is None
        assert result["per_game_results"] is None
        assert result["coaching_report"] is None
