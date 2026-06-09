"""Spaced-repetition moment reminder email — max one per user per 7 days (SRG-13)."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from django.contrib.auth.models import User
from django.core import mail
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from .email_send_log import (
    digest_already_sent_this_week,
    log_email_send,
    received_coaching_touchpoint_today,
    spaced_sent_in_last_days,
)
from .email_utils import get_frontend_base_url, is_email_configured
from .models import EmailSendLog, Game, GameAnalysis, Profile, SpacedReminderLog
from .notification_preferences import user_wants_spaced_repetition_email
from .stats_helpers import ANALYZED_GAME_Q

logger = logging.getLogger(__name__)

SWING_THRESHOLD = 0.5
MOMENT_COOLDOWN_DAYS = 30
COMPLETION_COOLDOWN_HOURS = 48


def moment_key(game_id: int, move_number: int) -> str:
    return f"game:{game_id}:move:{move_number}"


def _moment_swing(moment: Dict[str, Any]) -> float:
    for key in ("eval_swing", "swing", "eval_drop"):
        raw = moment.get(key)
        if raw is None:
            continue
        try:
            return abs(float(raw))
        except (TypeError, ValueError):
            continue
    return 0.0


def _extract_moments(analysis: GameAnalysis) -> List[Dict[str, Any]]:
    moments: List[Dict[str, Any]] = []
    for source in (
        getattr(analysis, "feedback", None),
        getattr(analysis, "analysis_data", None),
    ):
        if not isinstance(source, dict):
            continue
        coaching = source.get("coaching")
        if isinstance(coaching, dict):
            raw = coaching.get("critical_moments")
            if isinstance(raw, list):
                moments.extend(row for row in raw if isinstance(row, dict))
        raw = source.get("critical_moments")
        if isinstance(raw, list):
            moments.extend(row for row in raw if isinstance(row, dict))
    return moments


def _analysis_completion_sent_recently(user: User) -> bool:
    since = timezone.now() - timedelta(hours=COMPLETION_COOLDOWN_HOURS)
    return EmailSendLog.objects.filter(
        user=user,
        email_type=EmailSendLog.TYPE_ANALYSIS_COMPLETION,
        sent_at__gte=since,
    ).exists()


def _moment_sent_recently(user: User, key: str, days: int = MOMENT_COOLDOWN_DAYS) -> bool:
    since = timezone.now() - timedelta(days=days)
    return SpacedReminderLog.objects.filter(
        user=user,
        moment_key=key,
        sent_at__gte=since,
    ).exists()


def find_best_spaced_moment(user: User) -> Optional[Tuple[Game, Dict[str, Any]]]:
    games = (
        Game.objects.filter(user=user)
        .filter(ANALYZED_GAME_Q)
        .order_by("-updated_at")[:20]
    )
    best: Optional[Tuple[Game, Dict[str, Any], float]] = None
    stale_cutoff = timezone.now() - timedelta(days=7)

    for game in games:
        try:
            analysis = GameAnalysis.objects.get(game=game)
        except GameAnalysis.DoesNotExist:
            continue
        if analysis.updated_at and analysis.updated_at >= stale_cutoff:
            continue

        for moment in _extract_moments(analysis):
            swing = _moment_swing(moment)
            move_number = moment.get("move_number")
            if swing < SWING_THRESHOLD or move_number is None:
                continue
            key = moment_key(game.id, int(move_number))
            if _moment_sent_recently(user, key):
                continue
            if best is None or swing > best[2]:
                best = (game, moment, swing)

    if best is None:
        return None
    return best[0], best[1]


def build_spaced_email_subject(moment: Dict[str, Any]) -> str:
    move_number = moment.get("move_number")
    if move_number:
        return f"Still thinking about move {move_number}?"
    return "Still thinking about that critical moment?"


@transaction.atomic
def send_spaced_repetition_for_user(user: User, *, force: bool = False) -> bool:
    if not user_wants_spaced_repetition_email(user):
        return False

    if not force:
        if digest_already_sent_this_week(user):
            return False
        if spaced_sent_in_last_days(user, days=7):
            return False
        if _analysis_completion_sent_recently(user):
            return False
        if received_coaching_touchpoint_today(user):
            return False

    match = find_best_spaced_moment(user)
    if not match:
        return False

    game, moment = match
    move_number = int(moment["move_number"])
    key = moment_key(game.id, move_number)

    if not force and _moment_sent_recently(user, key):
        return False

    if not is_email_configured():
        logger.error("Spaced reminder not sent for %s: SMTP not configured", user.email)
        return False

    base = get_frontend_base_url()
    review_url = f"{base}/game/{game.id}/analysis?mode=review&move={move_number}"
    subject = build_spaced_email_subject(moment)
    swing = _moment_swing(moment)

    context = {
        "user": user,
        "game_id": game.id,
        "move_number": move_number,
        "review_url": review_url,
        "swing": swing,
        "preferences_url": f"{base}/profile",
        "current_year": timezone.now().year,
    }

    try:
        html_body = render_to_string("email/spaced_moment.html", context)
    except Exception as template_error:
        logger.warning("Spaced moment template render failed: %s", template_error)
        html_body = (
            f"{subject}\n\n"
            f"Replay the moment that swung your game: {review_url}\n"
        )

    mail.send_mail(
        subject=subject,
        message=strip_tags(str(html_body)),
        from_email=None,
        recipient_list=[user.email],
        html_message=str(html_body),
    )

    SpacedReminderLog.objects.create(user=user, moment_key=key)
    log_email_send(
        user,
        EmailSendLog.TYPE_SPACED_MOMENT,
        week_key=key,
        meta={"game_id": game.id, "move_number": move_number},
    )
    logger.info("Spaced reminder sent to %s for %s", user.email, key)
    return True


def send_spaced_repetition_reminders() -> int:
    sent = 0
    users = User.objects.filter(email__gt="").select_related("profile")
    for user in users:
        try:
            if send_spaced_repetition_for_user(user):
                sent += 1
        except Exception as exc:
            logger.exception("Spaced reminder failed for user %s: %s", user.pk, exc)
    return sent
