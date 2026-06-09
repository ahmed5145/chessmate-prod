"""Referral credits — grant on referee first batch complete (SRG-24)."""

from __future__ import annotations

import logging
import secrets
from typing import Any, Dict, Optional

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .first_batch_celebration import eligible_batches_for_user, is_first_eligible_batch
from .models import BatchAnalysisReport, Profile, ReferralRedemption

logger = logging.getLogger(__name__)

REFERRAL_CODE_KEY = "referral_code"
REFERRED_BY_USER_ID_KEY = "referred_by_user_id"
SIGNUP_IP_KEY = "signup_ip"

REFERRER_CREDITS = 5
REFEREE_BONUS_CREDITS = 5
MONTHLY_REFERRAL_CAP = 10


def _normalize_code(code: Any) -> str:
    return str(code or "").strip().lower()


def generate_referral_code(user: User) -> str:
    base = "".join(ch for ch in user.username.lower() if ch.isalnum())[:10]
    suffix = secrets.token_hex(2)
    return f"{base}-{suffix}" if base else f"cm-{suffix}"


def ensure_referral_code(profile: Profile) -> str:
    existing = profile.get_preference(REFERRAL_CODE_KEY)
    if existing:
        return str(existing)
    code = generate_referral_code(profile.user)
    for _ in range(5):
        clash = (
            Profile.objects.filter(referral_code=code).exclude(pk=profile.pk).exists()
        )
        if not clash:
            break
        code = generate_referral_code(profile.user)
    profile.referral_code = code
    profile.set_preference(REFERRAL_CODE_KEY, code)
    profile.save(update_fields=["preferences", "referral_code"])
    return code


def find_referrer_profile(code: str) -> Optional[Profile]:
    normalized = _normalize_code(code)
    if not normalized:
        return None
    profile = Profile.objects.filter(referral_code__iexact=normalized).first()
    if profile:
        return profile
    return Profile.objects.filter(preferences__referral_code__iexact=normalized).first()


def attach_referral_on_signup(
    referee_profile: Profile,
    *,
    referral_code: Optional[str],
    signup_ip: Optional[str] = None,
) -> bool:
    if not referral_code:
        return False
    if referee_profile.get_preference(REFERRED_BY_USER_ID_KEY):
        return False

    referrer_profile = find_referrer_profile(referral_code)
    if referrer_profile is None:
        return False
    if referrer_profile.user_id == referee_profile.user_id:
        return False

    if signup_ip and referrer_profile.get_preference(SIGNUP_IP_KEY) == signup_ip:
        logger.info(
            "Referral skipped for user %s: same signup IP as referrer",
            referee_profile.user_id,
        )
        return False

    referee_profile.set_preference(REFERRED_BY_USER_ID_KEY, referrer_profile.user_id)
    if signup_ip:
        referee_profile.set_preference(SIGNUP_IP_KEY, signup_ip)
    referee_profile.save(update_fields=["preferences"])
    return True


def _referrals_this_month(referrer: User) -> int:
    month_start = timezone.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    return ReferralRedemption.objects.filter(
        referrer=referrer,
        created_at__gte=month_start,
    ).count()


def build_referral_payload(profile: Profile, request=None) -> Dict[str, Any]:
    from .email_utils import get_frontend_base_url

    code = ensure_referral_code(profile)
    base = get_frontend_base_url(request)
    link = f"{base}/register?ref={code}"
    redemptions = ReferralRedemption.objects.filter(referrer=profile.user).count()
    return {
        "referral_code": code,
        "referral_link": link,
        "referrer_credits": REFERRER_CREDITS,
        "referee_bonus_credits": REFEREE_BONUS_CREDITS,
        "monthly_cap": MONTHLY_REFERRAL_CAP,
        "successful_referrals": redemptions,
        "referrals_this_month": _referrals_this_month(profile.user),
    }


@transaction.atomic
def process_referral_on_first_batch(
    batch_report: BatchAnalysisReport,
) -> Optional[ReferralRedemption]:
    if not is_first_eligible_batch(batch_report):
        return None

    referee = batch_report.user
    try:
        referee_profile = Profile.objects.select_for_update().get(user=referee)
    except Profile.DoesNotExist:
        return None

    if ReferralRedemption.objects.filter(referee=referee).exists():
        return None

    referrer_id = referee_profile.get_preference(REFERRED_BY_USER_ID_KEY)
    if not referrer_id:
        return None

    try:
        referrer = User.objects.get(pk=int(referrer_id))
    except (User.DoesNotExist, TypeError, ValueError):
        return None

    if referrer.pk == referee.pk:
        return None

    if _referrals_this_month(referrer) >= MONTHLY_REFERRAL_CAP:
        logger.info("Referral cap reached for referrer %s", referrer.pk)
        return None

    referrer_profile = Profile.objects.select_for_update().get(user=referrer)
    referrer_profile.credits = F("credits") + REFERRER_CREDITS
    referrer_profile.save(update_fields=["credits"])

    referee_profile.credits = F("credits") + REFEREE_BONUS_CREDITS
    referee_profile.save(update_fields=["credits"])

    redemption = ReferralRedemption.objects.create(
        referrer=referrer,
        referee=referee,
        referrer_credits=REFERRER_CREDITS,
        referee_credits=REFEREE_BONUS_CREDITS,
        batch_report=batch_report,
    )
    logger.info(
        "Referral redeemed: referrer=%s referee=%s batch=%s",
        referrer.pk,
        referee.pk,
        batch_report.pk,
    )
    return redemption
