"""Tests for coach priority inbox (SRG-9)."""

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import BatchAnalysisReport, Game, Profile
from core.priority_inbox import (
    build_priority_inbox_link,
    get_priority_inbox_payload,
    mark_priority_inbox_reviewed,
    seed_priority_inbox_from_batch,
)
from core.tests.profile_helpers import ensure_profile


class TestPriorityInboxService(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="inboxuser", password="pass")
        ensure_profile(self.user, credits=10)
        self.game = Game.objects.create(
            user=self.user,
            platform="lichess",
            white="inboxuser",
            black="opponent",
            result="loss",
            pgn="1. e4 e5",
            analysis_status="analyzed",
        )

    def _batch_with_priorities(self, **kwargs):
        defaults = {
            "user": self.user,
            "task_id": "task-inbox",
            "status": "completed",
            "games_count": 5,
            "coaching_report": {
                "top_3_priorities": [
                    {
                        "rank": 1,
                        "title": "Fix hanging pieces",
                        "specific_drill": "Review game_2 move 14 blunder",
                    },
                    {
                        "rank": 2,
                        "title": "Opening prep",
                        "specific_drill": "Drill Najdorf lines",
                    },
                ]
            },
            "per_game_results": [
                {"game_id": "game_2", "saved_game_id": self.game.id},
            ],
            "batch_summary": {
                "top_critical_moments": [
                    {"saved_game_id": self.game.id, "move_number": 14}
                ]
            },
        }
        defaults.update(kwargs)
        return BatchAnalysisReport.objects.create(**defaults)

    def test_seed_creates_pending_items_with_proof_link(self):
        batch = self._batch_with_priorities()
        count = seed_priority_inbox_from_batch(batch)
        assert count == 2

        profile = Profile.objects.get(user=self.user)
        payload = get_priority_inbox_payload(profile)
        assert payload["pending_count"] == 2
        first = payload["pending_items"][0]
        assert first["title"] == "Fix hanging pieces"
        assert first["linked_game_id"] == self.game.id
        assert first["linked_move"] == 14
        assert first["href"] == (
            f"/game/{self.game.id}/analysis?mode=review&batch={batch.id}&priority=1&move=14"
        )

    def test_new_batch_archives_old_pending_items(self):
        old_batch = self._batch_with_priorities(task_id="old")
        seed_priority_inbox_from_batch(old_batch)

        new_batch = self._batch_with_priorities(
            task_id="new",
            coaching_report={
                "top_3_priorities": [
                    {"rank": 1, "title": "New priority", "specific_drill": "Do X"}
                ]
            },
        )
        seed_priority_inbox_from_batch(new_batch)

        profile = Profile.objects.get(user=self.user)
        inbox = profile.get_preference("priority_inbox")
        old_item = next(
            item for item in inbox["items"] if item["batch_id"] == old_batch.id
        )
        assert old_item["archived"] is True
        payload = get_priority_inbox_payload(profile)
        assert payload["pending_count"] == 1

    def test_mark_reviewed_updates_status(self):
        batch = self._batch_with_priorities()
        seed_priority_inbox_from_batch(batch)

        ok, message, streak = mark_priority_inbox_reviewed(
            self.user, batch_id=batch.id, priority_index=1
        )
        assert ok is True
        assert streak["count"] == 1

        profile = Profile.objects.get(user=self.user)
        payload = get_priority_inbox_payload(profile)
        assert payload["pending_count"] == 1
        assert payload["reviewed_count"] == 1

    def test_build_link_falls_back_to_batch_report(self):
        item = {"batch_id": 9, "priority_index": 2, "linked_game_id": None}
        assert build_priority_inbox_link(item) == "/batch-report/9?priority=2"


class TestPriorityInboxAPI(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="apiinbox", password="pass")
        ensure_profile(self.user, credits=10)
        self.client = APIClient()
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        self.batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="api-batch",
            status="completed",
            games_count=5,
            coaching_report={
                "top_3_priorities": [
                    {"rank": 1, "title": "Priority one", "specific_drill": "Drill A"},
                ]
            },
        )
        seed_priority_inbox_from_batch(self.batch)

    def test_get_inbox_returns_pending_items(self):
        response = self.client.get("/api/v1/batches/inbox/")
        assert response.status_code == 200
        assert response.data["pending_count"] == 1
        assert response.data["pending_items"][0]["title"] == "Priority one"

    def test_review_endpoint_marks_item(self):
        response = self.client.post(
            "/api/v1/batches/inbox/review/",
            {"batch_id": self.batch.id, "priority_index": 1},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["priority_inbox"]["pending_count"] == 0

    def test_review_rejects_other_users_batch(self):
        other = User.objects.create_user(username="otherinbox", password="pass")
        ensure_profile(other, credits=10)
        response = self.client.post(
            "/api/v1/batches/inbox/review/",
            {"batch_id": 99999, "priority_index": 1},
            format="json",
        )
        assert response.status_code == 404
