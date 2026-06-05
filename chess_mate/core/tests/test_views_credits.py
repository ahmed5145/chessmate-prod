import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from core.models import Profile


@pytest.mark.django_db
class TestCreditsViews:
    def setup_method(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="credits_user",
            email="credits@example.com",
            password="testpass123",
        )
        Profile.objects.create(user=self.user, credits=12)
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

    def test_purchase_without_stripe_returns_503(self, settings):
        settings.STRIPE_SECRET_KEY = ""
        response = self.client.post("/api/v1/purchase-credits/", {"package_id": "basic"})
        assert response.status_code == 503

    def test_purchase_invalid_package(self, settings):
        settings.STRIPE_SECRET_KEY = "sk_test_x"
        response = self.client.post("/api/v1/purchase-credits/", {"package_id": "invalid"})
        assert response.status_code == 400
