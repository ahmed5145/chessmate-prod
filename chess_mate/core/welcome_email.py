"""One-time welcome email after email verification (SRG-22)."""

from __future__ import annotations

import logging

from django.conf import settings
from django.core import mail
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from .email_utils import email_template_context, get_frontend_base_url, is_email_configured
from .models import Profile

logger = logging.getLogger(__name__)

WELCOME_EMAIL_SENT_KEY = "welcome_email_sent_at"


def welcome_email_already_sent(profile: Profile) -> bool:
    return bool(profile.get_preference(WELCOME_EMAIL_SENT_KEY))


@transaction.atomic
def send_welcome_email_once(user, profile: Profile, request=None) -> bool:
    """
    Send the onboarding welcome email at most once per user.
    Acts as the lightweight WelcomeEmailLog via profile.preferences.
    """
    locked_profile = Profile.objects.select_for_update().get(pk=profile.pk)

    if not locked_profile.email_verified:
        return False
    if welcome_email_already_sent(locked_profile):
        return False
    if not is_email_configured():
        logger.error("Welcome email not sent for %s: SMTP not configured", user.email)
        return False

    signup_bonus_credits = int(getattr(settings, "SIGNUP_BONUS_CREDITS", 15) or 15)
    import_url = f"{get_frontend_base_url(request)}/fetch-games"
    batch_url = f"{get_frontend_base_url(request)}/batch-analysis"
    credit_label = "credit" if signup_bonus_credits == 1 else "credits"

    context = email_template_context(
        user=user,
        signup_bonus_credits=signup_bonus_credits,
        credit_label=credit_label,
        import_url=import_url,
        batch_url=batch_url,
    )

    try:
        html_body = render_to_string("email/welcome.html", context)
    except Exception as template_error:
        logger.warning("Welcome template render failed: %s", template_error)
        html_body = (
            f"Welcome to ChessMate, {user.username}!\n\n"
            f"You have {signup_bonus_credits} free {credit_label}.\n"
            f"1) Connect Chess.com or Lichess\n"
            f"2) Import games: {import_url}\n"
            f"3) Run Batch Coach on 5–30 games: {batch_url}\n"
        )

    mail.send_mail(
        subject="Welcome to ChessMate — your coach is ready",
        message=strip_tags(str(html_body)),
        from_email=None,
        recipient_list=[user.email],
        html_message=str(html_body),
    )

    locked_profile.set_preference(WELCOME_EMAIL_SENT_KEY, timezone.now().isoformat())
    logger.info("Welcome email sent to %s", user.email)
    return True
