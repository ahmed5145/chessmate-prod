"""Tests for batch fix-rate score (SRG-17)."""

from core.fix_rate import build_dashboard_fix_rate, build_fix_rate_payload
from core.models import BatchAnalysisReport
from core.tests.profile_helpers import ensure_profile
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone


class TestFixRate(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="fixrateuser", password="pass")
        ensure_profile(self.user, credits=10)

    def _batch(self, task_id, weaknesses, priorities=None):
        return BatchAnalysisReport.objects.create(
            user=self.user,
            task_id=task_id,
            status="completed",
            games_count=5,
            coaching_report={
                "top_3_priorities": priorities or [],
            },
            batch_summary={"recurring_weaknesses": weaknesses},
            created_at=timezone.now(),
        )

    def test_hidden_on_first_batch(self):
        self._batch("only", [{"pattern": "hanging_piece", "avg_eval_swing": 1.0}])
        payload = build_dashboard_fix_rate(self.user)
        assert payload["show"] is False

    def test_fixed_when_pattern_absent(self):
        previous = self._batch(
            "prev",
            [
                {"pattern": "hanging_piece", "avg_eval_swing": 1.2},
                {"pattern": "missed_fork", "avg_eval_swing": 0.9},
            ],
            priorities=[{"rank": 1, "title": "Slow opening prep"}],
        )
        current = self._batch(
            "current",
            [{"pattern": "missed_fork", "avg_eval_swing": 0.8}],
        )
        payload = build_fix_rate_payload(current, previous)
        assert payload["show"] is True
        assert payload["fixed_count"] == 2
        assert payload["total_count"] == 3
        assert "2/3" in payload["headline"]

    def test_improved_when_swing_drops(self):
        previous = self._batch(
            "prev",
            [{"pattern": "hanging_piece", "avg_eval_swing": 1.5}],
        )
        current = self._batch(
            "current",
            [{"pattern": "hanging_piece", "avg_eval_swing": 1.2}],
        )
        payload = build_fix_rate_payload(current, previous)
        assert payload["patterns"][0]["status"] == "improved"
        assert payload["fixed_count"] == 1

    def test_persisting_when_swing_flat(self):
        previous = self._batch(
            "prev",
            [{"pattern": "hanging_piece", "avg_eval_swing": 1.0}],
        )
        current = self._batch(
            "current",
            [{"pattern": "hanging_piece", "avg_eval_swing": 0.95}],
        )
        payload = build_fix_rate_payload(current, previous)
        assert payload["patterns"][0]["status"] == "persisting"
        assert payload["fixed_count"] == 0
