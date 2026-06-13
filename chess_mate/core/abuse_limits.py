"""Signup, auth, import, analysis, and batch abuse limits."""

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
from .batch_labels import BATCH_COACH_ACTIVE_LIMIT
from .cache import cache_get, cache_set
from .models import BatchAnalysisReport, Game

logger = logging.getLogger(__name__)


def _staff_bypasses(user: User) -> bool:
    return bool(user.is_staff or user.is_superuser)


def _retry_after(window_seconds: int, cache_key: str) -> int:
    first_ts = int(cache_get(f"{cache_key}:ts", 0) or 0)
    if not first_ts:
        return max(1, window_seconds)
    elapsed = max(0, int(timezone.now().timestamp()) - first_ts)
    return max(1, window_seconds - elapsed)


def _check_ip_window(cache_prefix: str, request, max_count: int, window_seconds: int) -> Tuple[bool, int]:
    ip = get_client_ip(request)
    cache_key = f"{cache_prefix}:{ip}"
    count = int(cache_get(cache_key, 0) or 0)
    if count >= max_count:
        logger.warning("%s limit exceeded for IP %s (%s/%s)", cache_prefix, ip, count, max_count)
        return False, _retry_after(window_seconds, cache_key)
    return True, 0


def _record_ip_window(cache_prefix: str, request, window_seconds: int) -> None:
    ip = get_client_ip(request)
    cache_key = f"{cache_prefix}:{ip}"
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


def _check_email_window(email: str, cache_prefix: str, max_count: int, window_seconds: int) -> Tuple[bool, int]:
    normalized = (email or "").strip().lower()
    if not normalized:
        return True, 0
    cache_key = f"{cache_prefix}:{normalized}"
    count = int(cache_get(cache_key, 0) or 0)
    if count >= max_count:
        logger.warning("%s limit exceeded for email %s", cache_prefix, normalized)
        return False, _retry_after(window_seconds, cache_key)
    return True, 0


def _record_email_window(email: str, cache_prefix: str, window_seconds: int) -> None:
    normalized = (email or "").strip().lower()
    if not normalized:
        return
    cache_key = f"{cache_prefix}:{normalized}"
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


def abuse_limit_response(
    *,
    code: str,
    message: str,
    error: str,
    retry_after: Optional[int] = None,
    detail: Optional[Dict[str, Any]] = None,
) -> Response:
    payload: Dict[str, Any] = {
        "status": "error",
        "code": code,
        "message": message,
        "error": error,
    }
    if retry_after is not None:
        payload["retry_after"] = retry_after
    if detail:
        payload["detail"] = detail
    headers = {}
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return Response(payload, status=status.HTTP_429_TOO_MANY_REQUESTS, headers=headers)


def _start_of_local_day() -> datetime:
    tz = timezone.get_current_timezone()
    today = timezone.localdate()
    start = datetime.combine(today, time.min)
    if timezone.is_naive(start):
        return timezone.make_aware(start, tz)
    return start.astimezone(tz)


def _end_of_local_day() -> datetime:
    return _start_of_local_day() + timedelta(days=1)


# --- Signup ---


def check_signup_allowed(request) -> Tuple[bool, int]:
    max_per_ip = int(getattr(settings, "SIGNUP_RATE_LIMIT_MAX_PER_IP", 5))
    window_seconds = int(getattr(settings, "SIGNUP_RATE_LIMIT_WINDOW_SECONDS", 3600))
    return _check_ip_window("signup_attempts", request, max(1, max_per_ip), max(60, window_seconds))


def record_signup_attempt(request) -> None:
    window_seconds = int(getattr(settings, "SIGNUP_RATE_LIMIT_WINDOW_SECONDS", 3600))
    _record_ip_window("signup_attempts", request, max(60, window_seconds))


def signup_rate_limit_response(retry_after: int) -> Response:
    return abuse_limit_response(
        code="RATE_001",
        message=f"Too many signups from this network. Try again in {retry_after} seconds.",
        error="Signup rate limit exceeded",
        retry_after=retry_after,
    )


# --- Login brute force ---


def check_login_allowed(request) -> Tuple[bool, int]:
    max_per_ip = int(getattr(settings, "LOGIN_FAILED_MAX_PER_IP", 20))
    window_seconds = int(getattr(settings, "LOGIN_FAILED_WINDOW_SECONDS", 3600))
    return _check_ip_window("login_failed", request, max(1, max_per_ip), max(60, window_seconds))


def record_failed_login(request) -> None:
    window_seconds = int(getattr(settings, "LOGIN_FAILED_WINDOW_SECONDS", 3600))
    _record_ip_window("login_failed", request, max(60, window_seconds))


def login_rate_limit_response(retry_after: int) -> Response:
    return abuse_limit_response(
        code="RATE_002",
        message=f"Too many failed login attempts. Try again in {retry_after} seconds.",
        error="Login rate limit exceeded",
        retry_after=retry_after,
    )


# --- Password reset (email bombing) ---


def check_password_reset_allowed(request, email: str) -> Tuple[bool, int]:
    ip_max = int(getattr(settings, "PASSWORD_RESET_MAX_PER_IP", 5))
    ip_window = int(getattr(settings, "PASSWORD_RESET_WINDOW_SECONDS", 3600))
    email_max = int(getattr(settings, "PASSWORD_RESET_MAX_PER_EMAIL", 3))
    email_window = int(getattr(settings, "PASSWORD_RESET_EMAIL_WINDOW_SECONDS", 86400))

    ip_ok, ip_retry = _check_ip_window("password_reset_ip", request, max(1, ip_max), max(60, ip_window))
    if not ip_ok:
        return False, ip_retry
    email_ok, email_retry = _check_email_window(email, "password_reset_email", max(1, email_max), max(60, email_window))
    if not email_ok:
        return False, email_retry
    return True, 0


def record_password_reset_request(request, email: str) -> None:
    ip_window = int(getattr(settings, "PASSWORD_RESET_WINDOW_SECONDS", 3600))
    email_window = int(getattr(settings, "PASSWORD_RESET_EMAIL_WINDOW_SECONDS", 86400))
    _record_ip_window("password_reset_ip", request, max(60, ip_window))
    _record_email_window(email, "password_reset_email", max(60, email_window))


def password_reset_rate_limit_response(retry_after: int) -> Response:
    return abuse_limit_response(
        code="RATE_003",
        message=f"Too many password reset requests. Try again in {retry_after} seconds.",
        error="Password reset rate limit exceeded",
        retry_after=retry_after,
    )


# --- Batches ---


def batches_started_today(user: User) -> int:
    return BatchAnalysisReport.objects.filter(user=user, created_at__gte=_start_of_local_day()).count()


def user_has_active_batch(user: User) -> bool:
    return BatchAnalysisReport.objects.filter(user=user, status__in=["pending", "in_progress"]).exists()


def check_batch_creation_allowed(user: User) -> Tuple[bool, Dict[str, Any]]:
    daily_limit = max(0, int(getattr(settings, "MAX_BATCHES_PER_USER_PER_DAY", 3)))
    allow_concurrent = bool(getattr(settings, "ALLOW_CONCURRENT_BATCHES", False))
    count = batches_started_today(user)
    resets_at = _end_of_local_day()
    info: Dict[str, Any] = {
        "limit": daily_limit,
        "count": count,
        "remaining": max(0, daily_limit - count) if daily_limit else None,
        "resets_at": resets_at.isoformat(),
    }

    if _staff_bypasses(user):
        info["bypass"] = True
        return True, info

    if not allow_concurrent and user_has_active_batch(user):
        info["active_batch"] = True
        logger.warning("Blocked new batch for user %s: active batch in progress", user.id)
        return False, info

    if daily_limit > 0 and count >= daily_limit:
        logger.warning(
            "Daily batch limit exceeded for user %s (%s/%s)",
            user.id,
            count,
            daily_limit,
        )
        return False, info

    return True, info


def batch_daily_limit_response(info: Dict[str, Any]) -> Response:
    if info.get("active_batch"):
        return abuse_limit_response(
            code="BATCH_002",
            message=BATCH_COACH_ACTIVE_LIMIT,
            error="Active batch in progress",
            detail=info,
        )
    limit = info.get("limit", 0)
    return abuse_limit_response(
        code="BATCH_001",
        message=(
            f"Daily batch limit reached ({limit} per day). "
            "Try again after midnight or contact support if you need a higher limit."
        ),
        error="Daily batch limit exceeded",
        detail=info,
    )


# --- Game imports ---


def games_imported_today(user: User) -> int:
    return Game.objects.filter(user=user, created_at__gte=_start_of_local_day()).count()


def check_game_import_allowed(user: User, num_games: int = 1) -> Tuple[bool, Dict[str, Any]]:
    daily_limit = max(0, int(getattr(settings, "MAX_GAME_IMPORTS_PER_USER_PER_DAY", 100)))
    count = games_imported_today(user)
    info = {
        "limit": daily_limit,
        "count": count,
        "requested": num_games,
        "resets_at": _end_of_local_day().isoformat(),
    }
    if _staff_bypasses(user) or daily_limit <= 0:
        info["bypass"] = True
        return True, info
    if count + max(0, num_games) > daily_limit:
        logger.warning(
            "Daily import limit exceeded for user %s (%s+%s>%s)",
            user.id,
            count,
            num_games,
            daily_limit,
        )
        return False, info
    return True, info


def game_import_limit_response(info: Dict[str, Any]) -> Response:
    return abuse_limit_response(
        code="IMPORT_001",
        message=(
            f"Daily game import limit reached ({info.get('limit')} per day). " "Try again tomorrow or contact support."
        ),
        error="Daily game import limit exceeded",
        detail=info,
    )


def check_external_fetch_allowed(user: User) -> Tuple[bool, Dict[str, Any]]:
    """Limit external platform fetch *requests* per day (each may import many games)."""
    daily_limit = max(0, int(getattr(settings, "MAX_EXTERNAL_FETCH_REQUESTS_PER_USER_PER_DAY", 30)))
    cache_key = f"external_fetch_count:{user.id}:{timezone.localdate().isoformat()}"
    count = int(cache_get(cache_key, 0) or 0)
    info = {
        "limit": daily_limit,
        "count": count,
        "resets_at": _end_of_local_day().isoformat(),
    }
    if _staff_bypasses(user) or daily_limit <= 0:
        info["bypass"] = True
        return True, info
    if count >= daily_limit:
        return False, info
    return True, info


def record_external_fetch(user: User) -> None:
    cache_key = f"external_fetch_count:{user.id}:{timezone.localdate().isoformat()}"
    count = int(cache_get(cache_key, 0) or 0)
    seconds_until_midnight = int((_end_of_local_day() - timezone.now()).total_seconds())
    cache_set(cache_key, count + 1, timeout=max(60, seconds_until_midnight))


def external_fetch_limit_response(info: Dict[str, Any]) -> Response:
    return abuse_limit_response(
        code="IMPORT_002",
        message=f"Daily external fetch limit reached ({info.get('limit')} requests per day).",
        error="External fetch limit exceeded",
        detail=info,
    )


# --- Single-game analysis ---


def check_single_analysis_allowed(user: User) -> Tuple[bool, Dict[str, Any]]:
    daily_limit = max(0, int(getattr(settings, "MAX_SINGLE_ANALYSES_PER_USER_PER_DAY", 50)))
    cache_key = f"single_analysis_count:{user.id}:{timezone.localdate().isoformat()}"
    count = int(cache_get(cache_key, 0) or 0)
    info = {
        "limit": daily_limit,
        "count": count,
        "resets_at": _end_of_local_day().isoformat(),
    }
    if _staff_bypasses(user) or daily_limit <= 0:
        info["bypass"] = True
        return True, info
    if count >= daily_limit:
        return False, info
    return True, info


def record_single_analysis(user: User) -> None:
    cache_key = f"single_analysis_count:{user.id}:{timezone.localdate().isoformat()}"
    count = int(cache_get(cache_key, 0) or 0)
    seconds_until_midnight = int((_end_of_local_day() - timezone.now()).total_seconds())
    cache_set(cache_key, count + 1, timeout=max(60, seconds_until_midnight))


def single_analysis_limit_response(info: Dict[str, Any]) -> Response:
    return abuse_limit_response(
        code="ANALYSIS_001",
        message=f"Daily single-game analysis limit reached ({info.get('limit')} per day).",
        error="Daily analysis limit exceeded",
        detail=info,
    )


# --- Coaching regenerate (OpenAI cost) ---


def check_coaching_regenerate_allowed(user: User, batch_id: int) -> Tuple[bool, Dict[str, Any]]:
    user_daily = max(0, int(getattr(settings, "MAX_COACHING_REGENERATIONS_PER_USER_PER_DAY", 10)))
    batch_daily = max(0, int(getattr(settings, "MAX_COACHING_REGENERATIONS_PER_BATCH_PER_DAY", 3)))
    today = timezone.localdate().isoformat()
    user_key = f"coaching_regen_user:{user.id}:{today}"
    batch_key = f"coaching_regen_batch:{batch_id}:{today}"
    user_count = int(cache_get(user_key, 0) or 0)
    batch_count = int(cache_get(batch_key, 0) or 0)
    info = {
        "user_limit": user_daily,
        "user_count": user_count,
        "batch_limit": batch_daily,
        "batch_count": batch_count,
        "resets_at": _end_of_local_day().isoformat(),
    }
    if _staff_bypasses(user):
        info["bypass"] = True
        return True, info
    if user_daily > 0 and user_count >= user_daily:
        return False, info
    if batch_daily > 0 and batch_count >= batch_daily:
        return False, info
    return True, info


def record_coaching_regenerate(user: User, batch_id: int) -> None:
    today = timezone.localdate().isoformat()
    ttl = max(60, int((_end_of_local_day() - timezone.now()).total_seconds()))
    for key in (
        f"coaching_regen_user:{user.id}:{today}",
        f"coaching_regen_batch:{batch_id}:{today}",
    ):
        count = int(cache_get(key, 0) or 0)
        cache_set(key, count + 1, timeout=ttl)


def coaching_regenerate_limit_response(info: Dict[str, Any]) -> Response:
    return abuse_limit_response(
        code="COACH_001",
        message="Coaching regeneration limit reached for today. Try again tomorrow.",
        error="Coaching regeneration limit exceeded",
        detail=info,
    )


# --- Profile / preferences updates ---


def check_profile_update_allowed(user: User) -> Tuple[bool, int]:
    max_per_hour = int(getattr(settings, "MAX_PROFILE_UPDATES_PER_USER_PER_HOUR", 30))
    window_seconds = 3600
    cache_key = f"profile_updates:{user.id}"
    count = int(cache_get(cache_key, 0) or 0)
    if _staff_bypasses(user) or max_per_hour <= 0:
        return True, 0
    if count >= max_per_hour:
        return False, _retry_after(window_seconds, cache_key)
    return True, 0


def record_profile_update(user: User) -> None:
    window_seconds = 3600
    cache_key = f"profile_updates:{user.id}"
    count = int(cache_get(cache_key, 0) or 0)
    now = int(timezone.now().timestamp())
    if count == 0:
        cache_set(cache_key, 1, timeout=window_seconds)
        cache_set(f"{cache_key}:ts", now, timeout=window_seconds)
        return
    ttl_key = f"{cache_key}:ts"
    first_ts = int(cache_get(ttl_key, now) or now)
    ttl = max(60, window_seconds - max(0, now - first_ts))
    cache_set(cache_key, count + 1, timeout=ttl)
    cache_set(ttl_key, first_ts, timeout=ttl)


def profile_update_limit_response(retry_after: int) -> Response:
    return abuse_limit_response(
        code="PROFILE_001",
        message=f"Too many profile updates. Try again in {retry_after} seconds.",
        error="Profile update rate limit exceeded",
        retry_after=retry_after,
    )


def preferences_subset_unchanged(current: Optional[Dict[str, Any]], incoming: Dict[str, Any]) -> bool:
    base = current if isinstance(current, dict) else {}
    for key, value in incoming.items():
        if base.get(key) != value:
            return False
    return True


# --- Stripe checkout spam ---


def check_checkout_allowed(user: User) -> Tuple[bool, int]:
    max_per_hour = int(getattr(settings, "MAX_CHECKOUT_SESSIONS_PER_USER_PER_HOUR", 10))
    window_seconds = 3600
    cache_key = f"checkout_sessions:{user.id}"
    count = int(cache_get(cache_key, 0) or 0)
    if _staff_bypasses(user) or max_per_hour <= 0:
        return True, 0
    if count >= max_per_hour:
        return False, _retry_after(window_seconds, cache_key)
    return True, 0


def record_checkout_session(user: User) -> None:
    window_seconds = 3600
    cache_key = f"checkout_sessions:{user.id}"
    count = int(cache_get(cache_key, 0) or 0)
    now = int(timezone.now().timestamp())
    if count == 0:
        cache_set(cache_key, 1, timeout=window_seconds)
        cache_set(f"{cache_key}:ts", now, timeout=window_seconds)
        return
    ttl_key = f"{cache_key}:ts"
    first_ts = int(cache_get(ttl_key, now) or now)
    ttl = max(60, window_seconds - max(0, now - first_ts))
    cache_set(cache_key, count + 1, timeout=ttl)
    cache_set(ttl_key, first_ts, timeout=ttl)


def checkout_limit_response(retry_after: int) -> Response:
    return abuse_limit_response(
        code="PAY_001",
        message=f"Too many checkout attempts. Try again in {retry_after} seconds.",
        error="Checkout rate limit exceeded",
        retry_after=retry_after,
    )
