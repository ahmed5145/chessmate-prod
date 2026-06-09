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

    def test_proof_game_id_resolves_batch_local_example_ids(self):
        """example_game_ids use game_N batch refs, not saved_game_id ints."""
        previous = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="prev-local",
            status="completed",
            games_count=5,
            batch_summary={
                "recurring_weaknesses": [
                    {
                        "pattern": "hanging_piece",
                        "avg_eval_swing": 1.0,
                        "example_game_ids": ["game_0"],
                    }
                ]
            },
            created_at=timezone.now(),
        )
        current = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="current-local",
            status="completed",
            games_count=5,
            per_game_results=[
                {"game_id": "game_0", "saved_game_id": 42, "result": "win"},
                {"game_id": "game_1", "saved_game_id": 99},
            ],
            batch_summary={
                "recurring_weaknesses": [
                    {"pattern": "missed_fork", "avg_eval_swing": 0.8, "example_game_ids": ["game_1"]},
                ]
            },
            created_at=timezone.now(),
        )
        payload = build_fix_rate_payload(current, previous)
        assert payload["show"] is True
        fixed_row = next(row for row in payload["patterns"] if row["label"] == "hanging_piece")
        assert fixed_row["status"] == "fixed"
        assert fixed_row["proof_game_id"] == 42

        dashboard_payload = build_dashboard_fix_rate(self.user)
        assert dashboard_payload["show"] is True
