"""
Harden Django admin access for public deployments.

Best practices applied here:
- Non-default admin URL path (configured via DJANGO_ADMIN_PATH)
- Legacy /admin/ hidden in production (404, no redirect leak)
- Optional IP allowlist (ADMIN_ALLOWED_IPS)
- Stricter rate limiting on admin login POSTs
"""

from __future__ import annotations

import logging
import re
from typing import Optional, Set

from django.conf import settings
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseNotFound,
)
from django.utils.deprecation import MiddlewareMixin

from .cache import cache_get, cache_set

logger = logging.getLogger(__name__)

_BLOCKED_ADMIN_PATHS = frozenset(
    {
        "admin",
        "administrator",
        "django-admin",
        "django",
        "login",
        "wp-admin",
    }
)


def normalize_admin_path(raw: str) -> str:
    """Return a URL segment (no leading/trailing slashes) for the admin site."""
    return (raw or "").strip().strip("/")


def resolve_admin_path(*, is_production: bool, testing: bool, configured: str) -> str:
    """Validate and return the admin path for the current environment."""
    path = normalize_admin_path(configured)

    if is_production and not testing:
        if not path:
            raise ValueError(
                "DJANGO_ADMIN_PATH must be set in production (e.g. cm-ops-your-secret-path). "
                "Do not use the default /admin/ URL on a public site."
            )
        if path.lower() in _BLOCKED_ADMIN_PATHS:
            raise ValueError(f"DJANGO_ADMIN_PATH '{path}' is not allowed in production.")
        if len(path) < 8:
            raise ValueError("DJANGO_ADMIN_PATH must be at least 8 characters in production.")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", path):
            raise ValueError("DJANGO_ADMIN_PATH may only contain letters, numbers, hyphens, and underscores.")

    return path or "admin"


def admin_url_prefix(admin_path: Optional[str] = None) -> str:
    segment = normalize_admin_path(admin_path or getattr(settings, "DJANGO_ADMIN_PATH", "admin"))
    return f"/{segment}/"


def get_client_ip(request: HttpRequest) -> str:
    """Best-effort client IP behind reverse proxies (e.g. Elastic Beanstalk)."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.META.get("HTTP_X_REAL_IP")
    if real_ip:
        return real_ip.strip()
    return request.META.get("REMOTE_ADDR", "127.0.0.1")


def is_admin_path(path: str, admin_path: Optional[str] = None) -> bool:
    prefix = admin_url_prefix(admin_path)
    return path == prefix.rstrip("/") or path.startswith(prefix)


def is_legacy_admin_path(path: str) -> bool:
    return path in ("/admin", "/admin/")


def admin_login_rate_limit_exceeded(request: HttpRequest) -> bool:
    """Return True when an IP exceeds admin login attempt limits."""
    if request.method != "POST":
        return False

    path = request.path
    if not path.endswith("/login/"):
        return False

    max_attempts = int(getattr(settings, "ADMIN_LOGIN_MAX_ATTEMPTS", 5))
    window_seconds = int(getattr(settings, "ADMIN_LOGIN_WINDOW_SECONDS", 900))
    ip = get_client_ip(request)
    cache_key = f"admin_login_attempts:{ip}"

    count = int(cache_get(cache_key, 0) or 0)
    if count >= max_attempts:
        return True

    cache_set(cache_key, count + 1, timeout=window_seconds)
    return False


class AdminSecurityMiddleware(MiddlewareMixin):
    """Restrict and monitor access to the Django admin site."""

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        path = request.path

        if getattr(settings, "ADMIN_HIDE_LEGACY_PATH", False) and is_legacy_admin_path(path):
            logger.warning("Blocked legacy admin path access from %s", get_client_ip(request))
            return HttpResponseNotFound()

        if not is_admin_path(path):
            return None

        client_ip = get_client_ip(request)
        allowed_ips: Set[str] = set(getattr(settings, "ADMIN_ALLOWED_IPS", []) or [])
        if allowed_ips and client_ip not in allowed_ips:
            logger.warning("Admin access denied for IP %s on %s", client_ip, path)
            return HttpResponseForbidden("Admin access is restricted.")

        if admin_login_rate_limit_exceeded(request):
            logger.warning("Admin login rate limit exceeded for IP %s", client_ip)
            return HttpResponseForbidden("Too many login attempts. Try again later.")

        user_label = getattr(getattr(request, "user", None), "username", "anonymous")
        logger.info(
            "Admin request: %s %s ip=%s user=%s",
            request.method,
            path,
            client_ip,
            user_label,
        )
        return None
