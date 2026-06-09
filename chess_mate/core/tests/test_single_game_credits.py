"""Tests for single-game analysis credit refunds on hard failure."""

from core.single_game_credits import (
    charge_single_game_credit,
    mark_single_game_credit_charged,
    qualifies_for_first_single_game_free,
    refund_single_game_credit_on_fail,
    resolve_single_game_credit_waiver,
)
from core.tests.profile_helpers import ensure_profile
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings

LOC_MEM_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "single-game-credit-tests",
    }
}


@override_settings(SINGLE_GAME_ANALYSIS_CREDITS=1, CACHES=LOC_MEM_CACHES)
class TestSingleGameCreditRefund(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="sg_refund_user", password="testpass"
        )
        self.profile = ensure_profile(self.user, credits=10)
        self.game_id = 42

    def tearDown(self):
        cache.clear()

    def test_refund_restores_one_credit(self):
        self.profile.credits = 9
        self.profile.save(update_fields=["credits"])
        mark_single_game_credit_charged(self.user.id, self.game_id)

        refunded = refund_single_game_credit_on_fail(self.user.id, self.game_id)

        assert refunded == 1
        self.profile.refresh_from_db()
        assert self.profile.credits == 10

    def test_refund_is_idempotent(self):
        self.profile.credits = 9
        self.profile.save(update_fields=["credits"])
        mark_single_game_credit_charged(self.user.id, self.game_id)

        assert refund_single_game_credit_on_fail(self.user.id, self.game_id) == 1
        assert refund_single_game_credit_on_fail(self.user.id, self.game_id) == 0

        self.profile.refresh_from_db()
        assert self.profile.credits == 10

    def test_refund_skips_invalid_ids(self):
        assert refund_single_game_credit_on_fail(0, self.game_id) == 0
        assert refund_single_game_credit_on_fail(self.user.id, 0) == 0

    def test_first_single_game_free_waiver(self):
        assert qualifies_for_first_single_game_free(self.profile) is True
        waiver = resolve_single_game_credit_waiver(
            self.user,
            self.game_id,
            self.profile,
            force_reanalyze=False,
        )
        assert waiver == "first_free"
        charged = charge_single_game_credit(
            self.user, self.game_id, self.profile, waiver=waiver
        )
        assert charged == 0
        self.profile.refresh_from_db()
        assert qualifies_for_first_single_game_free(self.profile) is False

    def test_reanalyze_never_waived(self):
        waiver = resolve_single_game_credit_waiver(
            self.user,
            self.game_id,
            self.profile,
            force_reanalyze=True,
        )
        assert waiver == ""

    def test_refund_skips_when_credit_was_not_charged(self):
        self.profile.credits = 9
        self.profile.save(update_fields=["credits"])

        assert refund_single_game_credit_on_fail(self.user.id, self.game_id) == 0
        self.profile.refresh_from_db()
        assert self.profile.credits == 9
