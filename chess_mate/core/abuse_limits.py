"""Signup and batch abuse limits for public deployments."""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from .admin_security import get_client_ip
from .cache import cache_get, cache_set
from .models import BatchAnalysisReport

logger = logging.getLogger(__name__)


def _signup_settings() -> Tuple[int, int]:
    max_per_ip = int(getattr(settings, "SIGNUP_RATE_LIMIT_MAX_PER_IP", 5))
    window_seconds = int(getattr(settings, "SIGNUP_RATE_LIMIT_WINDOW_SECONDS", 3600))
    return max(1, max_per_ip), max(60, window_seconds)


def _batch_daily_limit() -> int:
    return max(0, int(getattr(settings, "MAX_BATCHES_PER_USER_PER_DAY", 3)))


def _staff_bypasses_batch_limit(user: User) -> bool:
    return bool(user.is_staff or user.is_superuser)


def check_signup_allowed(request) -> Tuple[bool, int]:
    """
    Return (allowed, retry_after_seconds).
    IP-based counter; does not increment on failed validation (call record_signup_attempt after success only).
    """
    max_per_ip, window_seconds = _signup_settings()
    ip = get_client_ip(request)
    cache_key = f"signup_attempts:{ip}"
    count = int(cache_get(cache_key, 0) or 0)
    if count >= max_per_ip:
        ttl_key = f"{cache_key}:ts"
        first_ts = int(cache_get(ttl_key, 0) or 0)
        if first_ts:
            elapsed = max(0, int(timezone.now().timestamp()) - first_ts)
            retry_after = max(1, window_seconds - elapsed)
        else:
            retry_after = window_seconds
        logger.warning("Signup rate limit exceeded for IP %s (%s/%s)", ip, count, max_per_ip)
        return False, retry_after
    return True, 0


def record_signup_attempt(request) -> None:
    """Increment signup counter after a successful registration."""
    max_per_ip, window_seconds = _signup_settings()
    ip = get_client_ip(request)
    cache_key = f"signup_attempts:{ip}"
    count = int(cache_get(cache_key, 0) or 0)
    now = int(timezone.now().timestamp())
    if count == 0:
        cache_set(cache_key, 1, timeout=window_seconds)
        cache_set(f"{cache_key}:ts", now, timeout=window_seconds)
        return
    ttl_key = f"{cache_key}:ts"
    first_ts = int(cache_get(ttl_key, now) or now)
    elapsed = max(0, now - first_ts)
    ttl = max(60, window_seconds - elapsed)
    cache_set(cache_key, count + 1, timeout=ttl)
    cache_set(ttl_key, first_ts, timeout=ttl)


def signup_rate_limit_response(retry_after: int) -> Response:
    return Response(
        {
            "status": "error",
            "code": "RATE_001",
            "message": f"Too many signups from this network. Try again in {retry_after} seconds.",
            "error": "Signup rate limit exceeded",
            "retry_after": retry_after,
        },
        status=status.HTTP_429_TOO_MANY_REQUESTS,
        headers={"Retry-After": str(retry_after)},
    )


def _start_of_local_day() -> datetime:
    tz = timezone.get_current_timezone()
    today = timezone.localdate()
    start = datetime.combine(today, time.min)
    if timezone.is_naive(start):
        return timezone.make_aware(start, tz)
    return start.astimezone(tz)


def _end_of_local_day() -> datetime:
    return _start_of_local_day() + timedelta(days=1)


def batches_started_today(user: User) -> int:
    start = _start_of_local_day()
    return BatchAnalysisReport.objects.filter(user=user, created_at__gte=start).count()


def check_batch_creation_allowed(user: User) -> Tuple[bool, Dict[str, Any]]:
    """Return (allowed, info dict with limit/count/resets_at)."""
    limit = _batch_daily_limit()
    if limit <= 0 or _staff_bypasses_batch_limit(user):
        return True, {"limit": limit, "count": batches_started_today(user), "bypass": True}

    count = batches_started_today(user)
    resets_at = _end_of_local_day()
    info = {
        "limit": limit,
        "count": count,
        "remaining": max(0, limit - count),
        "resets_at": resets_at.isoformat(),
    }
    if count >= limit:
        logger.warning(
            "Daily batch limit exceeded for user %s (%s/%s)",
            user.id,
            count,
            limit,
        )
        return False, info
    return True, info


def batch_daily_limit_response(info: Dict[str, Any]) -> Response:
    limit = info.get("limit", 0)
    return Response(
        {
            "status": "error",
            "code": "BATCH_001",
            "message": (
                f"Daily batch limit reached ({limit} per day). "
                "Try again after midnight or contact support if you need a higher limit."
            ),
            "error": "Daily batch limit exceeded",
            "detail": info,
        },
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )
