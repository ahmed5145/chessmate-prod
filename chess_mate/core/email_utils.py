"""Helpers for outbound email configuration checks."""

from django.conf import settings


def is_email_configured() -> bool:
    """Return True when Django can send mail (SMTP creds or console backend in dev)."""
    backend = getattr(settings, "EMAIL_BACKEND", "") or ""
    if "console" in backend.lower():
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


def password_reset_unavailable_message() -> str:
    return (
        "Password reset email is temporarily unavailable. "
        "Please try again later or contact support."
    )
