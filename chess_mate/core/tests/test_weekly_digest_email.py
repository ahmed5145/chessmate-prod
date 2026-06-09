"""Tests for SRG-15 weekly coach digest."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from core.email_send_log import (
    digest_already_sent_this_week,
    iso_week_key,
    log_email_send,
)
from core.models import EmailSendLog, Profile, UserNotification
from core.notification_preferences import WANTS_WEEKLY_DIGEST_KEY
from core.weekly_digest_email import (
    build_weekly_digest_payload,
    send_weekly_digest_for_user,
)
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def digest_user(db):
    user = User.objects.create_user(
        username="digest_user",
        email="digest@example.com",
        password="Test.Password.123",
    )
    profile = Profile.objects.get(user=user)
    profile.preferences = {WANTS_WEEKLY_DIGEST_KEY: True}
    profile.save(update_fields=["preferences"])
    return user


def test_iso_week_key_format():
    from datetime import datetime
    from datetime import timezone as dt_timezone

    key = iso_week_key(datetime(2026, 6, 8, tzinfo=dt_timezone.utc))
    assert key.startswith("2026-W")


def test_digest_skipped_when_opted_out(digest_user):
    profile = Profile.objects.get(user=digest_user)
    profile.preferences = {WANTS_WEEKLY_DIGEST_KEY: False}
    profile.save(update_fields=["preferences"])

    with patch("core.weekly_digest_email.send_coaching_email") as mock_send:
        assert send_weekly_digest_for_user(digest_user) is False
        mock_send.assert_not_called()


def test_digest_skipped_when_no_content(digest_user):
    with patch(
        "core.weekly_digest_email.build_weekly_digest_payload",
        return_value={"has_content": False},
    ):
        with patch("core.weekly_digest_email.send_coaching_email") as mock_send:
            assert send_weekly_digest_for_user(digest_user) is False
            mock_send.assert_not_called()


@patch("core.weekly_digest_email.is_email_configured", return_value=True)
@patch("core.weekly_digest_email.render_to_string", return_value="<p>Digest</p>")
@patch("core.weekly_digest_email.send_coaching_email", return_value=1)
def test_sends_once_per_week(mock_send, _mock_render, _mock_email, digest_user):
    payload = {
        "has_content": True,
        "sections": [{"label": "Coach inbox", "body": "2 priorities waiting."}],
        "cta_href": "/dashboard",
        "cta_label": "Open dashboard",
        "title": "Your week with ChessMate Coach",
        "one_thing_today": {},
        "pending_inbox_count": 2,
    }
    with patch(
        "core.weekly_digest_email.received_coaching_touchpoint_today",
        return_value=False,
    ):
        with patch(
            "core.weekly_digest_email.build_weekly_digest_payload",
            return_value=payload,
        ):
            assert send_weekly_digest_for_user(digest_user) is True
            mock_send.assert_called_once()

            mock_send.reset_mock()
            assert send_weekly_digest_for_user(digest_user) is False
            mock_send.assert_not_called()


@patch("core.weekly_digest_email.is_email_configured", return_value=True)
@patch("core.weekly_digest_email.render_to_string", return_value="<p>Digest</p>")
@patch("core.weekly_digest_email.send_coaching_email", return_value=1)
def test_skips_when_completion_notification_today(
    mock_send, _mock_render, _mock_email, digest_user
):
    UserNotification.objects.create(
        user=digest_user,
        notification_type=UserNotification.TYPE_SINGLE_COMPLETE,
        entity_id="game:1",
        title="Review ready",
        href="/game/1/analysis?mode=review",
    )
    payload = {
        "has_content": True,
        "sections": [{"label": "Coach inbox", "body": "1 priority waiting."}],
        "cta_href": "/dashboard",
        "cta_label": "Open dashboard",
        "title": "Weekly",
        "one_thing_today": {},
        "pending_inbox_count": 1,
    }
    with patch(
        "core.weekly_digest_email.build_weekly_digest_payload", return_value=payload
    ):
        assert send_weekly_digest_for_user(digest_user) is False
        mock_send.assert_not_called()


def test_digest_already_sent_this_week(digest_user):
    week_key = iso_week_key()
    log_email_send(
        digest_user,
        EmailSendLog.TYPE_WEEKLY_DIGEST,
        week_key=week_key,
    )
    assert digest_already_sent_this_week(digest_user) is True


def test_build_payload_includes_inbox_when_pending(digest_user):
    profile = Profile.objects.get(user=digest_user)
    with patch(
        "core.weekly_digest_email.get_priority_inbox_payload",
        return_value={
            "pending_items": [
                {"title": "Fix hanging pieces", "href": "/game/5/analysis?mode=review"}
            ]
        },
    ):
        payload = build_weekly_digest_payload(digest_user, profile)
    assert payload["has_content"] is True
    assert payload["pending_inbox_count"] == 1
