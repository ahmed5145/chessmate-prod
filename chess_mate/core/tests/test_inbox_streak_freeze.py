"""Tests for inbox streak freeze (SRG-25)."""

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from core.inbox_streak import (
    FREEZE_MONTH_KEY,
    apply_inbox_streak_freeze,
    can_use_inbox_streak_freeze,
    get_inbox_streak_payload,
)
from core.models import Profile
from core.tests.profile_helpers import ensure_profile


class TestInboxStreakFreeze(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="freezeuser", password="pass")
        self.profile = ensure_profile(self.user, credits=10)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _prefs_with_streak(self, count, days_ago):
        today = timezone.localdate()
        return {
            "inbox_streak": {
                "count": count,
                "last_reviewed_date": (today - timedelta(days=days_ago)).isoformat(),
            }
        }

    def test_can_freeze_after_exactly_one_missed_day(self):
        prefs = self._prefs_with_streak(count=4, days_ago=2)
        assert can_use_inbox_streak_freeze(prefs) is True

    def test_cannot_freeze_below_three_day_streak(self):
        prefs = self._prefs_with_streak(count=2, days_ago=2)
        assert can_use_inbox_streak_freeze(prefs) is False

    def test_cannot_freeze_twice_same_month(self):
        today = timezone.localdate()
        prefs = self._prefs_with_streak(count=4, days_ago=2)
        prefs[FREEZE_MONTH_KEY] = today.strftime("%Y-%m")
        assert can_use_inbox_streak_freeze(prefs) is False

    def test_apply_freeze_preserves_count_and_extends_streak(self):
        profile = Profile.objects.get(user=self.user)
        profile.preferences = self._prefs_with_streak(count=4, days_ago=2)
        profile.save(update_fields=["preferences"])

        payload = apply_inbox_streak_freeze(profile)
        assert payload["count"] == 4
        assert payload["show"] is True
        assert payload["freeze"]["used_this_month"] is True
        assert payload["freeze"]["can_use"] is False

        profile.refresh_from_db()
        read_payload = get_inbox_streak_payload(profile.preferences)
        assert read_payload["count"] == 4

    def test_freeze_api_returns_inbox_payload(self):
        profile = Profile.objects.get(user=self.user)
        profile.preferences = self._prefs_with_streak(count=3, days_ago=2)
        profile.save(update_fields=["preferences"])

        response = self.client.post("/api/v1/batches/inbox/freeze/")
        assert response.status_code == 200
        body = response.json()
        assert body["detail"] == "Streak freeze applied"
        assert body["inbox_streak"]["count"] == 3
        assert "priority_inbox" in body

    def test_freeze_api_rejects_when_unavailable(self):
        profile = Profile.objects.get(user=self.user)
        profile.preferences = self._prefs_with_streak(count=1, days_ago=2)
        profile.save(update_fields=["preferences"])

        response = self.client.post("/api/v1/batches/inbox/freeze/")
        assert response.status_code == 400
