"""Tests for coach inbox review streak (SRG-16)."""

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from core.inbox_streak import (get_inbox_streak_payload,
                               update_inbox_streak_on_review)
from core.models import BatchAnalysisReport, Profile
from core.priority_inbox import (mark_priority_inbox_reviewed,
                                 seed_priority_inbox_from_batch)
from core.tests.profile_helpers import ensure_profile


class TestInboxStreak(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="streakuser", password="pass")
        self.profile = ensure_profile(self.user, credits=10)

    def _seed_inbox(self):
        batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="streak-batch",
            status="completed",
            games_count=5,
            coaching_report={
                "top_3_priorities": [
                    {"rank": 1, "title": "Priority one", "specific_drill": "Drill"},
                ]
            },
        )
        seed_priority_inbox_from_batch(batch)
        return batch

    def test_first_review_starts_streak_at_one_not_shown(self):
        batch = self._seed_inbox()
        ok, _, streak = mark_priority_inbox_reviewed(
            self.user, batch_id=batch.id, priority_index=1
        )
        assert ok is True
        assert streak["count"] == 1
        assert streak["show"] is False

    def test_consecutive_days_increment_and_show_from_two(self):
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        profile = Profile.objects.get(user=self.user)
        profile.preferences = {
            "inbox_streak": {
                "count": 1,
                "last_reviewed_date": yesterday.isoformat(),
            }
        }
        profile.save(update_fields=["preferences"])

        streak = update_inbox_streak_on_review(profile)
        assert streak["count"] == 2
        assert streak["show"] is True
        assert streak["label"] == "2-day coach streak"

    def test_same_day_second_review_does_not_increment(self):
        today = timezone.localdate()
        profile = Profile.objects.get(user=self.user)
        profile.preferences = {
            "inbox_streak": {
                "count": 3,
                "last_reviewed_date": today.isoformat(),
            }
        }
        profile.save(update_fields=["preferences"])

        streak = update_inbox_streak_on_review(profile)
        assert streak["count"] == 3

    def test_missed_day_resets_effective_count_on_read(self):
        today = timezone.localdate()
        three_days_ago = today - timedelta(days=3)
        profile = Profile.objects.get(user=self.user)
        profile.preferences = {
            "inbox_streak": {
                "count": 5,
                "last_reviewed_date": three_days_ago.isoformat(),
            }
        }
        profile.save(update_fields=["preferences"])

        payload = get_inbox_streak_payload(profile.preferences)
        assert payload["count"] == 0
        assert payload["show"] is False

    def test_milestone_message_at_five_days(self):
        today = timezone.localdate()
        profile = Profile.objects.get(user=self.user)
        profile.preferences = {
            "inbox_streak": {
                "count": 5,
                "last_reviewed_date": today.isoformat(),
            }
        }
        payload = get_inbox_streak_payload(profile.preferences)
        assert payload["show"] is True
        assert "5-day coach streak" in payload["milestone_message"]
