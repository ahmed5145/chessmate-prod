"""Tests for in-app notification center (SRG-14)."""

from datetime import timedelta

from core.models import BatchAnalysisReport, Game, UserNotification
from core.notifications import (
    create_user_notification,
    notify_batch_complete,
    notify_single_game_complete,
)
from core.priority_inbox import seed_priority_inbox_from_batch
from core.tests.profile_helpers import ensure_profile
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


class TestNotificationCenter(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="notifyuser", password="pass")
        ensure_profile(self.user, credits=10)
        self.client = APIClient()
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    def test_create_dedupes_within_24_hours(self):
        first = create_user_notification(
            self.user,
            notification_type=UserNotification.TYPE_BATCH_COMPLETE,
            entity_id="batch:1",
            title="Batch ready",
            href="/batch-report/1",
        )
        second = create_user_notification(
            self.user,
            notification_type=UserNotification.TYPE_BATCH_COMPLETE,
            entity_id="batch:1",
            title="Batch ready again",
            href="/batch-report/1",
        )
        assert first is not None
        assert second is None
        assert UserNotification.objects.filter(user=self.user).count() == 1

    def test_list_and_mark_read_api(self):
        row = create_user_notification(
            self.user,
            notification_type=UserNotification.TYPE_SINGLE_COMPLETE,
            entity_id="game:9",
            title="Review ready",
            href="/game/9/analysis?mode=review",
        )
        list_response = self.client.get("/api/v1/notifications/")
        assert list_response.status_code == 200
        assert list_response.data["unread_count"] == 1
        assert list_response.data["notifications"][0]["href"].endswith("mode=review")

        patch_response = self.client.patch(
            "/api/v1/notifications/",
            {"ids": [row.id]},
            format="json",
        )
        assert patch_response.status_code == 200
        assert patch_response.data["unread_count"] == 0
        row.refresh_from_db()
        assert row.read_at is not None

    def test_mark_all_read_api(self):
        create_user_notification(
            self.user,
            notification_type=UserNotification.TYPE_INBOX_ITEM,
            entity_id="inbox:1:1",
            title="Priority",
            href="/game/1/analysis?mode=review",
        )
        create_user_notification(
            self.user,
            notification_type=UserNotification.TYPE_FIX_RATE,
            entity_id="fix_rate:2",
            title="Fixed 2/3",
            href="/batch-report/2",
        )
        response = self.client.patch(
            "/api/v1/notifications/",
            {"mark_all": True},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["unread_count"] == 0
        assert response.data["marked_read"] == 2

    def test_batch_complete_seeds_inbox_notifications(self):
        game = Game.objects.create(
            user=self.user,
            platform="lichess",
            white="notifyuser",
            black="opponent",
            result="loss",
            pgn="1. e4 e5",
            analysis_status="analyzed",
        )
        batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="notify-batch",
            status="completed",
            games_count=5,
            coaching_report={
                "top_3_priorities": [
                    {"rank": 1, "title": "Fix forks", "specific_drill": "Review game"},
                ]
            },
            per_game_results=[{"saved_game_id": game.id, "move_number": 12}],
            batch_summary={
                "top_critical_moments": [{"saved_game_id": game.id, "move_number": 12}]
            },
        )
        seed_priority_inbox_from_batch(batch)
        notify_batch_complete(self.user, batch)

        types = set(UserNotification.objects.filter(user=self.user).values_list("notification_type", flat=True))
        assert UserNotification.TYPE_BATCH_COMPLETE in types
        assert UserNotification.TYPE_INBOX_ITEM in types

    def test_old_duplicate_allowed_after_24h(self):
        row = create_user_notification(
            self.user,
            notification_type=UserNotification.TYPE_BATCH_COMPLETE,
            entity_id="batch:5",
            title="First",
            href="/batch-report/5",
        )
        UserNotification.objects.filter(id=row.id).update(created_at=timezone.now() - timedelta(hours=25))
        second = create_user_notification(
            self.user,
            notification_type=UserNotification.TYPE_BATCH_COMPLETE,
            entity_id="batch:5",
            title="Second",
            href="/batch-report/5",
        )
        assert second is not None

    def test_single_complete_notification_uses_review_link(self):
        game = Game.objects.create(
            user=self.user,
            platform="lichess",
            white="notifyuser",
            black="opponent",
            result="loss",
            pgn="1. e4 e5",
            analysis_status="analyzed",
        )

        class StubAnalysis:
            feedback = {
                "coaching": {
                    "headline": "Blunder on move 14",
                    "critical_moments": [{"move_number": 14, "eval_swing": 1.2}],
                }
            }
            analysis_data = {}

        notify_single_game_complete(self.user, game, StubAnalysis())
        row = UserNotification.objects.get(user=self.user)
        assert "mode=review" in row.href
        assert "move=14" in row.href
