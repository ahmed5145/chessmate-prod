"""Tests for batch completion email notifications."""

from unittest.mock import MagicMock, patch

from core.batch_notifications import send_batch_complete_email


def _batch_report(**overrides):
    report = MagicMock()
    report.pk = overrides.get("pk", 42)
    report.games_count = overrides.get("games_count", 10)
    report.status = overrides.get("status", "completed")
    report.batch_summary = overrides.get(
        "batch_summary",
        {"overall_accuracy_pct": 72.5, "overall_eval_stability": 0.81},
    )
    report.coaching_report = overrides.get(
        "coaching_report",
        {"executive_summary": "Focus on hanging pieces in the middlegame."},
    )
    return report


@patch("core.batch_notifications.is_email_configured", return_value=False)
def test_skips_when_smtp_not_configured(_mock_email_configured):
    user = MagicMock(email="player@example.com")
    assert send_batch_complete_email(user, _batch_report()) is False


@patch("core.batch_notifications.is_email_configured", return_value=True)
def test_skips_when_user_has_no_email(_mock_email_configured):
    user = MagicMock(email=None)
    assert send_batch_complete_email(user, _batch_report()) is False


@patch("core.batch_notifications.mail.send_mail", return_value=1)
@patch("core.batch_notifications.render_to_string", return_value="<p>Ready</p>")
@patch(
    "core.batch_notifications.get_frontend_base_url",
    return_value="https://chessmate.test",
)
@patch("core.batch_notifications.is_email_configured", return_value=True)
def test_sends_email_on_completed_batch(
    _mock_email_configured,
    _mock_frontend_url,
    _mock_render,
    mock_send_mail,
):
    user = MagicMock(email="player@example.com")
    batch = _batch_report(status="completed")

    assert send_batch_complete_email(user, batch) is True
    mock_send_mail.assert_called_once()
    kwargs = mock_send_mail.call_args.kwargs
    assert kwargs["recipient_list"] == ["player@example.com"]
    assert "batch coach report is ready" in kwargs["subject"].lower()

    render_context = _mock_render.call_args[0][1]
    assert render_context["report_url"] == "https://chessmate.test/batch-report/42"
    assert render_context["status"] == "completed"


@patch("core.batch_notifications.mail.send_mail", return_value=1)
@patch(
    "core.batch_notifications.render_to_string",
    side_effect=Exception("template missing"),
)
@patch(
    "core.batch_notifications.get_frontend_base_url",
    return_value="https://chessmate.test",
)
@patch("core.batch_notifications.is_email_configured", return_value=True)
def test_template_render_failure_uses_plaintext_fallback(
    _mock_email_configured,
    _mock_frontend_url,
    _mock_render,
    mock_send_mail,
):
    user = MagicMock(email="player@example.com")

    assert send_batch_complete_email(user, _batch_report()) is True
    plain = mock_send_mail.call_args.kwargs["message"]
    assert "batch coach report" in plain.lower()
    assert "https://chessmate.test/batch-report/42" in plain


@patch("core.batch_notifications.mail.send_mail", side_effect=RuntimeError("SMTP down"))
@patch("core.batch_notifications.render_to_string", return_value="<p>Ready</p>")
@patch("core.batch_notifications.is_email_configured", return_value=True)
def test_returns_false_when_send_mail_fails(_mock_email_configured, _mock_render, _mock_send_mail):
    user = MagicMock(email="player@example.com")
    assert send_batch_complete_email(user, _batch_report()) is False
