"""Tests for shared coaching email budget (SRG-13/15 global gate)."""

from datetime import timedelta

import pytest
from core.email_send_log import (
    MAX_COACHING_EMAILS_PER_7_DAYS,
    coaching_email_budget_exceeded,
    coaching_emails_in_last_days,
    log_email_send,
    user_active_within_hours,
)
from core.models import EmailSendLog
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def mail_user(db):
    return User.objects.create_user(
        username="mail_budget_user",
        email="budget@example.com",
        password="Test.Password.123",
    )


def test_coaching_emails_in_last_days_counts_only_coaching_types(mail_user):
    log_email_send(mail_user, EmailSendLog.TYPE_WEEKLY_DIGEST, week_key="2026-W23")
    log_email_send(mail_user, EmailSendLog.TYPE_REACTIVATION)
    assert coaching_emails_in_last_days(mail_user) == 1


def test_coaching_email_budget_exceeded_at_cap(mail_user):
    log_email_send(mail_user, EmailSendLog.TYPE_WEEKLY_DIGEST, week_key="2026-W23")
    log_email_send(mail_user, EmailSendLog.TYPE_SPACED_MOMENT, week_key="game:1:move:4")
    assert coaching_emails_in_last_days(mail_user) == 2
    assert coaching_email_budget_exceeded(mail_user) is True


def test_coaching_email_budget_allows_under_cap(mail_user):
    log_email_send(
        mail_user, EmailSendLog.TYPE_ANALYSIS_COMPLETION, meta={"game_id": 1}
    )
    assert coaching_email_budget_exceeded(mail_user) is False
    assert coaching_emails_in_last_days(mail_user) == 1


def test_user_active_within_hours(mail_user):
    mail_user.last_login = timezone.now() - timedelta(hours=12)
    mail_user.save(update_fields=["last_login"])
    assert user_active_within_hours(mail_user, hours=72) is True

    mail_user.last_login = timezone.now() - timedelta(days=5)
    mail_user.save(update_fields=["last_login"])
    assert user_active_within_hours(mail_user, hours=72) is False


def test_budget_constant_matches_plan():
    assert MAX_COACHING_EMAILS_PER_7_DAYS == 2
