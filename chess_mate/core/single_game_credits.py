"""Single-game analysis credit refunds on hard failure."""

from __future__ import annotations

import logging
from typing import Any, Optional

from django.conf import settings
from django.core.cache import cache
from django.db import transaction

from .models import Profile

logger = logging.getLogger(__name__)

PREF_FIRST_FREE_USED = "single_game_free_used"

_REFUND_CACHE_TTL = 60 * 60 * 24 * 7
_CHARGE_CACHE_TTL = 60 * 60 * 24 * 7


def _refund_cache_key(user_id: int, game_id: int) -> str:
    return f"single_game_credit_refund:{user_id}:{game_id}"


def _charge_cache_key(user_id: int, game_id: int) -> str:
    return f"single_game_credit_charged:{user_id}:{game_id}"


def single_game_credits_amount() -> int:
    return int(getattr(settings, "SINGLE_GAME_ANALYSIS_CREDITS", 1))


def mark_single_game_credit_charged(user_id: int, game_id: int) -> None:
    if user_id and game_id:
        cache.set(_charge_cache_key(user_id, game_id), True, _CHARGE_CACHE_TTL)


def was_single_game_credit_charged(user_id: int, game_id: int) -> bool:
    if not user_id or not game_id:
        return False
    return bool(cache.get(_charge_cache_key(user_id, game_id)))


def has_used_first_single_game_free(profile: Profile) -> bool:
    preferences = profile.preferences if isinstance(profile.preferences, dict) else {}
    return bool(preferences.get(PREF_FIRST_FREE_USED))


def qualifies_for_first_single_game_free(profile: Optional[Profile]) -> bool:
    if profile is None:
        return False
    if not getattr(settings, "SINGLE_GAME_FIRST_FREE", True):
        return False
    return not has_used_first_single_game_free(profile)


def mark_first_single_game_free_used(profile: Profile) -> None:
    preferences = (
        dict(profile.preferences) if isinstance(profile.preferences, dict) else {}
    )
    preferences[PREF_FIRST_FREE_USED] = True
    profile.preferences = preferences
    profile.save(update_fields=["preferences"])


def resolve_single_game_credit_waiver(
    user,
    game_id: int,
    profile: Optional[Profile],
    *,
    from_batch: bool = False,
    batch_id: Any = None,
    force_reanalyze: bool = False,
) -> str:
    """
    Return waiver reason: 'batch', 'first_free', or '' (paid).
    Re-analyze always requires payment.
    """
    if force_reanalyze:
        return ""

    if (
        from_batch
        and batch_id not in (None, "")
        and getattr(settings, "SINGLE_GAME_FREE_FROM_BATCH", True)
    ):
        from .analysis.single_game_context import game_qualifies_for_batch_waiver

        if game_qualifies_for_batch_waiver(user, game_id, batch_id):
            return "batch"

    if qualifies_for_first_single_game_free(profile):
        return "first_free"

    return ""


def charge_single_game_credit(
    user,
    game_id: int,
    profile: Optional[Profile],
    *,
    waiver: str = "",
) -> int:
    """Deduct one credit when not waived; return credits charged (0 or 1)."""
    if user.is_staff or waiver:
        if waiver == "first_free" and profile is not None:
            mark_first_single_game_free_used(profile)
        return 0

    if profile is None:
        profile = Profile.objects.get(user=user)

    profile.credits = max(0, profile.credits - 1)
    profile.save(update_fields=["credits"])
    mark_single_game_credit_charged(user.id, game_id)
    return 1


def refund_single_game_credit_on_fail(user_id: int, game_id: int) -> int:
    """
    Refund credits when single-game analysis hard-fails after enqueue charge.
    Idempotent per user/game for one week.
    """
    if not user_id or not game_id:
        return 0

    if not was_single_game_credit_charged(user_id, game_id):
        return 0

    cache_key = _refund_cache_key(user_id, game_id)
    if cache.get(cache_key):
        return 0

    amount = single_game_credits_amount()
    if amount <= 0:
        return 0

    try:
        with transaction.atomic():
            profile = Profile.objects.select_for_update().get(user_id=user_id)
            profile.credits += amount
            profile.save(update_fields=["credits"])
    except Profile.DoesNotExist:
        logger.warning(
            "Cannot refund single-game credit — profile missing user_id=%s", user_id
        )
        return 0

    cache.set(cache_key, True, _REFUND_CACHE_TTL)
    logger.info(
        "Refunded %s credit(s) for failed single-game analysis game_id=%s user_id=%s",
        amount,
        game_id,
        user_id,
    )
    return amount
