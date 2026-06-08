"""User preferences for analysis completion notifications."""

from __future__ import annotations

from typing import Any


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
