"""Tests for batch credit refunds on hard failure."""

from unittest.mock import patch

from core.batch_credits import refund_batch_credits_on_hard_fail
from core.models import BatchAnalysisReport, Profile
from core.tasks import aggregate_and_report_task
from core.tests.profile_helpers import ensure_profile
from django.contrib.auth.models import User
from django.test import TestCase


class TestBatchCreditRefund(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="refunduser", password="testpass")
        self.profile = ensure_profile(self.user, credits=50)

    def test_refund_on_insufficient_successful_games(self):
        batch_id = "batch_refund_001"
        games = 10
        charged = 10
        self.profile.credits = 40
        self.profile.save(update_fields=["credits"])

        BatchAnalysisReport.objects.create(
            user=self.user,
            task_id=batch_id,
            status="pending",
            games_count=games,
            credits_charged=charged,
        )

        task_results = [
            {
                "game_id": f"game_{i}",
                "status": "success",
                "result": {"game_id": f"game_{i}"},
            }
            for i in range(4)
        ] + [
            {"game_id": f"game_{i}", "status": "failed", "error": "err"}
            for i in range(4, games)
        ]

        with patch("core.tasks.aggregate_batch") as mock_agg:
            with patch("core.tasks.generate_coaching_report") as mock_coach:
                result = aggregate_and_report_task(
                    task_results, batch_id, ["pgn"] * games, self.user.id
                )

        assert result["status"] == "failed"
        mock_agg.assert_not_called()
        mock_coach.assert_not_called()

        self.profile.refresh_from_db()
        assert self.profile.credits == 50

        batch_report = BatchAnalysisReport.objects.get(task_id=batch_id)
        assert batch_report.credits_refunded is True

    def test_refund_is_idempotent(self):
        batch_report = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="batch_refund_002",
            status="failed",
            games_count=5,
            credits_charged=5,
        )
        self.profile.credits = 45
        self.profile.save(update_fields=["credits"])

        assert refund_batch_credits_on_hard_fail(batch_report) == 5
        self.profile.refresh_from_db()
        assert self.profile.credits == 50

        batch_report.refresh_from_db()
        assert refund_batch_credits_on_hard_fail(batch_report) == 0
        self.profile.refresh_from_db()
        assert self.profile.credits == 50

    def test_partial_batch_does_not_refund(self):
        batch_report = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="batch_refund_003",
            status="partial",
            games_count=10,
            credits_charged=10,
        )
        self.profile.credits = 40
        self.profile.save(update_fields=["credits"])

        assert refund_batch_credits_on_hard_fail(batch_report) == 0
        self.profile.refresh_from_db()
        assert self.profile.credits == 40
