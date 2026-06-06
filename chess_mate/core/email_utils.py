"""Helpers for outbound email configuration checks."""

import os

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
    return "Verification email is temporarily unavailable. " "Please try again later or contact support."
