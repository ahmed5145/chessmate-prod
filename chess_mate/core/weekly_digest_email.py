"""Weekly coach digest email — max one per user per ISO week (SRG-15)."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.contrib.auth.models import User
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from .email_send_log import (
    coaching_email_budget_exceeded,
    digest_already_sent_this_week,
    iso_week_key,
    log_email_send,
    received_coaching_touchpoint_today,
)
from .email_utils import (
    email_template_context,
    get_frontend_base_url,
    is_email_configured,
    send_coaching_email,
)
from .fix_rate import build_dashboard_fix_rate
from .inbox_streak import get_inbox_streak_payload
from .models import BatchAnalysisReport, EmailSendLog, Game, Profile, UserNotification
from .notification_preferences import (
    user_wants_weekly_digest_email,
    user_wants_weekly_digest_notification,
)
from .notifications import create_user_notification
from .priority_inbox import get_priority_inbox_payload
from .single_game_streak import get_single_game_streak
from .stats_helpers import ANALYZED_GAME_Q, build_one_thing_today

logger = logging.getLogger(__name__)

DIGEST_SUBJECT = "Your weekly ChessMate coach check-in"


def _activity_since(user: User, days: int = 7) -> Dict[str, int]:
    since = timezone.now() - timedelta(days=days)
    new_batches = BatchAnalysisReport.objects.filter(
        user=user,
        status__in=["completed", "partial"],
        updated_at__gte=since,
    ).count()
    new_analyses = Game.objects.filter(user=user).filter(ANALYZED_GAME_Q).filter(updated_at__gte=since).count()
    return {"new_batches": new_batches, "new_analyses": new_analyses}


def build_weekly_digest_payload(user: User, profile: Profile) -> Dict[str, Any]:
    inbox = get_priority_inbox_payload(profile)
    pending_items = inbox.get("pending_items") or []
    pending_count = len(pending_items) if isinstance(pending_items, list) else 0

    inbox_streak = get_inbox_streak_payload(profile.preferences)
    single_streak = get_single_game_streak(profile.preferences)
    fix_rate = build_dashboard_fix_rate(user)
    activity = _activity_since(user)

    one_thing = build_one_thing_today(
        total_games=profile.total_games(),
        analyzed_games=Game.objects.filter(user=user).filter(ANALYZED_GAME_Q).count(),
        priority_inbox=inbox,
    )

    has_streak = bool(inbox_streak.get("show")) or int(single_streak.get("count") or 0) >= 2
    has_content = (
        pending_count > 0
        or has_streak
        or bool(fix_rate.get("show"))
        or activity["new_batches"] > 0
        or activity["new_analyses"] > 0
        or bool(one_thing.get("cta_to"))
    )

    sections: List[Dict[str, str]] = []
    if pending_count > 0:
        sections.append(
            {
                "label": "Coach inbox",
                "body": f"{pending_count} priorit{'y' if pending_count == 1 else 'ies'} waiting for review.",
            }
        )
    if inbox_streak.get("show"):
        sections.append(
            {
                "label": "Inbox streak",
                "body": inbox_streak.get("label") or f"{inbox_streak.get('count', 0)}-day coach streak",
            }
        )
    if int(single_streak.get("count") or 0) >= 2:
        sections.append(
            {
                "label": "Clean reviews",
                "body": f"{single_streak['count']}-game blunder-free streak",
            }
        )
    if fix_rate.get("show"):
        sections.append(
            {
                "label": "Progress",
                "body": fix_rate.get("headline") or "Patterns improved since your last batch.",
            }
        )
    if activity["new_batches"] or activity["new_analyses"]:
        parts = []
        if activity["new_batches"]:
            parts.append(f"{activity['new_batches']} new batch{'es' if activity['new_batches'] != 1 else ''}")
        if activity["new_analyses"]:
            parts.append(f"{activity['new_analyses']} depth-20 review{'s' if activity['new_analyses'] != 1 else ''}")
        sections.append({"label": "This week", "body": " · ".join(parts)})

    cta_href = "/dashboard"
    cta_label = "Open dashboard"
    if one_thing.get("cta_to"):
        cta_href = str(one_thing["cta_to"])
        cta_label = str(one_thing.get("cta_label") or "Do today's drill")

    return {
        "has_content": has_content,
        "pending_inbox_count": pending_count,
        "sections": sections,
        "one_thing_today": one_thing,
        "fix_rate": fix_rate if fix_rate.get("show") else None,
        "inbox_streak": inbox_streak,
        "single_game_streak": single_streak,
        "activity": activity,
        "cta_href": cta_href,
        "cta_label": cta_label,
        "title": "Your week with ChessMate Coach",
        "summary": sections[0]["body"] if sections else "",
    }


def _digest_notification_body(payload: Dict[str, Any]) -> str:
    parts = [row.get("body", "") for row in payload.get("sections") or [] if row.get("body")]
    return " · ".join(parts)[:500]


def seed_weekly_digest_notification(user: User, payload: Dict[str, Any], week_key: str) -> None:
    if not user_wants_weekly_digest_notification(user):
        return
    href = payload.get("cta_href") or "/dashboard"
    create_user_notification(
        user,
        notification_type=UserNotification.TYPE_WEEKLY_DIGEST,
        entity_id=f"digest:{week_key}",
        title=payload.get("title") or "Weekly coach check-in",
        body=_digest_notification_body(payload),
        href=href,
        meta={"week_key": week_key},
    )


@transaction.atomic
def send_weekly_digest_for_user(user: User, *, force: bool = False) -> bool:
    profile = getattr(user, "profile", None)
    if profile is None:
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            return False

    wants_email = user_wants_weekly_digest_email(user)
    wants_notification = user_wants_weekly_digest_notification(user)
    if not wants_email and not wants_notification:
        return False

    if digest_already_sent_this_week(user) and not force:
        return False

    if coaching_email_budget_exceeded(user) and not force:
        return False

    if received_coaching_touchpoint_today(user) and not force:
        return False

    payload = build_weekly_digest_payload(user, profile)
    if not payload.get("has_content"):
        return False

    week_key = iso_week_key()

    if wants_notification:
        seed_weekly_digest_notification(user, payload, week_key)

    if wants_email:
        if not is_email_configured():
            logger.error("Weekly digest not sent for %s: SMTP not configured", user.email)
            return bool(wants_notification)

        base_url = get_frontend_base_url()
        cta_href = payload.get("cta_href") or "/dashboard"
        if cta_href.startswith("/"):
            cta_url = f"{base_url}{cta_href}"
        else:
            cta_url = cta_href

        context = email_template_context(
            user=user,
            payload=payload,
            dashboard_url=f"{base_url}/dashboard",
            cta_url=cta_url,
            cta_label=payload.get("cta_label") or "Open dashboard",
            preferences_url=f"{base_url}/profile",
        )

        try:
            html_body = render_to_string("email/weekly_digest.html", context)
        except Exception as template_error:
            logger.warning("Weekly digest template render failed: %s", template_error)
            lines = [DIGEST_SUBJECT, ""]
            for section in payload.get("sections") or []:
                lines.append(f"{section.get('label')}: {section.get('body')}")
            lines.append(f"\n{context['cta_label']}: {cta_url}")
            html_body = "\n".join(lines)

        send_coaching_email(
            subject=DIGEST_SUBJECT,
            message=strip_tags(str(html_body)),
            recipient_list=[user.email],
            html_message=str(html_body),
            preferences_url=context["preferences_url"],
        )
        log_email_send(
            user,
            EmailSendLog.TYPE_WEEKLY_DIGEST,
            week_key=week_key,
            meta={"pending_inbox": payload.get("pending_inbox_count")},
        )
        logger.info("Weekly digest sent to %s", user.email)

    return True


def send_weekly_digests() -> int:
    """Send weekly digests to all opted-in users. Returns send count."""
    sent = 0
    users = User.objects.filter(email__gt="").select_related("profile")
    for user in users:
        try:
            if send_weekly_digest_for_user(user):
                sent += 1
        except Exception as exc:
            logger.exception("Weekly digest failed for user %s: %s", user.pk, exc)
    return sent
