import pytest
from core.email_utils import email_template_context, get_support_email
from django.core.management import call_command
from io import StringIO


def test_get_support_email_prefers_support_env(settings):
    settings.SUPPORT_EMAIL = "support@example.com"
    settings.DEFAULT_FROM_EMAIL = "noreply@example.com"
    assert get_support_email() == "support@example.com"


def test_get_support_email_falls_back_to_from_email(settings):
    settings.SUPPORT_EMAIL = ""
    settings.DEFAULT_FROM_EMAIL = "noreply@example.com"
    assert get_support_email() == "noreply@example.com"


def test_email_template_context_includes_support_email(settings):
    settings.SUPPORT_EMAIL = "help@example.com"
    context = email_template_context(user="u1")
    assert context["support_email"] == "help@example.com"
    assert context["user"] == "u1"
    assert "current_year" in context


@pytest.mark.django_db
def test_launch_metrics_command_runs():
    out = StringIO()
    call_command("launch_metrics", "--days", "30", stdout=out)
    output = out.getvalue()
    assert "Signups:" in output
    assert "Second batch within" in output
