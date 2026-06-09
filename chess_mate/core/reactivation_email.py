"""Inactive user reactivation email — max one per 30 days (SRG-27)."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, Optional

from django.contrib.auth.models import User
from django.core import mail
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from .email_send_log import (
    digest_already_sent_this_week,
    log_email_send,
    spaced_sent_in_last_days,
)
from .email_utils import get_frontend_base_url, is_email_configured
from .models import BatchAnalysisReport, EmailSendLog, Game, Profile
from .notification_preferences import user_wants_reactivation_email
from .stats_helpers import parse_last_dashboard_visit

logger = logging.getLogger(__name__)

REACTIVATION_SUBJECT = "Your games are waiting — run Batch Coach"
INACTIVITY_DAYS = 30
REACTIVATION_COOLDOWN_DAYS = 30


def _last_activity_at(user: User, profile: Profile):
    candidates = [user.last_login, profile.updated_at, profile.created_at]
    dash = parse_last_dashboard_visit(profile.preferences)
    if dash:
        candidates.append(dash)
    last_batch = (
        BatchAnalysisReport.objects.filter(user=user)
        .order_by("-updated_at")
        .values_list("updated_at", flat=True)
        .first()
    )
    if last_batch:
        candidates.append(last_batch)
    return max(dt for dt in candidates if dt is not None)


def reactivation_sent_recently(
    user: User, days: int = REACTIVATION_COOLDOWN_DAYS
) -> bool:
    since = timezone.now() - timedelta(days=days)
    return EmailSendLog.objects.filter(
        user=user,
        email_type=EmailSendLog.TYPE_REACTIVATION,
        sent_at__gte=since,
    ).exists()


def is_eligible_for_reactivation(user: User, profile: Profile) -> bool:
    if not user_wants_reactivation_email(user):
        return False
    if reactivation_sent_recently(user):
        return False
    if digest_already_sent_this_week(user) or spaced_sent_in_last_days(user, days=7):
        return False

    cutoff = timezone.now() - timedelta(days=INACTIVITY_DAYS)
    if _last_activity_at(user, profile) > cutoff:
        return False

    has_games = Game.objects.filter(user=user).exists()
    has_platform = bool(profile.chess_com_username or profile.lichess_username)
    return has_games or has_platform


@transaction.atomic
def send_reactivation_for_user(user: User, *, force: bool = False) -> bool:
    try:
        profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        return False

    if not force and not is_eligible_for_reactivation(user, profile):
        return False

    if not is_email_configured():
        logger.error(
            "Reactivation email not sent for %s: SMTP not configured", user.email
        )
        return False

    base = get_frontend_base_url()
    cta_url = f"{base}/batch-analysis"
    context = {
        "user": user,
        "cta_url": cta_url,
        "preferences_url": f"{base}/profile",
        "current_year": timezone.now().year,
    }

    try:
        html_body = render_to_string("email/reactivation.html", context)
    except Exception as template_error:
        logger.warning("Reactivation template render failed: %s", template_error)
        html_body = (
            f"Hi {user.username},\n\n"
            f"Your imported games are still in ChessMate. Run Batch Coach on 5–30 games:\n"
            f"{cta_url}\n"
        )

    mail.send_mail(
        subject=REACTIVATION_SUBJECT,
        message=strip_tags(str(html_body)),
        from_email=None,
        recipient_list=[user.email],
        html_message=str(html_body),
    )
    log_email_send(user, EmailSendLog.TYPE_REACTIVATION)
    logger.info("Reactivation email sent to %s", user.email)
    return True


def send_reactivation_emails() -> int:
    sent = 0
    users = User.objects.filter(email__gt="", is_active=True).select_related("profile")
    for user in users:
        try:
            if send_reactivation_for_user(user):
                sent += 1
        except Exception as exc:
            logger.exception("Reactivation failed for user %s: %s", user.pk, exc)
    return sent
