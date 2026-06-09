"""
Tests for batch analysis views (PRD section 11, Step 9).
"""

import uuid
from unittest.mock import MagicMock, Mock, patch

import pytest
from core.models import BatchAnalysisReport, Profile
from core.tests.profile_helpers import ensure_profile
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


class TestBatchViews(TestCase):
    """Test batch analysis API endpoints."""

    def setUp(self):
        """Create test user and API client."""
        self.user = User.objects.create_user(username="testuser", password="testpass")
        ensure_profile(self.user, credits=100)
        self.client = APIClient()

        # Generate JWT token for authentication
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

        # Authenticate client with JWT
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")

    def test_get_batch_list_returns_user_reports(self):
        """GET /api/v1/batches/ returns newest batches for the authenticated user."""
        other_user = User.objects.create_user(username="listother", password="pass")
        BatchAnalysisReport.objects.create(
            user=other_user,
            task_id="other-task",
            status="completed",
            games_count=5,
        )
        mine_old = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="mine-old",
            status="completed",
            games_count=5,
            coaching_report={"executive_summary": "Older batch insight."},
            batch_summary={"overall_accuracy_pct": 72.5},
        )
        mine_new = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="mine-new",
            status="partial",
            games_count=10,
            coaching_report={"executive_summary": "Latest batch insight."},
            batch_summary={"overall_accuracy_pct": 81.2},
        )

        response = self.client.get("/api/v1/batches/?limit=10")

        assert response.status_code == 200
        assert response.data["count"] == 2
        assert len(response.data["results"]) == 2
        assert response.data["results"][0]["id"] == mine_new.id
        assert response.data["results"][1]["id"] == mine_old.id
        assert response.data["results"][0]["coach_summary"] == "Latest batch insight."
        assert response.data["results"][0]["overall_accuracy_pct"] == 81.2

    def test_get_batch_compare_vs_previous(self):
        older = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="older-batch",
            status="completed",
            games_count=5,
            batch_summary={
                "recurring_weaknesses": [{"pattern": "hanging_piece"}],
                "overall_accuracy_pct": 70.0,
                "overall_eval_stability": 0.8,
            },
        )
        newer = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="newer-batch",
            status="completed",
            games_count=5,
            batch_summary={
                "recurring_weaknesses": [
                    {"pattern": "hanging_piece"},
                    {"pattern": "fork"},
                ],
                "overall_accuracy_pct": 75.0,
                "overall_eval_stability": 0.85,
            },
        )

        response = self.client.get(
            f"/api/v1/batches/{newer.id}/compare/?other=previous"
        )

        assert response.status_code == 200
        assert response.data["other_batch_id"] == older.id
        assert "hanging_piece" in response.data["weaknesses"]["persisting"]
        assert "fork" in response.data["weaknesses"]["new"]
        assert response.data["metrics"]["overall_accuracy_pct_delta"] == 5.0
        assert isinstance(response.data.get("narrative"), str)
        assert len(response.data["narrative"]) > 10

    def test_post_batch_share_enables_public_link(self):
        batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="share-task",
            status="completed",
            games_count=5,
            batch_summary={"games_analyzed": 5},
            per_game_results=[{"game_id": "game_0", "saved_game_id": 99}],
            coaching_report={"executive_summary": "Test"},
        )

        response = self.client.post(f"/api/v1/batches/{batch.id}/share/")
        assert response.status_code == 200
        assert response.data["shared"] is True
        assert response.data["share_token"]

        batch.refresh_from_db()
        assert batch.share_token is not None

        client = APIClient()
        public = client.get(f"/api/v1/batches/public/{batch.share_token}/report/")
        assert public.status_code == 200
        assert public.data["games_count"] == 5
        assert public.data["per_game_results"][0].get("saved_game_id") is None

    def test_delete_batch_share_revokes_link(self):
        token = uuid.uuid4()
        batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="revoke-task",
            status="completed",
            games_count=5,
            share_token=token,
            batch_summary={"games_analyzed": 5},
            per_game_results=[],
        )

        response = self.client.delete(f"/api/v1/batches/{batch.id}/share/")
        assert response.status_code == 200

        batch.refresh_from_db()
        assert batch.share_token is None

        client = APIClient()
        public = client.get(f"/api/v1/batches/public/{token}/report/")
        assert public.status_code == 404

    def test_get_batch_list_requires_auth(self):
        client = APIClient()
        response = client.get("/api/v1/batches/")
        assert response.status_code in [401, 403]

    def test_post_batch_create_returns_202(self):
        """POST /api/v1/batches/ creates batch and returns 202."""
        pgn_data = [
            '[Event "Test 1"]\n1.e4 e5',
            '[Event "Test 2"]\n1.d4 d5',
            '[Event "Test 3"]\n1.c4 c5',
            '[Event "Test 4"]\n1.Nf3 Nf6',
            '[Event "Test 5"]\n1.g4 g5',
        ]

        with patch("core.serializers_batches.chess.pgn.read_game") as mock_parse:
            mock_parse.return_value = Mock()

            with patch("core.views_batches.analyze_batch_task.delay") as mock_task:
                mock_task.return_value = Mock(id="celery-task-123")

                response = self.client.post(
                    "/api/v1/batches/",
                    {"games": pgn_data},
                    format="json",
                )

        assert response.status_code == 202
        assert "batch_id" in response.data
        assert "task_id" in response.data
        assert response.data["status"] == "pending"
        assert response.data["games_count"] == 5

        # Verify batch was created in database
        batch = BatchAnalysisReport.objects.get(id=response.data["batch_id"])
        assert batch.user == self.user
        assert batch.status == "pending"
        assert batch.games_count == 5

        # Verify task was queued
        mock_task.assert_called_once()

    def test_get_batch_status_returns_progress(self):
        """GET /api/v1/batches/{id}/status/ returns correct progress."""
        # Create a batch in progress
        batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="task-123",
            status="in_progress",
            games_count=10,
            completed_games=["game_1", "game_2", "game_3"],
            failed_games=[{"game_id": "game_4", "error": "Timeout"}],
        )

        response = self.client.get(f"/api/v1/batches/{batch.id}/status/")

        assert response.status_code == 200
        assert response.data["batch_id"] == batch.id
        assert response.data["task_id"] == "task-123"
        assert response.data["status"] == "in_progress"
        assert response.data["games_count"] == 10
        assert response.data["completed_games"] == 3
        assert response.data["failed_games"] == 1
        assert response.data["progress"] == "3/10 games analyzed"
        assert len(response.data["errors"]) == 1
        assert response.data["errors"][0]["game_id"] == "game_4"
        assert response.data["errors"][0]["message"] == "Timeout"

    def test_get_batch_status_404_wrong_user(self):
        """GET /api/v1/batches/{id}/status/ returns 404 for wrong user."""
        other_user = User.objects.create_user(username="otheruser", password="pass")
        batch = BatchAnalysisReport.objects.create(
            user=other_user,
            task_id="task-456",
            status="pending",
            games_count=5,
        )

        response = self.client.get(f"/api/v1/batches/{batch.id}/status/")

        assert response.status_code == 404

    def test_get_batch_report_202_while_in_progress(self):
        """GET /api/v1/batches/{id}/report/ returns 202 while analysis in progress."""
        batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="task-789",
            status="in_progress",
            games_count=5,
        )

        response = self.client.get(f"/api/v1/batches/{batch.id}/report/")

        assert response.status_code == 202
        assert response.data["status"] == "in_progress"
        assert "Analysis in progress" in response.data["message"]

    def test_get_batch_report_202_pending(self):
        """GET /api/v1/batches/{id}/report/ returns 202 while pending."""
        batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="task-pending",
            status="pending",
            games_count=5,
        )

        response = self.client.get(f"/api/v1/batches/{batch.id}/report/")

        assert response.status_code == 202
        assert response.data["status"] == "pending"

    def test_get_batch_report_failed(self):
        """GET /api/v1/batches/{id}/report/ returns failed message on failure."""
        batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="task-failed",
            status="failed",
            games_count=3,  # Less than 5
        )

        response = self.client.get(f"/api/v1/batches/{batch.id}/report/")

        assert response.status_code == 200
        assert response.data["status"] == "failed"
        assert "insufficient games succeeded" in response.data["message"]

    def test_get_batch_report_completed(self):
        """GET /api/v1/batches/{id}/report/ returns full report when completed."""
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

        batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="task-completed",
            status="completed",
            games_count=5,
            batch_summary=batch_summary,
            per_game_results=per_game_results,
            coaching_report=coaching_report,
        )

        response = self.client.get(f"/api/v1/batches/{batch.id}/report/")

        assert response.status_code == 200
        assert response.data["status"] == "completed"
        assert response.data["batch_summary"] == batch_summary
        assert response.data["per_game_results"] == per_game_results
        assert response.data["coaching_report"] == coaching_report

    def test_get_batch_report_partial(self):
        """GET /api/v1/batches/{id}/report/ returns report for partial status."""
        batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="task-partial",
            status="partial",
            games_count=5,
            batch_summary={"games_analyzed": 5},
        )

        response = self.client.get(f"/api/v1/batches/{batch.id}/report/")

        assert response.status_code == 200
        assert response.data["status"] == "partial"

    def test_get_batch_report_includes_failed_games_and_errors(self):
        """GET report includes per-game failure details for the results UI."""
        failed_games = [
            {"game_id": "game_2", "error": "Invalid PGN"},
            {"game_id": "game_7", "error": "Stockfish timeout"},
        ]
        batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="task-failures",
            status="partial",
            games_count=10,
            batch_summary={"games_analyzed": 8},
            per_game_results=[{"game_id": "game_0"}],
            coaching_report={"executive_summary": "OK"},
            failed_games=failed_games,
        )

        response = self.client.get(f"/api/v1/batches/{batch.id}/report/")

        assert response.status_code == 200
        assert response.data["failed_games"] == failed_games
        assert len(response.data["errors"]) == 2
        assert response.data["errors"][0]["message"] == "Invalid PGN"
        assert response.data["errors"][1]["game_id"] == "game_7"

    def test_get_batch_report_404_wrong_user(self):
        """GET /api/v1/batches/{id}/report/ returns 404 for wrong user."""
        other_user = User.objects.create_user(username="otheruser2", password="pass")
        batch = BatchAnalysisReport.objects.create(
            user=other_user,
            task_id="task-other",
            status="completed",
            games_count=5,
        )

        response = self.client.get(f"/api/v1/batches/{batch.id}/report/")

        assert response.status_code == 404

    def test_post_regenerate_coaching_success(self):
        """POST regenerate-coaching reuses frozen analysis and updates coaching_report."""
        batch_summary = {
            "games_analyzed": 5,
            "player_rating": 1500,
            "opening_insights": [{"opening_name": "Italian Game", "status": "strong"}],
        }
        per_game_results = [
            {"game_id": f"game_{i}", "total_moves": 40} for i in range(5)
        ]
        batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="task-regen",
            status="partial",
            games_count=5,
            batch_summary=batch_summary,
            per_game_results=per_game_results,
            coaching_report=None,
        )

        new_coaching = {
            "executive_summary": "Updated summary",
            "coaching_narrative": {"opening": "O", "middlegame": "M", "endgame": "E"},
            "top_3_priorities": [
                {
                    "rank": 1,
                    "title": "game_0 move 12",
                    "why_it_matters": "W",
                    "how_to_fix": "H",
                    "specific_drill": "Drill game_0 move 12",
                    "estimated_study_hours": 1,
                },
                {
                    "rank": 2,
                    "title": "T2",
                    "why_it_matters": "W2",
                    "how_to_fix": "H2",
                    "specific_drill": "D2",
                    "estimated_study_hours": 1,
                },
                {
                    "rank": 3,
                    "title": "T3",
                    "why_it_matters": "W3",
                    "how_to_fix": "H3",
                    "specific_drill": "D3",
                    "estimated_study_hours": 1,
                },
            ],
            "training_plan": {
                "week_1": "w1",
                "week_2": "w2",
                "week_3": "w3",
                "week_4": "w4",
            },
            "one_thing_to_do_today": "Practice",
        }

        with patch(
            "core.batch_coaching.generate_coaching_report", return_value=new_coaching
        ):
            response = self.client.post(
                f"/api/v1/batches/{batch.id}/regenerate-coaching/"
            )

        assert response.status_code == 200
        assert response.data["coaching_report"] == new_coaching
        assert response.data["status"] == "completed"

        batch.refresh_from_db()
        assert batch.coaching_report == new_coaching
        assert batch.status == "completed"

    def test_post_regenerate_coaching_rejects_pending(self):
        batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="task-pending-regen",
            status="in_progress",
            games_count=5,
        )
        response = self.client.post(f"/api/v1/batches/{batch.id}/regenerate-coaching/")
        assert response.status_code == 400

    def test_post_batch_unauthenticated(self):
        """POST /api/v1/batches/ requires JWT authentication."""
        client = APIClient()  # No auth
        pgn_data = [f'[Event "Test {i}"]\n1.e4 e5' for i in range(5)]

        response = client.post(
            "/api/v1/batches/",
            {"games": pgn_data},
            format="json",
        )

        assert response.status_code in [
            401,
            403,
        ]  # Auth required (401 or 403 per middleware)

    def test_get_status_unauthenticated(self):
        """GET /api/v1/batches/{id}/status/ requires JWT authentication."""
        batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="task-auth",
            status="pending",
            games_count=5,
        )

        client = APIClient()  # No auth
        response = client.get(f"/api/v1/batches/{batch.id}/status/")

        assert response.status_code in [
            401,
            403,
        ]  # Auth required (401 or 403 per middleware)

    def test_get_report_unauthenticated(self):
        """GET /api/v1/batches/{id}/report/ requires JWT authentication."""
        batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="task-auth2",
            status="pending",
            games_count=5,
        )

        client = APIClient()  # No auth
        response = client.get(f"/api/v1/batches/{batch.id}/report/")

        assert response.status_code in [
            401,
            403,
        ]  # Auth required (401 or 403 per middleware)

    def test_post_batch_invalid_pgn(self):
        """POST /api/v1/batches/ rejects invalid PGN."""
        pgn_data = [f'[Event "Test {i}"]\n1.e4 e5' for i in range(3)]  # Only 3

        with patch("core.serializers_batches.chess.pgn.read_game") as mock_parse:
            mock_parse.return_value = Mock()

            response = self.client.post(
                "/api/v1/batches/",
                {"games": pgn_data},
                format="json",
            )

        assert response.status_code == 400
        assert "at least 5 games" in str(response.data).lower()
