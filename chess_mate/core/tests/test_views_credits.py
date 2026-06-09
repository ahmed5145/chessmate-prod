import pytest
from core.models import Profile
from core.tests.profile_helpers import ensure_profile
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestCreditsViews:
    def setup_method(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="credits_user",
            email="credits@example.com",
            password="testpass123",
        )
        ensure_profile(self.user, credits=12)
        self.client.force_authenticate(user=self.user)

    def test_get_credits_balance(self):
        response = self.client.get("/api/v1/credits/")
        assert response.status_code == 200
        assert response.data["credits"] == 12

    def test_get_credit_packages(self):
        response = self.client.get("/api/v1/credits/packages/")
        assert response.status_code == 200
        assert len(response.data["packages"]) == 3
        ids = {pkg["id"] for pkg in response.data["packages"]}
        assert ids == {"basic", "pro", "premium"}
        starter = next(p for p in response.data["packages"] if p["id"] == "basic")
        assert starter["batch_reports_approx"] == 5
        assert response.data["credits_per_imported_game"] == 1
        assert response.data["batch_included"] is True
        assert isinstance(response.data["summary_points"], list)
        assert len(response.data["summary_points"]) >= 4

    def test_purchase_without_stripe_returns_503(self, settings):
        settings.STRIPE_SECRET_KEY = ""
        response = self.client.post(
            "/api/v1/purchase-credits/", {"package_id": "basic"}
        )
        assert response.status_code == 503

    def test_purchase_invalid_package(self, settings):
        settings.STRIPE_SECRET_KEY = "sk_test_x"
        response = self.client.post(
            "/api/v1/purchase-credits/", {"package_id": "invalid"}
        )
        assert response.status_code == 400

    def test_confirm_purchase_applies_credits(self, settings, monkeypatch):
        settings.STRIPE_SECRET_KEY = "sk_test_x"

        def fake_verify(session_id):
            assert session_id == "cs_test_abc"
            return {
                "amount": 999,
                "credits": 50,
                "user_id": str(self.user.id),
                "package_id": "basic",
            }

        monkeypatch.setattr(
            "core.views_credits.PaymentProcessor.verify_payment", fake_verify
        )

        response = self.client.post(
            "/api/v1/confirm-purchase/", {"payment_id": "cs_test_abc"}
        )
        assert response.status_code == 200
        assert response.data["credits_added"] == 50

        self.user.profile.refresh_from_db()
        assert self.user.profile.credits == 62

    def test_confirm_purchase_rejects_wrong_user(self, settings, monkeypatch):
        settings.STRIPE_SECRET_KEY = "sk_test_x"

        def fake_verify(session_id):
            return {
                "amount": 999,
                "credits": 50,
                "user_id": "99999",
                "package_id": "basic",
            }

        monkeypatch.setattr(
            "core.views_credits.PaymentProcessor.verify_payment", fake_verify
        )

        response = self.client.post(
            "/api/v1/confirm-purchase/", {"payment_id": "cs_test_wrong"}
        )
        assert response.status_code == 400
        assert "different account" in response.data["detail"].lower()
