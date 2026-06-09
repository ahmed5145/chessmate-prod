"""Tests for single-game completion email notifications."""

from unittest.mock import MagicMock, patch

import pytest
from core.single_game_notifications import (
    _email_subject,
    send_single_game_complete_email,
)
from django.template.loader import render_to_string
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

    render_context = _mock_render.call_args[0][1]
    assert render_context["report_url"] == "https://chessmate.test/game/168/analysis?mode=review"
    assert render_context["deep_review_url"] == "https://chessmate.test/game/168/analysis?mode=review&move=18"
    assert kwargs["subject"] == "Move 18 swung your game"


@patch("core.single_game_notifications.mail.send_mail", return_value=1)
@patch("core.single_game_notifications.render_to_string", return_value="<p>Ready</p>")
@patch("core.single_game_notifications.get_frontend_base_url", return_value="https://chessmate.test")
@patch("core.single_game_notifications.is_email_configured", return_value=True)
def test_uses_coaching_headline_as_subject(
    _mock_email_configured,
    _mock_frontend_url,
    _mock_render,
    mock_send_mail,
):
    analysis = _analysis(
        feedback={
            "coaching": {
                "headline": "You dropped the initiative on move 18",
                "takeaway": "The knight retreat let White take over.",
            },
            "critical_moments": [{"move_number": 18, "played_move": "Nf3", "best_move": "Nd2"}],
        },
    )

    assert send_single_game_complete_email(_user(), _game(id=42), analysis) is True

    subject = mock_send_mail.call_args.kwargs["subject"]
    assert subject == "You dropped the initiative on move 18"
    render_context = _mock_render.call_args[0][1]
    assert render_context["headline"] == "You dropped the initiative on move 18"
    assert render_context["worst_moment_best"] == "Nd2"
    assert "mode=review" in render_context["deep_review_url"]


def test_email_subject_fallback_move_swing():
    assert _email_subject("", {"move_number": 9}) == "Move 9 swung your game"
    assert _email_subject("Custom headline", {"move_number": 9}) == "Custom headline"


def test_template_renders_headline_and_review_links():
    html = render_to_string(
        "email/single_game_complete.html",
        {
            "user": MagicMock(username="player"),
            "game_id": 5,
            "game_context": {"opponent": "Rival", "result": "loss", "opening_name": "French"},
            "report_url": "https://chessmate.test/game/5/analysis?mode=review",
            "deep_review_url": "https://chessmate.test/game/5/analysis?mode=review&move=14",
            "coach_snippet": "The pawn push was too early.",
            "headline": "Move 14 swung your game",
            "accuracy_pct": 72.3,
            "worst_moment_move": 14,
            "worst_moment_played": "e5",
            "worst_moment_best": "d5",
            "worst_moment_swing": -1.8,
            "worst_moment_type": "mistake",
        },
    )
    assert "Move 14 swung your game" in html
    assert "mode=review&amp;move=14" in html or "mode=review&move=14" in html
    assert "e5" in html
    assert "d5" in html


@patch("core.single_game_notifications.mail.send_mail", side_effect=RuntimeError("SMTP down"))
@patch("core.single_game_notifications.render_to_string", return_value="<p>Ready</p>")
@patch("core.single_game_notifications.is_email_configured", return_value=True)
def test_returns_false_when_send_mail_fails(_mock_email_configured, _mock_render, _mock_send_mail):
    assert send_single_game_complete_email(_user(), _game(), _analysis()) is False
