"""Helpers for outbound email configuration checks."""

import os

from django.conf import settings


def is_email_configured() -> bool:
    """Return True when Django can send mail (SMTP creds or console backend in dev)."""
    if getattr(settings, "TESTING", False):
        return True

    backend = getattr(settings, "EMAIL_BACKEND", "") or ""
    if "console" in backend.lower() or "locmem" in backend.lower():
        return True

    host_user = (getattr(settings, "EMAIL_HOST_USER", None) or "").strip()
    host_password = (getattr(settings, "EMAIL_HOST_PASSWORD", None) or "").strip()
    from_email = (getattr(settings, "DEFAULT_FROM_EMAIL", None) or "").strip()

    if not host_user or not host_password:
        return False

    # SMTP backends need a from address; fall back to host user when unset.
    if "smtp" in backend.lower() and not (from_email or host_user):
        return False

    return True


def get_support_email() -> str:
    """Public support inbox from EB SUPPORT_EMAIL, else DEFAULT_FROM_EMAIL."""
    support = (getattr(settings, "SUPPORT_EMAIL", None) or "").strip()
    if support:
        return support
    return (getattr(settings, "DEFAULT_FROM_EMAIL", None) or "").strip()


def email_template_context(**extra) -> dict:
    """Shared template context for outbound mail (support contact from settings)."""
    from django.utils import timezone

    context = {
        "support_email": get_support_email(),
        "current_year": timezone.now().year,
    }
    context.update(extra)
    return context


def password_reset_unavailable_message() -> str:
    support = get_support_email()
    if support:
        return "Password reset email is temporarily unavailable. " f"Please try again later or contact us at {support}."
    return "Password reset email is temporarily unavailable. " "Please try again later or contact support."


def password_reset_expiry_hours() -> int:
    """Hours until reset links expire (matches PASSWORD_RESET_TIMEOUT)."""
    timeout_seconds = int(getattr(settings, "PASSWORD_RESET_TIMEOUT", 60 * 60 * 24))
    return max(1, timeout_seconds // 3600)


def get_frontend_base_url(request=None) -> str:
    """Public SPA origin for links in emails (FRONTEND_URL or current request host)."""
    explicit = (getattr(settings, "FRONTEND_URL", None) or os.environ.get("FRONTEND_URL") or "").strip()
    if explicit:
        return explicit.rstrip("/")

    if request is not None:
        scheme = "https" if request.is_secure() else "http"
        return f"{scheme}://{request.get_host()}"

    return "http://localhost:3000"


def build_password_reset_url(uid: str, token: str, request=None) -> str:
    base = get_frontend_base_url(request)
    return f"{base}/reset-password/{uid}/{token}"


def get_api_base_url(request=None) -> str:
    """Origin for API links in emails (verify-email hits Django, not the SPA)."""
    explicit = (getattr(settings, "API_BASE_URL", None) or os.environ.get("API_BASE_URL") or "").strip()
    if explicit:
        return explicit.rstrip("/")

    if request is not None:
        scheme = "https" if request.is_secure() else "http"
        return f"{scheme}://{request.get_host()}"

    return get_frontend_base_url(request)


def build_verification_url(uidb64: str, token: str, request=None) -> str:
    base = get_api_base_url(request)
    return f"{base}/api/v1/auth/verify-email/{uidb64}/{token}/"


def verification_email_unavailable_message() -> str:
    support = get_support_email()
    if support:
        return "Verification email is temporarily unavailable. " f"Please try again later or contact us at {support}."
    return "Verification email is temporarily unavailable. " "Please try again later or contact support."


def coaching_email_headers(preferences_url: str | None = None) -> dict[str, str]:
    """List-Unsubscribe headers for opt-in coaching mail (SRG-13/15)."""
    if not preferences_url:
        return {}
    return {
        "List-Unsubscribe": f"<{preferences_url}>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }


def send_coaching_email(
    *,
    subject: str,
    message: str,
    recipient_list: list[str],
    html_message: str | None = None,
    preferences_url: str | None = None,
) -> int:
    """Send coaching email with optional HTML body and unsubscribe headers."""
    from django.core.mail import EmailMultiAlternatives

    headers = coaching_email_headers(preferences_url)
    email = EmailMultiAlternatives(
        subject=subject,
        body=message,
        from_email=None,
        to=recipient_list,
        headers=headers,
    )
    if html_message:
        email.attach_alternative(html_message, "text/html")
    return email.send()
