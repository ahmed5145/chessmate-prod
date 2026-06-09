"""Tests for batch A vs B moment diff (SRG-20)."""

from core.batch_moment_diff import build_batch_moment_diff
from core.models import BatchAnalysisReport, Profile
from core.moment_timeline import record_batch_timeline_events
from core.tests.profile_helpers import ensure_profile
from django.contrib.auth.models import User
from django.test import TestCase


class TestBatchMomentDiff(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="diffuser", password="pass")
        ensure_profile(self.user, credits=10)
        self.profile = Profile.objects.get(user=self.user)

    def _batch(self, task_id, weaknesses):
        return BatchAnalysisReport.objects.create(
            user=self.user,
            task_id=task_id,
            status="completed",
            games_count=5,
            coaching_report={"top_3_priorities": []},
            batch_summary={"recurring_weaknesses": weaknesses},
        )

    def test_hidden_without_previous_batch(self):
        current = self._batch(
            "only",
            [{"pattern": "hanging_piece", "avg_eval_swing": 1.0}],
        )
        payload = build_batch_moment_diff(current, None, self.profile)
        assert payload["show"] is False

    def test_compares_top_three_patterns(self):
        previous = self._batch(
            "prev",
            [
                {"pattern": "hanging_piece", "avg_eval_swing": 1.5},
                {"pattern": "missed_fork", "avg_eval_swing": 1.1},
                {"pattern": "pin", "avg_eval_swing": 0.8},
                {"pattern": "skewer", "avg_eval_swing": 0.5},
            ],
        )
        current = self._batch(
            "current",
            [
                {"pattern": "missed_fork", "avg_eval_swing": 1.0},
                {"pattern": "endgame_slip", "avg_eval_swing": 1.2},
            ],
        )
        payload = build_batch_moment_diff(current, previous, self.profile)
        assert payload["show"] is True
        assert len(payload["rows"]) >= 3
        labels = {row["label"] for row in payload["rows"]}
        assert "hanging_piece" in labels
        assert "missed_fork" in labels
        assert payload["counts"]["resolved"] >= 1
        assert payload["counts"]["new"] >= 1

    def test_sparkline_uses_timeline_when_available(self):
        previous = self._batch(
            "timeline-prev",
            [{"pattern": "hanging_piece", "avg_eval_swing": 1.4}],
        )
        current = self._batch(
            "timeline-current",
            [{"pattern": "hanging_piece", "avg_eval_swing": 0.7}],
        )
        older = self._batch(
            "timeline-older",
            [{"pattern": "hanging_piece", "avg_eval_swing": 1.6}],
        )
        record_batch_timeline_events(older)
        record_batch_timeline_events(previous)
        record_batch_timeline_events(current)

        payload = build_batch_moment_diff(current, previous, self.profile)
        row = next(row for row in payload["rows"] if row["label"] == "hanging_piece")
        assert len(row["sparkline"]) >= 2

    def test_resolved_when_pattern_absent(self):
        previous = self._batch(
            "prev",
            [{"pattern": "hanging_piece", "avg_eval_swing": 1.2}],
        )
        current = self._batch("current", [])
        payload = build_batch_moment_diff(current, previous, self.profile)
        row = payload["rows"][0]
        assert row["status"] == "resolved"
        assert row["current_swing"] is None
