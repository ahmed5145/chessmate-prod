"""Email notifications for single-game analysis completion."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .email_send_log import coaching_email_budget_exceeded, log_email_send
from .email_utils import (get_frontend_base_url, is_email_configured,
                          send_coaching_email)
from .models import EmailSendLog
from .notification_preferences import user_wants_analysis_completion_email
from .stats_helpers import build_single_game_context

logger = logging.getLogger(__name__)

DEFAULT_SINGLE_GAME_EMAIL_SUBJECT = "Your ChessMate depth-20 game review is ready"


def _coaching_payload(feedback: Any, analysis_data: Any) -> Dict[str, Any]:
    coaching: Dict[str, Any] = {}
    if isinstance(analysis_data, dict):
        nested = analysis_data.get("coaching")
        if isinstance(nested, dict):
            coaching.update(nested)
    if isinstance(feedback, dict):
        nested = feedback.get("coaching")
        if isinstance(nested, dict):
            coaching.update(nested)
        for key in ("headline", "takeaway", "executive_summary", "do_today"):
            if feedback.get(key) and key not in coaching:
                coaching[key] = feedback[key]
    return coaching


def _coach_snippet(coaching: Dict[str, Any], feedback: Any, analysis_data: Any) -> str:
    for key in ("takeaway", "executive_summary", "do_today"):
        value = coaching.get(key)
        if value:
            return str(value)[:220]

    if isinstance(feedback, dict):
        for key in ("takeaway", "executive_summary", "do_today"):
            value = feedback.get(key)
            if value:
                return str(value)[:220]

    if isinstance(analysis_data, dict):
        nested_feedback = analysis_data.get("feedback")
        if isinstance(nested_feedback, dict):
            for key in ("takeaway", "executive_summary"):
                value = nested_feedback.get(key)
                if value:
                    return str(value)[:220]

    return ""


def _email_subject(headline: str, worst_moment: Dict[str, Any]) -> str:
    if headline:
        return str(headline)[:80]
    move_number = worst_moment.get("move_number")
    if move_number:
        return f"Move {move_number} swung your game"
    return DEFAULT_SINGLE_GAME_EMAIL_SUBJECT


def _build_review_urls(game_id: int, move_number: Optional[int]) -> Dict[str, str]:
    base = f"{get_frontend_base_url()}/game/{game_id}/analysis?mode=review"
    deep_review_url = base
    if move_number:
        deep_review_url = f"{base}&move={move_number}"
    return {"report_url": base, "deep_review_url": deep_review_url}


def _player_accuracy(
    analysis_model: Any, game_context: Dict[str, Any]
) -> Optional[float]:
    metrics = {}
    if hasattr(analysis_model, "metrics"):
        metrics = analysis_model.metrics or {}
    if not metrics and hasattr(analysis_model, "analysis_data"):
        data = (
            analysis_model.analysis_data
            if isinstance(analysis_model.analysis_data, dict)
            else {}
        )
        metrics = (
            data.get("metrics", {}) if isinstance(data.get("metrics"), dict) else {}
        )

    summary = metrics.get("summary", metrics) if isinstance(metrics, dict) else {}
    overall = (
        summary.get("overall", {}) if isinstance(summary.get("overall"), dict) else {}
    )
    accuracy = overall.get("accuracy")

    player_color = game_context.get("player_color")
    if (
        accuracy is None
        and player_color == "white"
        and getattr(analysis_model, "accuracy_white", None) is not None
    ):
        accuracy = analysis_model.accuracy_white
    if (
        accuracy is None
        and player_color == "black"
        and getattr(analysis_model, "accuracy_black", None) is not None
    ):
        accuracy = analysis_model.accuracy_black

    if accuracy is None:
        return None
    try:
        value = float(accuracy)
    except (TypeError, ValueError):
        return None
    if 0 < value <= 1:
        return round(value * 100, 1)
    return round(value, 1)


def _critical_moments(
    feedback: Any, analysis_data: Any, coaching: Dict[str, Any]
) -> list:
    moments = coaching.get("critical_moments") or []
    if not moments and isinstance(analysis_data, dict):
        moments = analysis_data.get("critical_moments") or []
    if not moments and isinstance(feedback, dict):
        moments = feedback.get("critical_moments") or []
    if not moments and isinstance(analysis_data, dict):
        nested = analysis_data.get("feedback")
        if isinstance(nested, dict):
            moments = nested.get("critical_moments") or []
    return moments if isinstance(moments, list) else []


def _worst_moment(
    feedback: Any, analysis_data: Any, coaching: Dict[str, Any]
) -> Dict[str, Any]:
    moments = _critical_moments(feedback, analysis_data, coaching)
    if not moments:
        return {}
    first = moments[0] if isinstance(moments[0], dict) else {}
    return {
        "move_number": first.get("move_number"),
        "played_move": first.get("played_move"),
        "best_move": first.get("best_move"),
        "eval_swing": first.get("eval_swing"),
        "type": first.get("type"),
    }


def send_single_game_complete_email(user, game, analysis_model) -> bool:
    """
    Notify the user that their single-game depth-20 review is ready.
    Returns True if sent, False if skipped or failed.
    """
    if not getattr(settings, "SINGLE_GAME_SEND_COMPLETE_EMAIL", True):
        logger.info(
            "Single-game complete email skipped: SINGLE_GAME_SEND_COMPLETE_EMAIL disabled"
        )
        return False

    if not is_email_configured():
        logger.info("Single-game complete email skipped: SMTP not configured")
        return False

    if not user_wants_analysis_completion_email(user):
        logger.info("Single-game complete email skipped: user opted out")
        return False

    if coaching_email_budget_exceeded(user):
        logger.info(
            "Single-game complete email skipped: weekly coaching email budget reached"
        )
        return False

    email = getattr(user, "email", None)
    if not email:
        return False

    profile = getattr(user, "profile", None)
    game_context = build_single_game_context(game, profile)
    feedback = getattr(analysis_model, "feedback", None)
    analysis_data = getattr(analysis_model, "analysis_data", None)
    coaching = _coaching_payload(feedback, analysis_data)
    coach_snippet = _coach_snippet(coaching, feedback, analysis_data)
    worst_moment = _worst_moment(feedback, analysis_data, coaching)
    accuracy_pct = _player_accuracy(analysis_model, game_context)
    headline = str(coaching.get("headline") or "").strip()
    email_subject = _email_subject(headline, worst_moment)

    urls = _build_review_urls(game.id, worst_moment.get("move_number"))
    report_url = urls["report_url"]
    deep_review_url = urls["deep_review_url"]

    try:
        html_body = render_to_string(
            "email/single_game_complete.html",
            {
                "user": user,
                "game_id": game.id,
                "game_context": game_context,
                "report_url": report_url,
                "deep_review_url": deep_review_url,
                "coach_snippet": coach_snippet,
                "headline": headline or email_subject,
                "accuracy_pct": accuracy_pct,
                "worst_moment_move": worst_moment.get("move_number"),
                "worst_moment_played": worst_moment.get("played_move"),
                "worst_moment_best": worst_moment.get("best_move"),
                "worst_moment_swing": worst_moment.get("eval_swing"),
                "worst_moment_type": worst_moment.get("type"),
            },
        )
    except Exception as exc:
        logger.warning("Single-game complete template render failed: %s", exc)
        opponent = game_context.get("opponent") or "your opponent"
        html_body = (
            f"Your ChessMate depth-20 review vs {opponent} is ready.\n"
            f"View report: {report_url}\n"
        )

    base = get_frontend_base_url()
    try:
        send_coaching_email(
            subject=email_subject,
            message=strip_tags(str(html_body)),
            recipient_list=[email],
            html_message=str(html_body),
            preferences_url=f"{base}/profile",
        )
        log_email_send(
            user,
            EmailSendLog.TYPE_ANALYSIS_COMPLETION,
            meta={"game_id": game.id, "channel": "single_game"},
        )
        logger.info("Single-game complete email sent to %s for game %s", email, game.id)
        return True
    except Exception as exc:
        logger.error(
            "Failed to send single-game complete email: %s", exc, exc_info=True
        )
        return False
