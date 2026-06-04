"""Email notifications for batch analysis completion."""

import logging

from django.conf import settings
from django.core import mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .email_utils import get_frontend_base_url, is_email_configured

logger = logging.getLogger(__name__)


def send_batch_complete_email(user, batch_report) -> bool:
    """
    Notify the user that their batch coach report is ready.
    Returns True if sent (or skipped because email disabled), False on send failure.
    """
    if not is_email_configured():
        logger.info("Batch complete email skipped: SMTP not configured")
        return False

    email = getattr(user, "email", None)
    if not email:
        return False

    batch_id = batch_report.pk
    report_url = f"{get_frontend_base_url()}/batch-report/{batch_id}"
    summary = batch_report.batch_summary or {}
    status = batch_report.status

    try:
        html_body = render_to_string(
            "email/batch_complete.html",
            {
                "user": user,
                "batch_id": batch_id,
                "games_count": batch_report.games_count,
                "status": status,
                "report_url": report_url,
                "overall_eval_stability": summary.get("overall_eval_stability")
                or summary.get("overall_accuracy"),
                "overall_acpl": summary.get("overall_acpl"),
            },
        )
    except Exception as exc:
        logger.warning("Batch complete template render failed: %s", exc)
        html_body = (
            f"Your ChessMate batch analysis ({batch_report.games_count} games) is ready.\n"
            f"View report: {report_url}\n"
        )

    subject = "Your ChessMate batch coach report is ready"
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
