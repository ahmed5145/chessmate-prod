"""Tests for SRG-23 first-batch celebration."""

import pytest
from core.first_batch_celebration import (
    FIRST_BATCH_CELEBRATED_KEY,
    build_first_batch_celebration_payload,
    is_first_eligible_batch,
    mark_first_batch_celebrated,
)
from core.models import BatchAnalysisReport, Profile
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def coach_user(db):
    return User.objects.create_user(
        username="celebrate_user",
        email="celebrate@example.com",
        password="Test.Password.123",
    )


def _make_batch(user, **overrides):
    payload = {
        "user": user,
        "task_id": "task-celebrate-1",
        "status": "completed",
        "games_count": 10,
        "coaching_report": {
            "executive_summary": "Your biggest leak is loose pieces in the opening.",
            "top_3_priorities": [{"rank": 1, "title": "Stop hanging pieces"}],
        },
        "batch_summary": {},
        "per_game_results": [],
    }
    payload.update(overrides)
    return BatchAnalysisReport.objects.create(**payload)


def test_first_batch_celebration_shows_once(coach_user):
    profile = Profile.objects.get(user=coach_user)
    batch = _make_batch(coach_user)

    payload = build_first_batch_celebration_payload(batch, profile)
    assert payload["show"] is True
    assert "opening" in payload["headline"].lower() or payload["headline"]
    assert payload["cta_href"]

    mark_first_batch_celebrated(profile)
    profile.refresh_from_db()
    assert profile.get_preference(FIRST_BATCH_CELEBRATED_KEY)

    payload_again = build_first_batch_celebration_payload(batch, profile)
    assert payload_again["show"] is False


def test_celebration_headline_uses_first_sentence(coach_user):
    profile = Profile.objects.get(user=coach_user)
    batch = _make_batch(
        coach_user,
        coaching_report={
            "executive_summary": (
                "This batch covers 5 games with a focus on your openings. "
                "Tactical oversight problems plagued both middlegames."
            ),
            "top_3_priorities": [{"rank": 1, "title": "Stop hanging pieces"}],
        },
    )

    payload = build_first_batch_celebration_payload(batch, profile)
    assert payload["show"] is True
    assert payload["headline"].endswith(".")
    assert "middlegames" not in payload["headline"]


def test_second_batch_not_first(coach_user):
    profile = Profile.objects.get(user=coach_user)
    _make_batch(coach_user, task_id="task-celebrate-a")
    second = _make_batch(coach_user, task_id="task-celebrate-b")

    assert is_first_eligible_batch(second) is False
    payload = build_first_batch_celebration_payload(second, profile)
    assert payload["show"] is False
