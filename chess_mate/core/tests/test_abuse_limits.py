"""Tests for signup, auth, import, analysis, batch, and checkout abuse limits."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from core.abuse_limits import (
    batches_started_today,
    check_batch_creation_allowed,
    check_checkout_allowed,
    check_coaching_regenerate_allowed,
    check_external_fetch_allowed,
    check_game_import_allowed,
    check_login_allowed,
    check_password_reset_allowed,
    check_signup_allowed,
    check_single_analysis_allowed,
    games_imported_today,
    record_checkout_session,
    record_coaching_regenerate,
    record_external_fetch,
    record_failed_login,
    record_password_reset_request,
    record_signup_attempt,
    record_single_analysis,
)
from core.models import BatchAnalysisReport, Game, Profile
from core.tests.profile_helpers import ensure_profile
from django.conf import settings as django_settings
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

LOCMEM_CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "local": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}

# Keep middleware AUTH limits out of the way; these tests target abuse_limits counters.
HIGH_AUTH_RATE_LIMIT = {
    "DEFAULT": {"MAX_REQUESTS": 1000, "TIME_WINDOW": 60},
    "AUTH": {"MAX_REQUESTS": 1000, "TIME_WINDOW": 60},
    "ANALYSIS": {"MAX_REQUESTS": 1000, "TIME_WINDOW": 60},
    "FETCH": {"MAX_REQUESTS": 1000, "TIME_WINDOW": 60},
    "CREDITS": {"MAX_REQUESTS": 1000, "TIME_WINDOW": 60},
    "BATCH_OPS": {"MAX_REQUESTS": 1000, "TIME_WINDOW": 60},
    "PUBLIC": {"MAX_REQUESTS": 1000, "TIME_WINDOW": 60},
    "GAMES": {"MAX_REQUESTS": 1000, "TIME_WINDOW": 60},
}


def _clear_cache():
    from core.cache import cache_delete
    from django.core.cache import caches

    for alias in ("default", "local"):
        try:
            caches[alias].clear()
        except Exception:
            pass

    for ip in ("127.0.0.1", "203.0.113.10"):
        for prefix in (
            "signup_attempts",
            "login_failed",
            "password_reset_ip",
        ):
            cache_delete(f"{prefix}:{ip}")
            cache_delete(f"{prefix}:{ip}:ts")


MIDDLEWARE_NO_RATE_LIMIT = [m for m in django_settings.MIDDLEWARE if m != "core.middleware.RateLimitMiddleware"]


def _auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


def _request(ip="203.0.113.10"):
    request = RequestFactory().post("/")
    request.META["REMOTE_ADDR"] = ip
    return request


@pytest.mark.django_db
class TestSignupRateLimit(TestCase):
    def setUp(self):
        _clear_cache()
        self.client = APIClient()

    @override_settings(
        SIGNUP_RATE_LIMIT_MAX_PER_IP=2,
        SIGNUP_RATE_LIMIT_WINDOW_SECONDS=3600,
        CACHES=LOCMEM_CACHES,
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
class TestLoginRateLimit(TestCase):
    def setUp(self):
        _clear_cache()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="loginuser",
            email="login@example.com",
            password="CorrectPass123!",
        )
        ensure_profile(self.user, credits=10, email_verified=True)

    @override_settings(
        LOGIN_FAILED_MAX_PER_IP=2,
        LOGIN_FAILED_WINDOW_SECONDS=3600,
        CACHES=LOCMEM_CACHES,
        MIDDLEWARE=MIDDLEWARE_NO_RATE_LIMIT,
    )
    def test_login_blocks_after_failed_attempts(self):
        for _ in range(2):
            response = self.client.post(
                "/api/v1/auth/login/",
                {"email": "login@example.com", "password": "wrong-password"},
                format="json",
            )
            assert response.status_code in (401, 403), response.data

        blocked = self.client.post(
            "/api/v1/auth/login/",
            {"email": "login@example.com", "password": "wrong-password"},
            format="json",
        )
        assert blocked.status_code == 429
        assert blocked.data["code"] == "RATE_002"

    @override_settings(
        LOGIN_FAILED_MAX_PER_IP=5,
        LOGIN_FAILED_WINDOW_SECONDS=3600,
        CACHES=LOCMEM_CACHES,
        MIDDLEWARE=MIDDLEWARE_NO_RATE_LIMIT,
    )
    def test_successful_login_not_blocked_after_one_failure(self):
        _clear_cache()
        self.client.post(
            "/api/v1/auth/login/",
            {"email": "login@example.com", "password": "wrong-password"},
            format="json",
        )
        ok = self.client.post(
            "/api/v1/auth/login/",
            {"email": "login@example.com", "password": "CorrectPass123!"},
            format="json",
        )
        assert ok.status_code == 200
        assert "access" in ok.data


@pytest.mark.django_db
class TestPasswordResetRateLimit(TestCase):
    def setUp(self):
        _clear_cache()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="resetuser",
            email="reset@example.com",
            password="Password123!",
        )
        ensure_profile(self.user, credits=5)

    @override_settings(
        PASSWORD_RESET_MAX_PER_IP=2,
        PASSWORD_RESET_WINDOW_SECONDS=3600,
        PASSWORD_RESET_MAX_PER_EMAIL=5,
        CACHES=LOCMEM_CACHES,
        MIDDLEWARE=MIDDLEWARE_NO_RATE_LIMIT,
    )
    def test_password_reset_blocks_by_ip(self):
        _clear_cache()
        with patch("core.email_utils.is_email_configured", return_value=True):
            with patch("django.core.mail.send_mail", return_value=1):
                for _ in range(2):
                    response = self.client.post(
                        "/api/v1/auth/reset-password/",
                        {"email": "reset@example.com"},
                        format="json",
                    )
                    assert response.status_code == 200

                blocked = self.client.post(
                    "/api/v1/auth/reset-password/",
                    {"email": "reset@example.com"},
                    format="json",
                )
        assert blocked.status_code == 429
        assert blocked.data["code"] == "RATE_003"

    @override_settings(
        PASSWORD_RESET_MAX_PER_IP=50,
        PASSWORD_RESET_MAX_PER_EMAIL=2,
        PASSWORD_RESET_EMAIL_WINDOW_SECONDS=86400,
        CACHES=LOCMEM_CACHES,
        MIDDLEWARE=MIDDLEWARE_NO_RATE_LIMIT,
    )
    def test_password_reset_blocks_by_email(self):
        _clear_cache()
        with patch("core.email_utils.is_email_configured", return_value=True):
            with patch("django.core.mail.send_mail", return_value=1):
                for _ in range(2):
                    response = self.client.post(
                        "/api/v1/auth/reset-password/",
                        {"email": "reset-email-limit@example.com"},
                        format="json",
                    )
                    assert response.status_code == 200

                blocked = self.client.post(
                    "/api/v1/auth/reset-password/",
                    {"email": "reset-email-limit@example.com"},
                    format="json",
                )
        assert blocked.status_code == 429
        assert blocked.data["code"] == "RATE_003"


@pytest.mark.django_db
class TestDailyBatchLimit(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="batchuser", password="pass")
        ensure_profile(self.user, credits=100)
        self.client = _auth_client(self.user)

    @override_settings(
        MAX_BATCHES_PER_USER_PER_DAY=2,
        ALLOW_CONCURRENT_BATCHES=True,
        CACHES=LOCMEM_CACHES,
    )
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

    @override_settings(MAX_BATCHES_PER_USER_PER_DAY=10, ALLOW_CONCURRENT_BATCHES=False)
    @patch("core.views_batches.analyze_batch_task.delay")
    @patch("core.serializers_batches.chess.pgn.read_game")
    def test_batch_create_blocks_while_active_batch_exists(self, mock_parse, mock_task):
        mock_parse.return_value = Mock()
        mock_task.return_value = Mock(id="celery-active")
        BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="active-batch",
            status="in_progress",
            games_count=5,
        )
        pgn_data = [f'[Event "T{i}"]\n1.e4 e5' for i in range(5)]
        response = self.client.post("/api/v1/batches/", {"games": pgn_data}, format="json")
        assert response.status_code == 429
        assert response.data["code"] == "BATCH_002"
        assert response.data["detail"]["active_batch"] is True

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

        assert batches_started_today(self.user) == 0
        allowed, _info = check_batch_creation_allowed(self.user)
        assert allowed is True


@pytest.mark.django_db
class TestCoachingRegenerateLimit(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="coachuser", password="pass")
        ensure_profile(self.user, credits=50)
        self.client = _auth_client(self.user)
        self.batch = BatchAnalysisReport.objects.create(
            user=self.user,
            task_id="coach-batch",
            status="completed",
            games_count=5,
            batch_summary={"games_analyzed": 5, "overall_accuracy_pct": 70.0},
            per_game_results=[{"game_id": f"g{i}"} for i in range(5)],
        )

    @override_settings(
        MAX_COACHING_REGENERATIONS_PER_USER_PER_DAY=5,
        MAX_COACHING_REGENERATIONS_PER_BATCH_PER_DAY=2,
        CACHES=LOCMEM_CACHES,
    )
    @patch("core.batch_coaching.generate_coaching_report")
    def test_regenerate_blocks_after_batch_daily_limit(self, mock_generate):
        mock_generate.return_value = {
            "executive_summary": "ok",
            "coaching_narrative": {"opening": "o", "middlegame": "m", "endgame": "e"},
            "top_3_priorities": [],
            "training_plan": {},
            "one_thing_to_do_today": "drill",
        }
        url = f"/api/v1/batches/{self.batch.id}/regenerate-coaching/"
        for _ in range(2):
            response = self.client.post(url)
            assert response.status_code == 200, response.data

        blocked = self.client.post(url)
        assert blocked.status_code == 429
        assert blocked.data["code"] == "COACH_001"


@pytest.mark.django_db
class TestCheckoutRateLimit(TestCase):
    def setUp(self):
        _clear_cache()
        self.user = User.objects.create_user(username="payuser", email="pay@example.com", password="pass")
        ensure_profile(self.user, credits=5)
        self.client = _auth_client(self.user)

    @override_settings(
        MAX_CHECKOUT_SESSIONS_PER_USER_PER_HOUR=2,
        CACHES=LOCMEM_CACHES,
        STRIPE_SECRET_KEY="sk_test_x",
        RATE_LIMIT=HIGH_AUTH_RATE_LIMIT,
    )
    def test_checkout_blocks_after_hourly_limit(self):
        with patch("core.views_credits.PaymentProcessor.create_checkout_session") as mock_checkout:
            mock_checkout.return_value = Mock(url="https://checkout.stripe.test/session", id="cs_test_1")
            for _ in range(2):
                response = self.client.post("/api/v1/purchase-credits/", {"package_id": "basic"})
                assert response.status_code == 200, response.data

            blocked = self.client.post("/api/v1/purchase-credits/", {"package_id": "basic"})
        assert blocked.status_code == 429
        assert blocked.data["code"] == "PAY_001"


@pytest.mark.django_db
class TestAbuseLimitUnitHelpers(TestCase):
    def setUp(self):
        _clear_cache()
        self.user = User.objects.create_user(username="unituser", password="pass")
        ensure_profile(self.user, credits=200)
        self.request = _request()

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_ip_window_helpers_for_signup_and_login(self):
        assert check_signup_allowed(self.request)[0] is True
        record_signup_attempt(self.request)
        record_signup_attempt(self.request)
        with override_settings(SIGNUP_RATE_LIMIT_MAX_PER_IP=2):
            assert check_signup_allowed(self.request)[0] is False

        assert check_login_allowed(self.request)[0] is True
        record_failed_login(self.request)
        record_failed_login(self.request)
        with override_settings(LOGIN_FAILED_MAX_PER_IP=2):
            assert check_login_allowed(self.request)[0] is False

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_password_reset_email_window(self):
        with override_settings(PASSWORD_RESET_MAX_PER_EMAIL=2):
            assert check_password_reset_allowed(self.request, "a@example.com")[0] is True
            record_password_reset_request(self.request, "a@example.com")
            record_password_reset_request(self.request, "a@example.com")
            assert check_password_reset_allowed(self.request, "a@example.com")[0] is False

    @override_settings(CACHES=LOCMEM_CACHES, MAX_GAME_IMPORTS_PER_USER_PER_DAY=3)
    def test_game_import_daily_count(self):
        for idx in range(3):
            Game.objects.create(
                user=self.user,
                platform="lichess",
                game_id=f"g{idx}",
                pgn="1. e4 e5",
                result="1-0",
                white="w",
                black="b",
            )
        assert games_imported_today(self.user) == 3
        allowed, info = check_game_import_allowed(self.user, 1)
        assert allowed is False
        assert info["count"] == 3

    @override_settings(CACHES=LOCMEM_CACHES, MAX_EXTERNAL_FETCH_REQUESTS_PER_USER_PER_DAY=2)
    def test_external_fetch_daily_count(self):
        assert check_external_fetch_allowed(self.user)[0] is True
        record_external_fetch(self.user)
        record_external_fetch(self.user)
        allowed, info = check_external_fetch_allowed(self.user)
        assert allowed is False
        assert info["count"] == 2

    @override_settings(CACHES=LOCMEM_CACHES, MAX_SINGLE_ANALYSES_PER_USER_PER_DAY=2)
    def test_single_analysis_daily_count(self):
        assert check_single_analysis_allowed(self.user)[0] is True
        record_single_analysis(self.user)
        record_single_analysis(self.user)
        assert check_single_analysis_allowed(self.user)[0] is False

    @override_settings(CACHES=LOCMEM_CACHES, MAX_CHECKOUT_SESSIONS_PER_USER_PER_HOUR=2)
    def test_checkout_hourly_count(self):
        from core.cache import cache_delete

        cache_delete(f"checkout_sessions:{self.user.id}")
        cache_delete(f"checkout_sessions:{self.user.id}:ts")
        record_checkout_session(self.user)
        record_checkout_session(self.user)
        assert check_checkout_allowed(self.user)[0] is False

    @override_settings(CACHES=LOCMEM_CACHES, MAX_COACHING_REGENERATIONS_PER_BATCH_PER_DAY=1)
    def test_coaching_regenerate_counters(self):
        batch_id = 99
        assert check_coaching_regenerate_allowed(self.user, batch_id)[0] is True
        record_coaching_regenerate(self.user, batch_id)
        assert check_coaching_regenerate_allowed(self.user, batch_id)[0] is False

    @override_settings(MAX_BATCHES_PER_USER_PER_DAY=5)
    def test_staff_bypasses_batch_daily_limit(self):
        staff = User.objects.create_user(username="staff", password="pass", is_staff=True)
        for idx in range(6):
            BatchAnalysisReport.objects.create(
                user=staff,
                task_id=f"staff-batch-{idx}",
                status="completed",
                games_count=5,
            )
        allowed, info = check_batch_creation_allowed(staff)
        assert allowed is True
        assert info.get("bypass") is True


@pytest.mark.django_db
class TestAwsSetupArtifacts(TestCase):
    """Sanity checks for repo CloudWatch alarm setup files."""

    @property
    def repo_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    def test_cloudwatch_policy_json_exists_and_allows_required_actions(self):
        policy_path = self.repo_root / "scripts" / "aws" / "iam-cloudwatch-alarms-policy.json"
        assert policy_path.is_file(), f"Missing policy file: {policy_path}"
        import json

        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        statements = policy.get("Statement", [])
        actions = {action for stmt in statements for action in stmt.get("Action", [])}
        assert "cloudwatch:PutMetricAlarm" in actions
        assert "sns:CreateTopic" in actions
        assert "sns:Subscribe" in actions

    def test_cloudwatch_setup_script_declares_all_alarms(self):
        script_path = self.repo_root / "scripts" / "aws" / "setup_cloudwatch_alarms.ps1"
        assert script_path.is_file(), f"Missing script: {script_path}"
        content = script_path.read_text(encoding="utf-8")
        for alarm_name in (
            "Chessmate-EB-CPU-High",
            "Chessmate-ALB-Target-5xx",
            "Chessmate-RDS-Connections-High",
        ):
            assert alarm_name in content
