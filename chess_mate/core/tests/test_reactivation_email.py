"""Tests for inactive user reactivation email (SRG-27)."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from core.email_send_log import log_email_send
from core.models import EmailSendLog, Profile
from core.notification_preferences import WANTS_REACTIVATION_KEY
from core.reactivation_email import (
    is_eligible_for_reactivation,
    reactivation_sent_recently,
    send_reactivation_for_user,
)
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def inactive_user(db):
    user = User.objects.create_user(
        username="inactive_user",
        email="inactive@example.com",
        password="Test.Password.123",
    )
    profile = Profile.objects.get(user=user)
    profile.preferences = {WANTS_REACTIVATION_KEY: True}
    profile.lichess_username = "inactive_lichess"
    profile.save(update_fields=["preferences", "lichess_username"])
    stale = timezone.now() - timedelta(days=45)
    Profile.objects.filter(pk=profile.pk).update(updated_at=stale, created_at=stale)
    user.last_login = stale
    user.save(update_fields=["last_login"])
    return user


def test_skipped_when_opted_out(inactive_user):
    profile = Profile.objects.get(user=inactive_user)
    profile.preferences = {WANTS_REACTIVATION_KEY: False}
    profile.save(update_fields=["preferences"])
    assert is_eligible_for_reactivation(inactive_user, profile) is False


def test_skipped_when_recently_active(inactive_user):
    profile = Profile.objects.get(user=inactive_user)
    inactive_user.last_login = timezone.now()
    inactive_user.save(update_fields=["last_login"])
    assert is_eligible_for_reactivation(inactive_user, profile) is False


def test_skipped_when_reactivation_sent_recently(inactive_user):
    profile = Profile.objects.get(user=inactive_user)
    log_email_send(inactive_user, EmailSendLog.TYPE_REACTIVATION)
    assert reactivation_sent_recently(inactive_user) is True
    assert is_eligible_for_reactivation(inactive_user, profile) is False


@patch("core.reactivation_email.is_email_configured", return_value=True)
@patch("core.reactivation_email.render_to_string", return_value="<p>Come back</p>")
@patch("core.reactivation_email.mail.send_mail", return_value=1)
def test_sends_when_eligible(mock_send, _mock_render, _mock_email, inactive_user):
    assert send_reactivation_for_user(inactive_user) is True
    mock_send.assert_called_once()
    assert reactivation_sent_recently(inactive_user) is True
    assert send_reactivation_for_user(inactive_user) is False
    mock_send.assert_called_once()
