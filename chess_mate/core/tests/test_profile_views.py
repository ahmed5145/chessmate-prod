"""
Tests for profile views.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .. import profile_views
from ..models import Payment, Profile, Subscription


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_user():
    user = User.objects.create_user(username="testuser", email="test@example.com", password="testpassword123")
    Profile.objects.create(
        user=user,
        email_verified=True,
        credits=10,
        chess_com_username="testuser",
        lichess_username="testuser_lichess",
        elo_rating=1500,
        analysis_count=5,
        preferences={"theme": "light", "notifications_enabled": True, "analysis_depth": "balanced"},
    )
    return user


@pytest.fixture
def authenticated_client(api_client, test_user):
    url = reverse("login")
    data = {"email": "test@example.com", "password": "testpassword123"}
    response = api_client.post(url, data, format="json")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return api_client


@pytest.mark.django_db
class TestProfileViews:
    def test_profile_view(self, authenticated_client, test_user):
        url = reverse("user_profile")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        # Check basic user data
        assert response.data["username"] == "testuser"
        assert response.data["email"] == "test@example.com"

        # Check profile data
        assert response.data["credits"] == 10
        assert response.data["chess_com_username"] == "testuser"
        assert response.data["lichess_username"] == "testuser_lichess"
        assert response.data["elo_rating"] == 1500
        assert response.data["analysis_count"] == 5

        # Check preferences
        assert response.data["preferences"]["theme"] == "light"
        assert response.data["preferences"]["notifications_enabled"] is True
        assert response.data["preferences"]["analysis_depth"] == "balanced"

    def test_profile_view_unauthorized(self, api_client):
        url = reverse("user_profile")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_profile(self, authenticated_client, test_user):
        url = reverse("update_profile")
        data = {
            "first_name": "Test",
            "last_name": "User",
            "chess_com_username": "testuser_updated",
            "lichess_username": "testuser_lichess_updated",
            "elo_rating": 1600,
        }
        response = authenticated_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK

        # Reload user from database
        test_user.refresh_from_db()
        test_user.profile.refresh_from_db()

        # Check updated user data
        assert test_user.first_name == "Test"
        assert test_user.last_name == "User"

        # Check updated profile data
        assert test_user.profile.chess_com_username == "testuser_updated"
        assert test_user.profile.lichess_username == "testuser_lichess_updated"
        assert test_user.profile.elo_rating == 1600

    def test_update_profile_partial(self, authenticated_client, test_user):
        url = reverse("update_profile")
        data = {"first_name": "Test"}
        response = authenticated_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK

        # Reload user from database
        test_user.refresh_from_db()

        # Check updated user data
        assert test_user.first_name == "Test"

        # Check that other fields remained unchanged
        assert test_user.last_name == ""
        assert test_user.profile.chess_com_username == "testuser"

    def test_update_profile_invalid_data(self, authenticated_client, test_user):
        url = reverse("update_profile")
        data = {"elo_rating": "not_a_number"}
        response = authenticated_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "elo_rating" in response.data

    def test_subscribe_pro_plan(self, authenticated_client, test_user):
        # Mock Stripe API calls
        with patch("stripe.PaymentIntent.create") as mock_payment_intent:
            mock_payment_intent.return_value = {"id": "pi_test123", "client_secret": "secret_test123"}

            url = reverse("subscribe_pro_plan")
            data = {"plan": "monthly", "payment_method_id": "pm_test123"}
            response = authenticated_client.post(url, data, format="json")

            assert response.status_code == status.HTTP_200_OK
            assert "client_secret" in response.data
            assert response.data["client_secret"] == "secret_test123"

            # Check that a subscription record was created
            assert Subscription.objects.filter(user=test_user).exists()

            subscription = Subscription.objects.get(user=test_user)
            assert subscription.plan == "monthly"
            assert subscription.active is False  # Not active until payment confirmed

    def test_subscribe_pro_plan_invalid_plan(self, authenticated_client, test_user):
        url = reverse("subscribe_pro_plan")
        data = {"plan": "invalid_plan", "payment_method_id": "pm_test123"}
        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "plan" in response.data

    def test_confirm_subscription(self, authenticated_client, test_user):
        # Create a pending subscription
        subscription = Subscription.objects.create(
            user=test_user, plan="monthly", stripe_subscription_id="sub_test123", active=False
        )

        # Mock Stripe API calls
        with patch("stripe.Subscription.retrieve") as mock_retrieve:
            mock_retrieve.return_value = {"status": "active", "current_period_end": 1672531200}  # 2023-01-01T00:00:00Z

            url = reverse("confirm_subscription")
            data = {"subscription_id": "sub_test123"}
            response = authenticated_client.post(url, data, format="json")

            assert response.status_code == status.HTTP_200_OK
            assert "message" in response.data
            assert "Successfully confirmed subscription" in response.data["message"]

            # Reload subscription from database
            subscription.refresh_from_db()
            assert subscription.active is True

    def test_purchase_credits(self, authenticated_client, test_user):
        # Initial credits
        initial_credits = test_user.profile.credits

        # Mock Stripe API calls
        with patch("stripe.PaymentIntent.create") as mock_payment_intent:
            mock_payment_intent.return_value = {"id": "pi_test123", "client_secret": "secret_test123"}

            url = reverse("purchase_credits")
            data = {"credit_package": "50_credits", "payment_method_id": "pm_test123"}
            response = authenticated_client.post(url, data, format="json")

            assert response.status_code == status.HTTP_200_OK
            assert "client_secret" in response.data
            assert response.data["client_secret"] == "secret_test123"

            # Check that a payment record was created
            assert Payment.objects.filter(user=test_user).exists()

            payment = Payment.objects.get(user=test_user)
            assert payment.amount == 9.99  # Assuming 50 credits cost $9.99
            assert payment.credit_amount == 50
            assert payment.status == "pending"

            # Credits should not be added until payment is confirmed
            test_user.profile.refresh_from_db()
            assert test_user.profile.credits == initial_credits

    def test_confirm_credit_purchase(self, authenticated_client, test_user):
        # Initial credits
        initial_credits = test_user.profile.credits

        # Create a pending payment
        payment = Payment.objects.create(
            user=test_user, amount=9.99, credit_amount=50, stripe_payment_id="pi_test123", status="pending"
        )

        # Mock Stripe API calls
        with patch("stripe.PaymentIntent.retrieve") as mock_retrieve:
            mock_retrieve.return_value = {"status": "succeeded"}

            url = reverse("confirm_credit_purchase")
            data = {"payment_intent_id": "pi_test123"}
            response = authenticated_client.post(url, data, format="json")

            assert response.status_code == status.HTTP_200_OK
            assert "message" in response.data
            assert "Successfully added 50 credits" in response.data["message"]

            # Reload payment from database
            payment.refresh_from_db()
            assert payment.status == "completed"

            # Check that credits were added
            test_user.profile.refresh_from_db()
            assert test_user.profile.credits == initial_credits + 50

    def test_update_preferences(self, authenticated_client, test_user):
        url = reverse("update_preferences")
        data = {"preferences": {"theme": "dark", "notifications_enabled": False, "analysis_depth": "deep"}}
        response = authenticated_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK

        # Reload profile from database
        test_user.profile.refresh_from_db()

        # Check updated preferences
        assert test_user.profile.preferences["theme"] == "dark"
        assert test_user.profile.preferences["notifications_enabled"] is False
        assert test_user.profile.preferences["analysis_depth"] == "deep"

    def test_update_preferences_partial(self, authenticated_client, test_user):
        url = reverse("update_preferences")
        data = {"preferences": {"theme": "dark"}}
        response = authenticated_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK

        # Reload profile from database
        test_user.profile.refresh_from_db()

        # Check that only specified preference was updated
        assert test_user.profile.preferences["theme"] == "dark"

        # Other preferences should remain unchanged
        assert test_user.profile.preferences["notifications_enabled"] is True
        assert test_user.profile.preferences["analysis_depth"] == "balanced"

    def test_update_preferences_invalid_data(self, authenticated_client, test_user):
        url = reverse("update_preferences")
        data = {"preferences": {"theme": "invalid_theme"}}
        response = authenticated_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "preferences" in response.data
