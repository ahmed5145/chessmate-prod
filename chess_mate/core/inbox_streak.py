"""Coach inbox review streak — consecutive calendar days clearing priorities (SRG-16)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, Optional

from django.utils import timezone

from .models import Profile

PREFERENCES_KEY = "inbox_streak"
_MIN_DISPLAY_COUNT = 2


def _parse_review_date(raw: Any) -> Optional[date]:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except (TypeError, ValueError):
        return None


def _load_streak_state(preferences: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    prefs = preferences if isinstance(preferences, dict) else {}
    raw = prefs.get(PREFERENCES_KEY)
    if not isinstance(raw, dict):
        return {"count": 0, "last_reviewed_date": None}

    count = int(raw.get("count") or 0)
    if count < 0:
        count = 0
    return {
        "count": count,
        "last_reviewed_date": raw.get("last_reviewed_date"),
    }


def _effective_streak_count(state: Dict[str, Any], today: date) -> int:
    last_date = _parse_review_date(state.get("last_reviewed_date"))
    if last_date is None:
        return 0
    if last_date == today or last_date == today - timedelta(days=1):
        return int(state.get("count") or 0)
    return 0


def _milestone_message(count: int) -> Optional[str]:
    if count >= 7:
        return "7-day coach streak — habits stick."
    if count >= 5:
        return "5-day coach streak — keep clearing priorities."
    if count >= 3:
        return "3-day coach streak — nice consistency."
    return None


def get_inbox_streak_payload(preferences: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Serialize streak for API/UI. Shown only when effective count >= 2."""
    today = timezone.localdate()
    state = _load_streak_state(preferences)
    count = _effective_streak_count(state, today)
    show = count >= _MIN_DISPLAY_COUNT
    return {
        "count": count,
        "show": show,
        "label": f"{count}-day coach streak" if show else None,
        "milestone_message": _milestone_message(count) if show else None,
        "last_reviewed_date": state.get("last_reviewed_date"),
    }


def update_inbox_streak_on_review(profile: Profile) -> Dict[str, Any]:
    """
    Increment streak when user marks an inbox item reviewed.
    At most one increment per calendar day.
    """
    today = timezone.localdate()
    prefs = profile.preferences if isinstance(profile.preferences, dict) else {}
    state = _load_streak_state(prefs)
    last_date = _parse_review_date(state.get("last_reviewed_date"))
    count = int(state.get("count") or 0)

    if last_date == today:
        new_count = count
    elif last_date == today - timedelta(days=1):
        new_count = count + 1 if count > 0 else 1
    else:
        new_count = 1

    new_state = {
        "count": new_count,
        "last_reviewed_date": today.isoformat(),
    }
    prefs = dict(prefs)
    prefs[PREFERENCES_KEY] = new_state
    profile.preferences = prefs
    profile.save(update_fields=["preferences"])
    return get_inbox_streak_payload(prefs)
