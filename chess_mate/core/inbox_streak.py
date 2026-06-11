"""Coach inbox review streak — consecutive calendar days clearing priorities (SRG-16)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, Optional

from django.utils import timezone

from .models import Profile

PREFERENCES_KEY = "inbox_streak"
FREEZE_MONTH_KEY = "inbox_streak_freeze_used_month"
_MIN_DISPLAY_COUNT = 2
_MIN_FREEZE_COUNT = 3


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


def _freeze_month_key(when: Optional[date] = None) -> str:
    day = when or timezone.localdate()
    return day.strftime("%Y-%m")


def can_use_inbox_streak_freeze(
    preferences: Optional[Dict[str, Any]],
    today: Optional[date] = None,
) -> bool:
    """True when user missed exactly yesterday, streak ≥3, freeze unused this month."""
    today = today or timezone.localdate()
    prefs = preferences if isinstance(preferences, dict) else {}
    if prefs.get(FREEZE_MONTH_KEY) == _freeze_month_key(today):
        return False

    state = _load_streak_state(prefs)
    count = int(state.get("count") or 0)
    if count < _MIN_FREEZE_COUNT:
        return False

    last_date = _parse_review_date(state.get("last_reviewed_date"))
    if last_date is None:
        return False
    return (today - last_date).days == 2


def apply_inbox_streak_freeze(profile: Profile) -> Dict[str, Any]:
    """
    Preserve streak after one missed day. Does not increment count.
    """
    today = timezone.localdate()
    prefs = profile.preferences if isinstance(profile.preferences, dict) else {}
    if not can_use_inbox_streak_freeze(prefs, today):
        raise ValueError("Streak freeze is not available right now.")

    state = _load_streak_state(prefs)
    prefs = dict(prefs)
    prefs[FREEZE_MONTH_KEY] = _freeze_month_key(today)
    state = dict(state)
    state["last_reviewed_date"] = (today - timedelta(days=1)).isoformat()
    prefs[PREFERENCES_KEY] = state
    profile.preferences = prefs
    profile.save(update_fields=["preferences"])
    return get_inbox_streak_payload(prefs)


def get_inbox_streak_payload(preferences: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Serialize streak for API/UI. Badge from 2+ days; day-1 shows progress hint."""
    today = timezone.localdate()
    prefs = preferences if isinstance(preferences, dict) else {}
    state = _load_streak_state(prefs)
    count = _effective_streak_count(state, today)
    show_badge = count >= _MIN_DISPLAY_COUNT
    show_progress = count == 1
    show = show_badge or show_progress
    if show_badge:
        label = f"{count}-day coach streak"
    elif show_progress:
        label = "Day 1 — mark a priority tomorrow to reach a 2-day streak"
    else:
        label = None
    freeze_used = prefs.get(FREEZE_MONTH_KEY) == _freeze_month_key(today)
    can_freeze = can_use_inbox_streak_freeze(prefs, today)
    return {
        "count": count,
        "show": show,
        "show_badge": show_badge,
        "label": label,
        "milestone_message": _milestone_message(count) if show_badge else None,
        "hint": (
            "Mark a coach inbox priority as reviewed on consecutive calendar days to build a streak. "
            "Using the app alone does not count — tap Mark reviewed on a proof game."
            if count < _MIN_DISPLAY_COUNT
            else None
        ),
        "last_reviewed_date": state.get("last_reviewed_date"),
        "freeze": {
            "can_use": can_freeze,
            "used_this_month": freeze_used,
            "label": "Use freeze (1 left this month)" if can_freeze else None,
            "blocked_reason": ("Freeze already used this month" if freeze_used and not can_freeze else None),
        },
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
