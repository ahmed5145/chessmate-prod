"""Batch analysis credit charge and refund helpers."""

import logging

from django.conf import settings
from django.db import transaction

from .models import BatchAnalysisReport, Profile

logger = logging.getLogger(__name__)


def batch_credits_required(games_count: int) -> int:
    per_game = int(getattr(settings, "BATCH_CREDITS_PER_GAME", 1))
    return max(0, int(games_count)) * per_game


def refund_amount_for_report(batch_report: BatchAnalysisReport) -> int:
    if batch_report.credits_charged:
        return int(batch_report.credits_charged)
    return batch_credits_required(batch_report.games_count)


def refund_batch_credits_on_hard_fail(batch_report: BatchAnalysisReport) -> int:
    """
    Refund credits when a batch hard-fails (status=failed).
    Idempotent — safe to call multiple times. Returns amount refunded.
    """
    if batch_report.status != "failed":
        return 0

    with transaction.atomic():
        locked = BatchAnalysisReport.objects.select_for_update().get(pk=batch_report.pk)
        if locked.credits_refunded:
            return 0

        amount = refund_amount_for_report(locked)
        if amount <= 0:
            locked.credits_refunded = True
            locked.save(update_fields=["credits_refunded", "updated_at"])
            return 0

        profile = Profile.objects.select_for_update().get(user_id=locked.user_id)
        profile.credits += amount
        profile.save(update_fields=["credits"])

        locked.credits_refunded = True
        locked.save(update_fields=["credits_refunded", "updated_at"])

    logger.info(
        "Refunded %s credits for failed batch id=%s user_id=%s",
        amount,
        batch_report.pk,
        batch_report.user_id,
    )
    return amount
