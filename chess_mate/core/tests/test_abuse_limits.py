"""Tests for signup and daily batch abuse limits."""

from unittest.mock import Mock, patch

import pytest
from core.models import BatchAnalysisReport, Profile
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.mark.django_db
class TestSignupRateLimit(TestCase):
    def setUp(self):
        self.client = APIClient()

    @override_settings(
        SIGNUP_RATE_LIMIT_MAX_PER_IP=2,
        SIGNUP_RATE_LIMIT_WINDOW_SECONDS=3600,
        CACHES={
            "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
            "local": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        },
    )
    def test_register_blocks_after_ip_limit(self):
        payload = {
            "username": "user1",
            "email": "one@example.com",
            "password": "Password123!",
        }
        for idx in range(2):
            response = self.client.post(
                "/api/v1/auth/register/",
                {
                    **payload,
                    "username": f"user{idx}",
                    "email": f"user{idx}@example.com",
                },
                format="json",
            )
            assert response.status_code == 201, response.data

        blocked = self.client.post(
            "/api/v1/auth/register/",
            {
                "username": "user3",
                "email": "user3@example.com",
                "password": "Password123!",
            },
            format="json",
        )
        assert blocked.status_code == 429
        assert blocked.data["code"] == "RATE_001"
        assert "retry_after" in blocked.data


@pytest.mark.django_db
class TestDailyBatchLimit(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="batchuser", password="pass")
        Profile.objects.create(user=self.user, credits=100)
        self.client = APIClient()
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    @override_settings(MAX_BATCHES_PER_USER_PER_DAY=2)
    @patch("core.views_batches.analyze_batch_task.delay")
    @patch("core.serializers_batches.chess.pgn.read_game")
    def test_batch_create_blocks_after_daily_limit(self, mock_parse, mock_task):
        mock_parse.return_value = Mock()
        mock_task.return_value = Mock(id="celery-1")
        pgn_data = [f'[Event "T{i}"]\n1.e4 e5' for i in range(5)]

        for _ in range(2):
            response = self.client.post("/api/v1/batches/", {"games": pgn_data}, format="json")
            assert response.status_code == 202, response.data

        blocked = self.client.post("/api/v1/batches/", {"games": pgn_data}, format="json")
        assert blocked.status_code == 429
        assert blocked.data["code"] == "BATCH_001"
        assert blocked.data["detail"]["limit"] == 2

    @override_settings(MAX_BATCHES_PER_USER_PER_DAY=1)
    def test_batches_started_today_ignores_yesterday(self):
        yesterday = timezone.now() - timezone.timedelta(days=1)
        old = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="old-batch",
            status="completed",
            games_count=5,
        )
        BatchAnalysisReport.objects.filter(pk=old.pk).update(created_at=yesterday)

        from core.abuse_limits import batches_started_today, check_batch_creation_allowed

        assert batches_started_today(self.user) == 0
        allowed, _info = check_batch_creation_allowed(self.user)
        assert allowed is True
