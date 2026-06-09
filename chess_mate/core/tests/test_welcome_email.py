"""Tests for SRG-22 welcome email after verification."""

from unittest.mock import patch

import pytest
from core.models import Profile
from core.welcome_email import (
    WELCOME_EMAIL_SENT_KEY,
    send_welcome_email_once,
    welcome_email_already_sent,
)
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def verified_user(db):
    user = User.objects.create_user(
        username="welcome_user",
        email="welcome@example.com",
        password="Test.Password.123",
    )
    profile = Profile.objects.get(user=user)
    profile.email_verified = True
    profile.save(update_fields=["email_verified", "legacy_rating"])
    return user


@pytest.fixture
def unverified_user(db):
    user = User.objects.create_user(
        username="unverified_user",
        email="unverified@example.com",
        password="Test.Password.123",
    )
    profile = Profile.objects.get(user=user)
    profile.email_verified = False
    profile.save(update_fields=["email_verified", "legacy_rating"])
    return user


def test_welcome_email_not_sent_without_verification(unverified_user):
    profile = Profile.objects.get(user=unverified_user)
    with patch("core.welcome_email.is_email_configured", return_value=True):
        with patch("core.welcome_email.mail.send_mail") as mock_send:
            assert send_welcome_email_once(unverified_user, profile) is False
            mock_send.assert_not_called()


@patch("core.welcome_email.mail.send_mail", return_value=1)
@patch("core.welcome_email.render_to_string", return_value="<p>Welcome</p>")
@patch("core.welcome_email.is_email_configured", return_value=True)
def test_sends_welcome_once_after_verify(
    _mock_email_configured,
    _mock_render,
    mock_send_mail,
    verified_user,
):
    profile = Profile.objects.get(user=verified_user)
    assert welcome_email_already_sent(profile) is False

    assert send_welcome_email_once(verified_user, profile) is True
    mock_send_mail.assert_called_once()
    assert mock_send_mail.call_args.kwargs["recipient_list"] == [verified_user.email]

    profile.refresh_from_db()
    assert welcome_email_already_sent(profile) is True
    assert profile.get_preference(WELCOME_EMAIL_SENT_KEY)

    mock_send_mail.reset_mock()
    assert send_welcome_email_once(verified_user, profile) is False
    mock_send_mail.assert_not_called()
