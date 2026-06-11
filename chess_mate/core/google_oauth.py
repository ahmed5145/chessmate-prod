"""Google OAuth 2.0 helpers for sign-in and registration."""

from __future__ import annotations

import logging
import re
import secrets
from datetime import timedelta
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .abuse_limits import check_signup_allowed, record_signup_attempt
from .email_utils import get_frontend_base_url
from .models import Profile, profile_creation_defaults

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

PREF_GOOGLE_SUB = "google_oauth_sub"
PREF_GOOGLE_LINKED_AT = "google_oauth_linked_at"
SESSION_STATE_KEY = "google_oauth_state"
SESSION_REFERRAL_KEY = "google_oauth_referral"
SESSION_REMEMBER_KEY = "google_oauth_remember_me"

GOOGLE_SCOPES = "openid email profile"
# Canonical path — do not use reverse() here; duplicate includes register
# both /api/v1/ and /api/api/v1/ with the same names, and reverse() picks the legacy one.
GOOGLE_OAUTH_CALLBACK_PATH = "/api/v1/auth/google/callback/"


class GoogleOAuthError(Exception):
    """Raised when Google OAuth cannot complete."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def is_google_oauth_configured() -> bool:
    client_id = (getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None) or "").strip()
    client_secret = (getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", None) or "").strip()
    return bool(client_id and client_secret)


def store_oauth_session(request, *, referral_code: Optional[str], remember_me: bool) -> str:
    state = secrets.token_urlsafe(32)
    request.session[SESSION_STATE_KEY] = state
    request.session[SESSION_REFERRAL_KEY] = (referral_code or "").strip() or None
    request.session[SESSION_REMEMBER_KEY] = bool(remember_me)
    request.session.modified = True
    return state


def pop_oauth_session(request) -> Tuple[Optional[str], Optional[str], bool]:
    state = request.session.pop(SESSION_STATE_KEY, None)
    referral = request.session.pop(SESSION_REFERRAL_KEY, None)
    remember_me = bool(request.session.pop(SESSION_REMEMBER_KEY, True))
    request.session.modified = True
    return state, referral, remember_me


def _normalize_callback_uri(uri: str) -> str:
    cleaned = (uri or "").strip()
    if not cleaned.endswith("/"):
        cleaned = f"{cleaned}/"
    return cleaned


def build_redirect_uri(request) -> str:
    """
    Redirect URI sent to Google — must match Google Console **exactly** (scheme, host, path, trailing slash).

    Local dev: use the request host (localhost:8000), not FRONTEND_URL (localhost:3000).
    Production behind ALB: prefer FRONTEND_URL so we emit https even when Django sees http.
    """
    explicit = (getattr(settings, "GOOGLE_OAUTH_REDIRECT_URI", None) or "").strip()
    if explicit:
        return _normalize_callback_uri(explicit)

    callback_path = GOOGLE_OAUTH_CALLBACK_PATH
    host = (request.get_host() or "").split(":")[0].lower()

    if host in ("localhost", "127.0.0.1"):
        return _normalize_callback_uri(request.build_absolute_uri(callback_path))

    frontend_base = get_frontend_base_url(request).rstrip("/")
    if frontend_base and "localhost:3000" not in frontend_base:
        return _normalize_callback_uri(f"{frontend_base}{callback_path}")

    return _normalize_callback_uri(request.build_absolute_uri(callback_path))


def build_authorization_url(request, state: str) -> str:
    redirect_uri = build_redirect_uri(request)
    logger.info("Google OAuth start redirect_uri=%s", redirect_uri)
    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_userinfo(request, code: str) -> Dict[str, Any]:
    redirect_uri = build_redirect_uri(request)
    token_response = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    if token_response.status_code != 200:
        logger.warning("Google token exchange failed: %s", token_response.text[:300])
        raise GoogleOAuthError("token_exchange_failed", "Could not complete Google sign-in.")

    access_token = token_response.json().get("access_token")
    if not access_token:
        raise GoogleOAuthError("token_exchange_failed", "Google did not return an access token.")

    userinfo_response = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    if userinfo_response.status_code != 200:
        logger.warning("Google userinfo failed: %s", userinfo_response.text[:300])
        raise GoogleOAuthError("userinfo_failed", "Could not read your Google profile.")

    userinfo = userinfo_response.json()
    if not userinfo.get("sub"):
        raise GoogleOAuthError("userinfo_failed", "Google profile is missing a user id.")

    email = (userinfo.get("email") or "").strip()
    if not email:
        raise GoogleOAuthError("email_required", "Google did not provide an email address.")

    if not userinfo.get("email_verified", False):
        raise GoogleOAuthError("email_unverified", "Your Google email is not verified.")

    return userinfo


def _suggest_username(email: str, name: str) -> str:
    raw = (name or email.split("@")[0] or "user").strip()
    base = re.sub(r"[^\w]", "", raw.replace(" ", ""))[:30] or "user"
    candidate = base
    suffix = 1
    while User.objects.filter(username__iexact=candidate).exists():
        candidate = f"{base}{suffix}"
        suffix += 1
    return candidate


def _profile_by_google_sub(google_sub: str) -> Optional[Profile]:
    return Profile.objects.filter(preferences__google_oauth_sub=google_sub).select_related("user").first()


def _link_google_profile(profile: Profile, google_sub: str) -> None:
    profile.preferences[PREF_GOOGLE_SUB] = google_sub
    profile.preferences[PREF_GOOGLE_LINKED_AT] = timezone.now().isoformat()
    profile.save(update_fields=["preferences"])


def _mark_email_verified(profile: Profile) -> None:
    if profile.email_verified:
        return
    profile.email_verified = True
    profile.email_verified_at = timezone.now()
    profile.email_verification_token = None
    profile.save(
        update_fields=[
            "email_verified",
            "email_verified_at",
            "email_verification_token",
            "legacy_rating",
        ]
    )


def issue_auth_tokens(user: User, remember_me: bool = True) -> Tuple[str, str]:
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    refresh_lifetime = (
        getattr(
            settings,
            "JWT_REFRESH_TOKEN_LIFETIME_REMEMBER",
            settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"],
        )
        if remember_me
        else getattr(settings, "JWT_REFRESH_TOKEN_LIFETIME_SESSION", timedelta(hours=12))
    )
    refresh.set_exp(lifetime=refresh_lifetime)
    return str(refresh.access_token), str(refresh)


@transaction.atomic
def upsert_user_from_google(
    request,
    userinfo: Dict[str, Any],
    *,
    referral_code: Optional[str] = None,
) -> Tuple[User, bool]:
    google_sub = str(userinfo["sub"])
    email = str(userinfo["email"]).strip()
    display_name = (userinfo.get("name") or userinfo.get("given_name") or "").strip()

    existing_profile = _profile_by_google_sub(google_sub)
    if existing_profile:
        user = existing_profile.user
        _mark_email_verified(existing_profile)
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        return user, False

    user = User.objects.filter(email__iexact=email).first()
    if user:
        profile = getattr(user, "profile", None)
        if profile is None:
            profile, _ = Profile.objects.get_or_create(user=user, defaults=profile_creation_defaults())
        conflict = Profile.objects.filter(preferences__google_oauth_sub=google_sub).exclude(user=user).exists()
        if conflict:
            raise GoogleOAuthError(
                "google_account_linked_elsewhere",
                "This Google account is already linked to another ChessMate user.",
            )
        _link_google_profile(profile, google_sub)
        _mark_email_verified(profile)
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        return user, False

    allowed, _retry_after = check_signup_allowed(request)
    if not allowed:
        raise GoogleOAuthError(
            "signup_rate_limited",
            "Too many sign-up attempts. Please try again later.",
        )

    username = _suggest_username(email, display_name)
    user = User(username=username, email=email, is_active=True)
    user.set_unusable_password()
    user.save()

    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults=profile_creation_defaults(
            email_verified=True,
            email_verified_at=timezone.now(),
        ),
    )
    if not profile.email_verified:
        _mark_email_verified(profile)
    _link_google_profile(profile, google_sub)

    from .referral import attach_referral_on_signup

    attach_referral_on_signup(
        profile,
        referral_code=referral_code,
        signup_ip=request.META.get("REMOTE_ADDR"),
    )

    record_signup_attempt(request)

    from .welcome_email import send_welcome_email_once

    send_welcome_email_once(user, profile, request)

    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])
    return user, True


def build_frontend_success_url(request, user: User, remember_me: bool) -> str:
    access, refresh = issue_auth_tokens(user, remember_me=remember_me)
    frontend = get_frontend_base_url(request)
    fragment = urlencode({"access": access, "refresh": refresh})
    return f"{frontend}/auth/google/callback#{fragment}"


def build_frontend_error_url(request, error_code: str, message: str) -> str:
    frontend = get_frontend_base_url(request)
    params = urlencode({"error": error_code, "message": message})
    return f"{frontend}/auth/google/callback?{params}"
