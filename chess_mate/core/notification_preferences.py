"""User preferences for analysis completion notifications."""

from __future__ import annotations

from typing import Any

WANTS_WEEKLY_DIGEST_KEY = "wants_weekly_digest"
WANTS_WEEKLY_DIGEST_IN_APP_KEY = "wants_weekly_digest_in_app"
WANTS_SPACED_REPETITION_KEY = "wants_spaced_repetition_email"


def _profile_preferences(user: Any) -> dict:
    profile = getattr(user, "profile", None)
    if profile is None:
        return {}
    prefs = getattr(profile, "preferences", None)
    return prefs if isinstance(prefs, dict) else {}


def user_wants_weekly_digest_email(user: Any) -> bool:
    """Opt-in weekly digest email (default off)."""
    if user is None or not getattr(user, "email", None):
        return False
    if not user_wants_analysis_completion_email(user):
        return False
    return _profile_preferences(user).get(WANTS_WEEKLY_DIGEST_KEY) is True


def user_wants_weekly_digest_notification(user: Any) -> bool:
    """In-app weekly digest mirror — on when email digest or in-app-only pref is set."""
    if user is None:
        return False
    prefs = _profile_preferences(user)
    if prefs.get(WANTS_WEEKLY_DIGEST_IN_APP_KEY) is True:
        return True
    return prefs.get(WANTS_WEEKLY_DIGEST_KEY) is True


def user_wants_spaced_repetition_email(user: Any) -> bool:
    """Opt-in spaced moment email (default off)."""
    if user is None or not getattr(user, "email", None):
        return False
    if not user_wants_analysis_completion_email(user):
        return False
    return _profile_preferences(user).get(WANTS_SPACED_REPETITION_KEY) is True


def user_wants_analysis_completion_email(user: Any) -> bool:
    """
    Return True when the user has not opted out of analysis completion emails.

    Supports both profile preference keys used in the app:
    - ``notifications_enabled`` (API / tests)
    - ``emailNotifications`` (UserProfile UI)
    """
    if user is None:
        return False

    email = getattr(user, "email", None)
    if not email:
        return False

    profile = getattr(user, "profile", None)
    if profile is None:
        return True

    prefs = profile.preferences if isinstance(getattr(profile, "preferences", None), dict) else {}
    if prefs.get("emailNotifications") is False:
        return False
    if prefs.get("notifications_enabled") is False:
        return False
    return True
