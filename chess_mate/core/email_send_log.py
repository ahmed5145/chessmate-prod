"""Shared coaching email budget and idempotency (SRG-15/13/27)."""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .models import EmailSendLog, UserNotification

COACHING_EMAIL_TYPES = {
    EmailSendLog.TYPE_WEEKLY_DIGEST,
    EmailSendLog.TYPE_SPACED_MOMENT,
    EmailSendLog.TYPE_ANALYSIS_COMPLETION,
}

MAX_COACHING_EMAILS_PER_7_DAYS = 2
COACHING_EMAIL_WINDOW_DAYS = 7

COMPLETION_NOTIFICATION_TYPES = {
    UserNotification.TYPE_SINGLE_COMPLETE,
    UserNotification.TYPE_BATCH_COMPLETE,
}


def iso_week_key(when=None) -> str:
    moment = when or timezone.now()
    year, week, _ = moment.isocalendar()
    return f"{year:04d}-W{week:02d}"


def digest_already_sent_this_week(user: User, when=None) -> bool:
    week_key = iso_week_key(when)
    return EmailSendLog.objects.filter(
        user=user,
        email_type=EmailSendLog.TYPE_WEEKLY_DIGEST,
        week_key=week_key,
    ).exists()


def spaced_sent_in_last_days(user: User, days: int = 7) -> bool:
    since = timezone.now() - timedelta(days=days)
    return EmailSendLog.objects.filter(
        user=user,
        email_type=EmailSendLog.TYPE_SPACED_MOMENT,
        sent_at__gte=since,
    ).exists()


def coaching_emails_in_last_days(user: User, days: int = COACHING_EMAIL_WINDOW_DAYS) -> int:
    since = timezone.now() - timedelta(days=days)
    return EmailSendLog.objects.filter(
        user=user,
        email_type__in=COACHING_EMAIL_TYPES,
        sent_at__gte=since,
    ).count()


def coaching_email_budget_exceeded(
    user: User,
    *,
    days: int = COACHING_EMAIL_WINDOW_DAYS,
    limit: int = MAX_COACHING_EMAILS_PER_7_DAYS,
) -> bool:
    """True when user already received the weekly coaching email cap."""
    return coaching_emails_in_last_days(user, days=days) >= limit


def user_active_within_hours(user: User, hours: int = 72) -> bool:
    last_login = getattr(user, "last_login", None)
    if last_login is None:
        return False
    return last_login >= timezone.now() - timedelta(hours=hours)


def received_coaching_touchpoint_today(user: User) -> bool:
    start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if EmailSendLog.objects.filter(
        user=user,
        email_type__in=COACHING_EMAIL_TYPES,
        sent_at__gte=start,
    ).exists():
        return True

    return UserNotification.objects.filter(
        user=user,
        notification_type__in=COMPLETION_NOTIFICATION_TYPES,
        created_at__gte=start,
    ).exists()


@transaction.atomic
def log_email_send(
    user: User,
    email_type: str,
    *,
    week_key: str = "",
    meta: Optional[dict] = None,
) -> EmailSendLog:
    return EmailSendLog.objects.create(
        user=user,
        email_type=email_type,
        week_key=week_key or "",
        meta=meta or {},
    )
