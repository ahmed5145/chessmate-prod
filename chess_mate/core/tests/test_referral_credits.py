"""Tests for SRG-24 referral credits."""

import pytest
from core.models import BatchAnalysisReport, Profile, ReferralRedemption
from core.referral import (MONTHLY_REFERRAL_CAP, REFEREE_BONUS_CREDITS,
                           REFERRER_CREDITS, attach_referral_on_signup,
                           ensure_referral_code,
                           process_referral_on_first_batch)
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def referrer(db):
    user = User.objects.create_user(
        username="referrer",
        email="referrer@example.com",
        password="Test.Password.123",
    )
    profile = Profile.objects.get(user=user)
    ensure_referral_code(profile)
    profile.refresh_from_db()
    return user


@pytest.fixture
def referee(db, referrer):
    user = User.objects.create_user(
        username="referee",
        email="referee@example.com",
        password="Test.Password.123",
    )
    profile = Profile.objects.get(user=user)
    referrer_profile = Profile.objects.get(user=referrer)
    attach_referral_on_signup(
        profile,
        referral_code=referrer_profile.referral_code,
        signup_ip="10.0.0.2",
    )
    return user


def _first_batch(user):
    return BatchAnalysisReport.objects.create(
        user=user,
        task_id=f"task-ref-{user.id}",
        status="completed",
        games_count=10,
        coaching_report={"executive_summary": "Coach ready", "top_3_priorities": []},
        batch_summary={},
        per_game_results=[],
    )


def test_referral_grants_credits_on_first_batch(referrer, referee):
    referrer_profile = Profile.objects.get(user=referrer)
    referee_profile = Profile.objects.get(user=referee)
    referrer_start = referrer_profile.credits
    referee_start = referee_profile.credits

    batch = _first_batch(referee)
    redemption = process_referral_on_first_batch(batch)

    assert redemption is not None
    referrer_profile.refresh_from_db()
    referee_profile.refresh_from_db()
    assert referrer_profile.credits == referrer_start + REFERRER_CREDITS
    assert referee_profile.credits == referee_start + REFEREE_BONUS_CREDITS
    assert ReferralRedemption.objects.filter(referee=referee).count() == 1


def test_self_referral_blocked(referrer):
    profile = Profile.objects.get(user=referrer)
    assert (
        attach_referral_on_signup(profile, referral_code=profile.referral_code) is False
    )


def test_no_double_redemption(referrer, referee):
    batch = _first_batch(referee)
    assert process_referral_on_first_batch(batch) is not None
    assert process_referral_on_first_batch(batch) is None


def test_monthly_referral_cap_blocks_referrer_reward(referrer, db):
    referrer_profile = Profile.objects.get(user=referrer)
    referrer_start = referrer_profile.credits

    for index in range(MONTHLY_REFERRAL_CAP):
        extra = User.objects.create_user(
            username=f"referee_{index}",
            email=f"referee_{index}@example.com",
            password="Test.Password.123",
        )
        extra_profile = Profile.objects.get(user=extra)
        attach_referral_on_signup(
            extra_profile,
            referral_code=referrer_profile.referral_code,
            signup_ip=f"10.0.0.{index + 10}",
        )
        batch = _first_batch(extra)
        assert process_referral_on_first_batch(batch) is not None

    capped_referee = User.objects.create_user(
        username="referee_capped",
        email="referee_capped@example.com",
        password="Test.Password.123",
    )
    capped_profile = Profile.objects.get(user=capped_referee)
    attach_referral_on_signup(
        capped_profile,
        referral_code=referrer_profile.referral_code,
        signup_ip="10.0.0.99",
    )
    capped_batch = _first_batch(capped_referee)

    assert process_referral_on_first_batch(capped_batch) is None
    referrer_profile.refresh_from_db()
    assert referrer_profile.credits == referrer_start + (
        REFERRER_CREDITS * MONTHLY_REFERRAL_CAP
    )
