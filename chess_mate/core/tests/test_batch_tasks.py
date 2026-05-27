"""
Tests for Phase 1 batch analysis Celery tasks.
"""
from unittest.mock import MagicMock, Mock, patch

import pytest
from core.models import BatchAnalysisReport
from core.tasks import (
    aggregate_and_report_task,
    analyze_batch_task,
    analyze_single_game_subtask,
)
from django.contrib.auth.models import User
from django.test import TestCase


class TestAnalyzeSingleGameSubtask(TestCase):
    """Test analyze_single_game_subtask exception handling."""

    def test_subtask_success(self):
        """Subtask returns success envelope with result."""
        pgn = "[Event \"Test\"]\n1.e4 e5 2.Nf3 Nc6"
        game_id = "test_game_1"
        batch_id = "batch_001"
        user_id = 1

        with patch("core.tasks.build_game_result") as mock_build:
            mock_result = {"game_id": "test_game_1", "total_moves": 4}
            mock_build.return_value = mock_result

            result = analyze_single_game_subtask(pgn, game_id, batch_id, user_id)

            assert result["game_id"] == "test_game_1"
            assert result["status"] == "success"
            assert result["result"] == mock_result
            mock_build.assert_called_once_with(pgn, game_id=game_id)

    def test_subtask_exception_handling(self):
        """Subtask catches exceptions and returns failed envelope."""
        pgn = "[Event \"Bad PGN\"]"
        game_id = "test_game_bad"
        batch_id = "batch_001"
        user_id = 1

        with patch("core.tasks.build_game_result") as mock_build:
            mock_build.side_effect = ValueError("Invalid PGN")

            result = analyze_single_game_subtask(pgn, game_id, batch_id, user_id)

            assert result["game_id"] == "test_game_bad"
            assert result["status"] == "failed"
            assert "Invalid PGN" in result["error"]

    def test_subtask_empty_result(self):
        """Subtask handles empty result from build_game_result."""
        pgn = "[Event \"Test\"]"
        game_id = "test_game_empty"
        batch_id = "batch_001"
        user_id = 1

        with patch("core.tasks.build_game_result") as mock_build:
            mock_build.return_value = None

            result = analyze_single_game_subtask(pgn, game_id, batch_id, user_id)

            assert result["game_id"] == "test_game_empty"
            assert result["status"] == "failed"
            assert "empty output" in result["error"]


class TestAggregateAndReportTask(TestCase):
    """Test aggregate_and_report_task chord callback."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(username="testuser", password="testpass")

    def test_all_games_succeed_status_completed(self):
        """All games succeed → status=completed, coaching called once."""
        batch_id = "batch_001"
        user_id = self.user.id
        game_pgn_list = ["pgn1", "pgn2", "pgn3", "pgn4", "pgn5"]

        # Create 5 successful task results
        task_results = [
            {
                "game_id": f"game_{i}",
                "status": "success",
                "result": {
                    "game_id": f"game_{i}",
                    "total_moves": 10 + i,
                    "phase_breakdown": {
                        "opening": {"moves": 4},
                        "middlegame": {"moves": 4},
                        "endgame": {"moves": 2 + i},
                    },
                },
            }
            for i in range(5)
        ]

        with patch("core.tasks.aggregate_batch") as mock_agg:
            with patch("core.tasks.generate_coaching_report") as mock_coach:
                mock_agg.return_value = {"games_analyzed": 5}
                mock_coach.return_value = {"executive_summary": "Good"}

                result = aggregate_and_report_task(
                    task_results, batch_id, game_pgn_list, user_id
                )

                # Verify coaching was called once
                assert mock_coach.call_count == 1

                # Verify result status
                assert result["status"] == "completed"
                assert result["games_analyzed"] == 5
                assert result["games_failed"] == 0

                # Verify BatchAnalysisReport was updated
                batch_report = BatchAnalysisReport.objects.get(task_id=batch_id)
                assert batch_report.status == "completed"
                assert batch_report.batch_summary == {"games_analyzed": 5}
                assert batch_report.coaching_report == {"executive_summary": "Good"}
                assert batch_report.games_count == 5
                assert len(batch_report.completed_games) == 5
                assert len(batch_report.failed_games) == 0

    def test_partial_success_status_partial(self):
        """7 games succeed, 3 fail (≥5 succeeded) → status=partial."""
        batch_id = "batch_002"
        user_id = self.user.id
        game_pgn_list = ["pgn" + str(i) for i in range(10)]

        # 7 successful, 3 failed
        task_results = [
            {
                "game_id": f"game_{i}",
                "status": "success",
                "result": {"game_id": f"game_{i}"},
            }
            for i in range(7)
        ] + [
            {
                "game_id": f"game_{i}",
                "status": "failed",
                "error": "Analysis error",
            }
            for i in range(7, 10)
        ]

        with patch("core.tasks.aggregate_batch") as mock_agg:
            with patch("core.tasks.generate_coaching_report") as mock_coach:
                mock_agg.return_value = {"games_analyzed": 7}
                mock_coach.return_value = {"executive_summary": "Good"}

                result = aggregate_and_report_task(
                    task_results, batch_id, game_pgn_list, user_id
                )

                # Verify status is partial
                assert result["status"] == "partial"
                assert result["games_analyzed"] == 7
                assert result["games_failed"] == 3

                # Verify coaching was called (≥5 succeeded)
                assert mock_coach.call_count == 1

                # Verify BatchAnalysisReport
                batch_report = BatchAnalysisReport.objects.get(task_id=batch_id)
                assert batch_report.status == "partial"
                assert batch_report.games_count == 10
                assert len(batch_report.completed_games) == 7
                assert len(batch_report.failed_games) == 3

    def test_insufficient_success_status_failed(self):
        """Only 4 games succeed (< 5) → status=failed, no coaching call."""
        batch_id = "batch_003"
        user_id = self.user.id
        game_pgn_list = ["pgn" + str(i) for i in range(10)]

        # Only 4 successful
        task_results = [
            {
                "game_id": f"game_{i}",
                "status": "success",
                "result": {"game_id": f"game_{i}"},
            }
            for i in range(4)
        ] + [
            {
                "game_id": f"game_{i}",
                "status": "failed",
                "error": "Analysis error",
            }
            for i in range(4, 10)
        ]

        with patch("core.tasks.aggregate_batch") as mock_agg:
            with patch("core.tasks.generate_coaching_report") as mock_coach:
                result = aggregate_and_report_task(
                    task_results, batch_id, game_pgn_list, user_id
                )

                # Verify status is failed
                assert result["status"] == "failed"
                assert result["successful_count"] == 4

                # Verify coaching was NOT called (< 5 succeeded)
                assert mock_coach.call_count == 0

                # Verify BatchAnalysisReport
                batch_report = BatchAnalysisReport.objects.get(task_id=batch_id)
                assert batch_report.status == "failed"
                assert batch_report.games_count == 0  # Not updated on early exit
                assert batch_report.per_game_results is not None

    def test_coaching_generation_failure_returns_partial_with_data(self):
        """Coaching generation failure -> status=partial with batch_summary & per_game_results saved."""
        from core.analysis.coaching_generator import CoachingGeneratorError

        batch_id = "batch_coaching_fail"
        user_id = self.user.id
        game_pgn_list = ["pgn1", "pgn2", "pgn3", "pgn4", "pgn5"]

        # Create 5 successful task results
        task_results = [
            {
                "game_id": f"game_{i}",
                "status": "success",
                "result": {
                    "game_id": f"game_{i}",
                    "total_moves": 10 + i,
                    "phase_breakdown": {
                        "opening": {"moves": 4, "avg_eval_drop": 0.1},
                        "middlegame": {"moves": 4, "avg_eval_drop": 0.2},
                        "endgame": {"moves": 2 + i, "avg_eval_drop": 0.05},
                    },
                    "move_quality": {"blunder": 0, "mistake": 1, "inaccuracy": 2},
                },
            }
            for i in range(5)
        ]

        with patch("core.tasks.aggregate_batch") as mock_agg:
            with patch("core.tasks.generate_coaching_report") as mock_coach:
                mock_agg.return_value = {"games_analyzed": 5, "overall_accuracy": 0.85}
                mock_coach.side_effect = CoachingGeneratorError("OpenAI API timeout")

                result = aggregate_and_report_task(
                    task_results, batch_id, game_pgn_list, user_id
                )

                assert result["status"] == "partial"
                assert result["batch_id"] == batch_id
                assert result["games_analyzed"] == 5
                assert mock_coach.call_count == 1

                batch_report = BatchAnalysisReport.objects.get(task_id=batch_id)
                assert batch_report.status == "partial"
                assert batch_report.batch_summary is not None
                assert batch_report.batch_summary["games_analyzed"] == 5
                assert batch_report.per_game_results is not None
                assert len(batch_report.per_game_results) == 5
                assert batch_report.coaching_report is None


class TestAnalyzeBatchTask(TestCase):
    """Test analyze_batch_task group/chord orchestration."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(username="testuser2", password="testpass")

    def test_batch_task_creates_workflow(self):
        """analyze_batch_task creates and returns chord workflow."""
        batch_id = "batch_004"
        user_id = self.user.id
        game_pgn_list = ["pgn1", "pgn2", "pgn3"]

        with patch("core.tasks.chord") as mock_chord:
            with patch("core.tasks.group") as mock_group:
                # Mock the group subtasks (generator)
                mock_group.return_value = MagicMock()

                # Mock the chord workflow — chord(subtasks) returns a callable that takes callback
                mock_chord_instance = MagicMock()
                mock_workflow = MagicMock()
                mock_workflow.id = "workflow_123"
                mock_chord_instance.return_value = mock_workflow
                mock_chord.return_value = mock_chord_instance

                result = analyze_batch_task(batch_id, game_pgn_list, user_id)

                # Verify group was called with 3 subtasks
                assert mock_group.call_count == 1

                # Verify chord was called
                assert mock_chord.call_count == 1
                # Verify the callback was called with the callback
                assert mock_chord_instance.call_count == 1
                # Task returns workflow.id which is the string "workflow_123"
                assert result == "workflow_123"

                # Verify batch report was created with in_progress status
                batch_report = BatchAnalysisReport.objects.get(task_id=batch_id)
                assert batch_report.status == "in_progress"
                assert batch_report.games_count == 3

    def test_batch_task_empty_pgn_list(self):
        """analyze_batch_task handles empty PGN list."""
        batch_id = "batch_005"
        user_id = self.user.id
        game_pgn_list = []

        with patch("core.tasks.chord") as mock_chord:
            with patch("core.tasks.group") as mock_group:
                mock_workflow = MagicMock()
                mock_workflow.id = "workflow_empty"
                mock_chord.return_value = mock_workflow

                result = analyze_batch_task(batch_id, game_pgn_list, user_id)

                # Batch report should still be created
                batch_report = BatchAnalysisReport.objects.get(task_id=batch_id)
                assert batch_report.status == "in_progress"
                assert batch_report.games_count == 0
