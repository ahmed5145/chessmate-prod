import json

import pytest
from core.models import Profile, Transaction
from core.tests.profile_helpers import ensure_profile
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestStripeWebhook:
    def setup_method(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="webhook_user",
            email="webhook@example.com",
            password="testpass123",
        )
        ensure_profile(self.user, credits=5)

    def test_webhook_without_secret_returns_503(self, settings):
        settings.STRIPE_WEBHOOK_SECRET = ""
        response = self.client.post(
            "/api/v1/webhooks/stripe/",
            data=b"{}",
            content_type="application/json",
        )
        assert response.status_code == 503

    def test_webhook_checkout_completed_adds_credits(self, settings, monkeypatch):
        settings.STRIPE_SECRET_KEY = "sk_test_x"
        settings.STRIPE_WEBHOOK_SECRET = "whsec_test"

        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_webhook_1",
                    "mode": "payment",
                    "payment_status": "paid",
                    "amount_total": 999,
                    "metadata": {
                        "user_id": str(self.user.id),
                        "credits": "50",
                        "package_id": "basic",
                    },
                }
            },
        }

        class FakeStripeError(Exception):
            pass

        FakeStripeError.SignatureVerificationError = type("SignatureVerificationError", (Exception,), {})

        def fake_construct(payload, sig, secret):
            assert secret == "whsec_test"
            return event

        monkeypatch.setattr("core.views_credits.stripe.Webhook.construct_event", fake_construct)

        response = self.client.post(
            "/api/v1/webhooks/stripe/",
            data=json.dumps(event).encode(),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig_test",
        )
        assert response.status_code == 200

        self.user.profile.refresh_from_db()
        assert self.user.profile.credits == 55
        assert Transaction.objects.filter(stripe_payment_id="cs_test_webhook_1").exists()

    def test_webhook_idempotent(self, settings, monkeypatch):
        settings.STRIPE_SECRET_KEY = "sk_test_x"
        settings.STRIPE_WEBHOOK_SECRET = "whsec_test"

        Transaction.objects.create(
            user=self.user,
            transaction_type="purchase",
            amount=9.99,
            credits=50,
            status="completed",
            stripe_payment_id="cs_test_dup",
        )
        self.user.profile.credits = 55
        self.user.profile.save()

        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_dup",
                    "mode": "payment",
                    "payment_status": "paid",
                    "amount_total": 999,
                    "metadata": {"user_id": str(self.user.id), "credits": "50"},
                }
            },
        }

        def fake_construct(payload, sig, secret):
            return event

        monkeypatch.setattr("core.views_credits.stripe.Webhook.construct_event", fake_construct)

        response = self.client.post(
            "/api/v1/webhooks/stripe/",
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )
        assert response.status_code == 200
        self.user.profile.refresh_from_db()
        assert self.user.profile.credits == 55


@pytest.mark.django_db
def test_public_site_config():
    client = APIClient()
    response = client.get("/api/v1/public/site-config/")
    assert response.status_code == 200
    assert "support_email" in response.data
    assert response.data["signup_bonus_credits"] >= 10
    assert "demo_batch_share_token" in response.data
    assert response.data["demo_batch_share_token"] is None
    assert response.data["batch_sends_completion_email"] is True
    assert response.data["batch_eta_minutes_per_game_low"] >= 2
    assert "legal_governing_law" in response.data
    assert response.data["legal_entity_incorporated"] is False
