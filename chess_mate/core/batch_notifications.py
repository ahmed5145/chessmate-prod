"""Email notifications for batch analysis completion."""

import logging

from django.conf import settings
from django.core import mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .batch_deep_links import build_worst_moment_deep_review_url, worst_moment_summary
from .batch_labels import BATCH_COACH_EMAIL_SUBJECT
from .email_utils import email_template_context, get_frontend_base_url, is_email_configured
from .notification_preferences import user_wants_analysis_completion_email

logger = logging.getLogger(__name__)


def send_batch_complete_email(user, batch_report) -> bool:
    """
    Notify the user that their batch coach report is ready.
    Returns True if sent (or skipped because email disabled), False on send failure.
    """
    if not is_email_configured():
        logger.info("Batch complete email skipped: SMTP not configured")
        return False

    if not user_wants_analysis_completion_email(user):
        logger.info("Batch complete email skipped: user opted out")
        return False

    email = getattr(user, "email", None)
    if not email:
        return False

    batch_id = batch_report.pk
    report_url = f"{get_frontend_base_url()}/batch-report/{batch_id}"
    summary = batch_report.batch_summary or {}
    status = batch_report.status
    coaching = batch_report.coaching_report if isinstance(batch_report.coaching_report, dict) else {}
    coach_snippet = (coaching.get("executive_summary") or "")[:220]
    deep_review_url = build_worst_moment_deep_review_url(batch_report)
    worst_moment = worst_moment_summary(batch_report)
    accuracy_pct = summary.get("overall_accuracy_pct")
    stability_raw = summary.get("overall_eval_stability") or summary.get("overall_accuracy")
    stability_pct = round(float(stability_raw) * 100, 1) if stability_raw is not None else None

    try:
        html_body = render_to_string(
            "email/batch_complete.html",
            email_template_context(
                user=user,
                batch_id=batch_id,
                games_count=batch_report.games_count,
                status=status,
                report_url=report_url,
                coach_snippet=coach_snippet,
                overall_accuracy_pct=accuracy_pct,
                stability_pct=stability_pct,
                deep_review_url=deep_review_url,
                worst_moment_move=worst_moment.get("move_number"),
                worst_moment_played=worst_moment.get("played_move"),
            ),
        )
    except Exception as exc:
        logger.warning("Batch complete template render failed: %s", exc)
        html_body = (
            f"Your ChessMate Batch Coach report ({batch_report.games_count} games) is ready.\n"
            f"View report: {report_url}\n"
        )

    subject = BATCH_COACH_EMAIL_SUBJECT
    try:
        mail.send_mail(
            subject=subject,
            message=strip_tags(str(html_body)),
            from_email=None,
            recipient_list=[email],
            html_message=str(html_body),
        )
        logger.info("Batch complete email sent to %s for batch %s", email, batch_id)
        return True
    except Exception as exc:
        logger.error("Failed to send batch complete email: %s", exc, exc_info=True)
        return False
