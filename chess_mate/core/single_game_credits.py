"""Single-game analysis credit refunds on hard failure."""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.cache import cache
from django.db import transaction

from .models import Profile

logger = logging.getLogger(__name__)

_REFUND_CACHE_TTL = 60 * 60 * 24 * 7


def _refund_cache_key(user_id: int, game_id: int) -> str:
    return f"single_game_credit_refund:{user_id}:{game_id}"


def single_game_credits_amount() -> int:
    return int(getattr(settings, "SINGLE_GAME_ANALYSIS_CREDITS", 1))


def refund_single_game_credit_on_fail(user_id: int, game_id: int) -> int:
    """
    Refund credits when single-game analysis hard-fails after enqueue charge.
    Idempotent per user/game for one week.
    """
    if not user_id or not game_id:
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
        logger.warning("Cannot refund single-game credit — profile missing user_id=%s", user_id)
        return 0

    cache.set(cache_key, True, _REFUND_CACHE_TTL)
    logger.info("Refunded %s credit(s) for failed single-game analysis game_id=%s user_id=%s", amount, game_id, user_id)
    return amount
