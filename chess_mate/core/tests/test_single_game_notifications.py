"""Tests for single-game completion email notifications."""

from unittest.mock import MagicMock, patch

import pytest
from core.single_game_notifications import send_single_game_complete_email
from django.test import override_settings


def _game(**overrides):
    game = MagicMock()
    game.id = overrides.get("id", 168)
    game.white = overrides.get("white", "Player")
    game.black = overrides.get("black", "Opponent")
    game.result = overrides.get("result", "win")
    game.opening_name = overrides.get("opening_name", "Sicilian Defense")
    game.opening_played = overrides.get("opening_played", "")
    game.eco_code = overrides.get("eco_code", "B90")
    game.platform = overrides.get("platform", "lichess")
    game.game_url = overrides.get("game_url", "")
    game.date_played = overrides.get("date_played", None)
    return game


def _analysis(**overrides):
    analysis = MagicMock()
    analysis.feedback = overrides.get(
        "feedback",
        {
            "takeaway": "Your largest swing was move 18.",
            "critical_moments": [{"move_number": 18, "played_move": "Nf3"}],
        },
    )
    analysis.analysis_data = overrides.get("analysis_data", {})
    analysis.accuracy_white = overrides.get("accuracy_white", 78.5)
    analysis.accuracy_black = overrides.get("accuracy_black", None)
    analysis.metrics = overrides.get("metrics", {})
    return analysis


def _user(**overrides):
    user = MagicMock()
    user.email = overrides.get("email", "player@example.com")
    user.username = overrides.get("username", "player")
    profile = MagicMock()
    profile.preferences = overrides.get("preferences", {})
    user.profile = profile
    return user


@patch("core.single_game_notifications.is_email_configured", return_value=False)
def test_skips_when_smtp_not_configured(_mock_email_configured):
    assert send_single_game_complete_email(_user(), _game(), _analysis()) is False


@pytest.mark.django_db
@override_settings(SINGLE_GAME_SEND_COMPLETE_EMAIL=False)
@patch("core.single_game_notifications.is_email_configured", return_value=True)
def test_skips_when_setting_disabled(_mock_email_configured):
    assert send_single_game_complete_email(_user(), _game(), _analysis()) is False


@patch("core.single_game_notifications.is_email_configured", return_value=True)
def test_skips_when_user_opted_out(_mock_email_configured):
    user = _user(preferences={"emailNotifications": False})
    assert send_single_game_complete_email(user, _game(), _analysis()) is False


@patch("core.single_game_notifications.mail.send_mail", return_value=1)
@patch("core.single_game_notifications.render_to_string", return_value="<p>Ready</p>")
@patch("core.single_game_notifications.get_frontend_base_url", return_value="https://chessmate.test")
@patch("core.single_game_notifications.is_email_configured", return_value=True)
def test_sends_email_on_completed_single_game(
    _mock_email_configured,
    _mock_frontend_url,
    _mock_render,
    mock_send_mail,
):
    user = _user()
    game = _game(id=168)

    assert send_single_game_complete_email(user, game, _analysis()) is True
    mock_send_mail.assert_called_once()
    kwargs = mock_send_mail.call_args.kwargs
    assert kwargs["recipient_list"] == ["player@example.com"]
    assert "depth-20 game review is ready" in kwargs["subject"].lower()

    render_context = _mock_render.call_args[0][1]
    assert render_context["report_url"] == "https://chessmate.test/game/168/analysis"
    assert render_context["deep_review_url"] == "https://chessmate.test/game/168/analysis?move=18"


@patch("core.single_game_notifications.mail.send_mail", side_effect=RuntimeError("SMTP down"))
@patch("core.single_game_notifications.render_to_string", return_value="<p>Ready</p>")
@patch("core.single_game_notifications.is_email_configured", return_value=True)
def test_returns_false_when_send_mail_fails(_mock_email_configured, _mock_render, _mock_send_mail):
    assert send_single_game_complete_email(_user(), _game(), _analysis()) is False
