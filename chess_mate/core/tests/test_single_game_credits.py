"""Tests for single-game analysis credit refunds on hard failure."""

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings

from core.single_game_credits import refund_single_game_credit_on_fail
from core.tests.profile_helpers import ensure_profile


LOC_MEM_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "single-game-credit-tests",
    }
}


@override_settings(SINGLE_GAME_ANALYSIS_CREDITS=1, CACHES=LOC_MEM_CACHES)
class TestSingleGameCreditRefund(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sg_refund_user", password="testpass")
        self.profile = ensure_profile(self.user, credits=10)
        self.game_id = 42

    def tearDown(self):
        cache.clear()

    def test_refund_restores_one_credit(self):
        self.profile.credits = 9
        self.profile.save(update_fields=["credits"])

        refunded = refund_single_game_credit_on_fail(self.user.id, self.game_id)

        assert refunded == 1
        self.profile.refresh_from_db()
        assert self.profile.credits == 10

    def test_refund_is_idempotent(self):
        self.profile.credits = 9
        self.profile.save(update_fields=["credits"])

        assert refund_single_game_credit_on_fail(self.user.id, self.game_id) == 1
        assert refund_single_game_credit_on_fail(self.user.id, self.game_id) == 0

        self.profile.refresh_from_db()
        assert self.profile.credits == 10

    def test_refund_skips_invalid_ids(self):
        assert refund_single_game_credit_on_fail(0, self.game_id) == 0
        assert refund_single_game_credit_on_fail(self.user.id, 0) == 0
