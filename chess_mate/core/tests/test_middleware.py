"""Tests for the request validation middleware."""

import json

import pytest
from core.middleware import RequestValidationMiddleware
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """Return an API client for testing."""
    return APIClient()


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(username="testuser", email="test@example.com", password="testpassword")


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an authenticated API client for testing."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
class TestRequestValidationMiddleware:
    """Tests for the RequestValidationMiddleware."""

    def test_valid_request_passes_validation(self, authenticated_client):
        """Test that a valid request passes validation."""
        url = reverse("register")
        data = {"email": "newuser@example.com", "password": "securepassword123", "username": "newuser"}
        response = authenticated_client.post(url, data=json.dumps(data), content_type="application/json")

        # Either a 201 CREATED or 400 BAD REQUEST if email already exists,
        # but not a validation error from the middleware
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            assert "Invalid request data" not in response.json().get("message", "")

    def test_missing_required_field(self, authenticated_client):
        """Test that a request with missing required fields is rejected."""
        url = reverse("register")
        data = {
            "email": "newuser@example.com",
            # Missing 'password' field
            "username": "newuser",
        }
        response = authenticated_client.post(url, data=json.dumps(data), content_type="application/json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert response_data["status"] == "error"
        assert "Invalid request data" in response_data["message"]
        # Check that the error mentions the missing field
        assert any(e["field"] == "password" for e in response_data["errors"])

    def test_invalid_type(self, authenticated_client):
        """Test that a request with invalid field type is rejected."""
        url = reverse("analyze_game", kwargs={"game_id": 1})
        data = {
            "depth": "not_an_integer",  # Should be an integer
        }
        response = authenticated_client.post(url, data=json.dumps(data), content_type="application/json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert response_data["status"] == "error"
        assert "Invalid request data" in response_data["message"]
        assert any(e["field"] == "depth" for e in response_data["errors"])

    def test_invalid_email_format(self, authenticated_client):
        """Test that a request with invalid email format is rejected."""
        url = reverse("register")
        data = {"email": "not_an_email", "password": "securepassword123", "username": "newuser"}  # Invalid email format
        response = authenticated_client.post(url, data=json.dumps(data), content_type="application/json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert any(e["field"] == "email" for e in response_data["errors"])

    def test_password_too_short(self, authenticated_client):
        """Test that a request with a short password is rejected."""
        url = reverse("register")
        data = {"email": "newuser@example.com", "password": "short", "username": "newuser"}  # Too short
        response = authenticated_client.post(url, data=json.dumps(data), content_type="application/json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert any(e["field"] == "password" for e in response_data["errors"])

    def test_invalid_json(self, authenticated_client):
        """Test that a request with invalid JSON is rejected."""
        url = reverse("register")

        # Send invalid JSON
        response = authenticated_client.post(url, data="{not valid json", content_type="application/json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert "Invalid JSON format" in str(response_data)

    def test_non_api_request_not_validated(self, authenticated_client):
        """Test that non-API requests are not validated."""
        # This endpoint doesn't start with /api/
        url = reverse("admin:index")
        response = authenticated_client.get(url)

        # The middleware should not affect this request
        assert response.status_code != status.HTTP_400_BAD_REQUEST

    def test_get_request_not_validated(self, authenticated_client):
        """Test that GET requests are not validated."""
        url = reverse("user_games")
        response = authenticated_client.get(url)

        # GET requests should bypass validation
        assert response.status_code != status.HTTP_400_BAD_REQUEST

    def test_value_validation(self, authenticated_client):
        """Test that value validation works properly."""
        url = reverse("analyze_game", kwargs={"game_id": 1})
        data = {"depth": 50}  # Too high, should be 1-30
        response = authenticated_client.post(url, data=json.dumps(data), content_type="application/json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert any(e["field"] == "depth" for e in response_data["errors"])

    def test_middleware_updates_request_data(self, authenticated_client):
        """Test that the middleware updates the request data after validation."""
        url = reverse("register")
        data = {"email": "validuser@example.com", "password": "securepassword123", "username": "validuser"}
        response = authenticated_client.post(url, data=json.dumps(data), content_type="application/json")

        # The request should be processed normally if validation passes
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            # This would happen if the user already exists
            assert "already exists" in str(response.content)
