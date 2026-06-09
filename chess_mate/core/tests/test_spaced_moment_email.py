"""Tests for SRG-13 spaced moment reminder email."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from core.email_send_log import log_email_send
from core.models import EmailSendLog, Game, GameAnalysis, Profile, SpacedReminderLog
from core.notification_preferences import WANTS_SPACED_REPETITION_KEY
from core.spaced_repetition_email import moment_key, send_spaced_repetition_for_user
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def spaced_user(db):
    user = User.objects.create_user(
        username="spaced_user",
        email="spaced@example.com",
        password="Test.Password.123",
    )
    profile = Profile.objects.get(user=user)
    profile.preferences = {WANTS_SPACED_REPETITION_KEY: True}
    profile.save(update_fields=["preferences"])
    return user


@pytest.fixture
def stale_moment_game(spaced_user):
    game = Game.objects.create(
        user=spaced_user,
        platform="lichess",
        game_id="spaced-test-1",
        pgn='[Event "test"]',
        result="loss",
        white="spaced_user",
        black="rival",
        analysis_status="completed",
        status="analyzed",
    )
    analysis = GameAnalysis.objects.create(
        game=game,
        depth=20,
        feedback={
            "coaching": {
                "critical_moments": [
                    {
                        "move_number": 12,
                        "eval_swing": 1.4,
                        "type": "blunder",
                    }
                ]
            }
        },
    )
    GameAnalysis.objects.filter(pk=analysis.pk).update(
        updated_at=timezone.now() - timedelta(days=10)
    )
    return game


@patch("core.spaced_repetition_email.is_email_configured", return_value=True)
@patch("core.spaced_repetition_email.render_to_string", return_value="<p>Spaced</p>")
@patch("core.spaced_repetition_email.send_coaching_email", return_value=1)
def test_sends_for_eligible_moment(
    mock_send, _mock_render, _mock_email, spaced_user, stale_moment_game
):
    with patch(
        "core.spaced_repetition_email.received_coaching_touchpoint_today",
        return_value=False,
    ):
        assert send_spaced_repetition_for_user(spaced_user) is True
    mock_send.assert_called_once()
    assert mock_send.call_args.kwargs["subject"] == "Still thinking about move 12?"
    assert SpacedReminderLog.objects.filter(
        user=spaced_user, moment_key=moment_key(stale_moment_game.id, 12)
    ).exists()


def test_skips_when_digest_sent_this_week(spaced_user, stale_moment_game):
    log_email_send(
        spaced_user,
        EmailSendLog.TYPE_WEEKLY_DIGEST,
        week_key="2026-W23",
    )
    with patch(
        "core.spaced_repetition_email.digest_already_sent_this_week", return_value=True
    ):
        with patch("core.spaced_repetition_email.send_coaching_email") as mock_send:
            assert send_spaced_repetition_for_user(spaced_user) is False
            mock_send.assert_not_called()


def test_skips_duplicate_moment_within_30_days(spaced_user, stale_moment_game):
    SpacedReminderLog.objects.create(
        user=spaced_user,
        moment_key=moment_key(stale_moment_game.id, 12),
    )
    with patch("core.spaced_repetition_email.send_coaching_email") as mock_send:
        assert send_spaced_repetition_for_user(spaced_user) is False
        mock_send.assert_not_called()


def test_skips_when_completion_email_sent_in_last_48h(spaced_user, stale_moment_game):
    log_email_send(
        spaced_user,
        EmailSendLog.TYPE_ANALYSIS_COMPLETION,
        meta={"game_id": stale_moment_game.id},
    )
    with patch("core.spaced_repetition_email.send_coaching_email") as mock_send:
        assert send_spaced_repetition_for_user(spaced_user) is False
        mock_send.assert_not_called()


def test_skips_when_spaced_sent_in_last_7_days(spaced_user, stale_moment_game):
    log_email_send(
        spaced_user,
        EmailSendLog.TYPE_SPACED_MOMENT,
        week_key=moment_key(stale_moment_game.id, 12),
    )
    with patch("core.spaced_repetition_email.send_coaching_email") as mock_send:
        assert send_spaced_repetition_for_user(spaced_user) is False
        mock_send.assert_not_called()


def test_skips_when_weekly_coaching_budget_exceeded(spaced_user, stale_moment_game):
    log_email_send(spaced_user, EmailSendLog.TYPE_WEEKLY_DIGEST, week_key="2026-W23")
    log_email_send(
        spaced_user,
        EmailSendLog.TYPE_ANALYSIS_COMPLETION,
        meta={"game_id": 1},
    )
    with patch("core.spaced_repetition_email.send_coaching_email") as mock_send:
        assert send_spaced_repetition_for_user(spaced_user) is False
        mock_send.assert_not_called()


def test_skips_when_user_active_within_72h(spaced_user, stale_moment_game):
    spaced_user.last_login = timezone.now() - timedelta(hours=6)
    spaced_user.save(update_fields=["last_login"])
    with patch("core.spaced_repetition_email.send_coaching_email") as mock_send:
        assert send_spaced_repetition_for_user(spaced_user) is False
        mock_send.assert_not_called()


def test_skips_when_opted_out(spaced_user, stale_moment_game):
    profile = Profile.objects.get(user=spaced_user)
    profile.preferences = {WANTS_SPACED_REPETITION_KEY: False}
    profile.save(update_fields=["preferences"])
    with patch("core.spaced_repetition_email.send_coaching_email") as mock_send:
        assert send_spaced_repetition_for_user(spaced_user) is False
        mock_send.assert_not_called()
