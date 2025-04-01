"""Tests for the error handling module."""
import pytest
from django.http import JsonResponse
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth.models import User

from core.error_handling import (
    create_error_response, handle_view_exception, api_error_handler,
    ChessServiceError, ResourceNotFoundError, InvalidOperationError,
    CreditLimitError, ValidationError, create_success_response
)


@pytest.fixture
def api_client():
    """Return an API client for testing."""
    return APIClient()


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpassword'
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an authenticated API client for testing."""
    api_client.force_authenticate(user=user)
    return api_client


class TestErrorHandlingUtilities:
    """Tests for the error handling utility functions."""

    def test_create_error_response(self):
        """Test creating a standardized error response."""
        response = create_error_response(
            error_type="resource_not_found",
            message="Game not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"game_id": 123},
            request_id="test-request-id"
        )
        
        assert isinstance(response, JsonResponse)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        data = response.json()
        assert data["status"] == "error"
        assert data["code"] == "RES_001"  # resource_not_found code
        assert data["message"] == "Game not found"
        assert data["details"] == {"game_id": 123}
        assert data["request_id"] == "test-request-id"

    def test_handle_view_exception_api_exception(self):
        """Test handling of REST framework APIException."""
        exc = ChessServiceError("Chess.com", "API timeout")
        response = handle_view_exception(exc, "test-request-id")
        
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        data = response.json()
        assert data["status"] == "error"
        assert data["message"] == "Error communicating with Chess.com: API timeout"
        assert data["request_id"] == "test-request-id"

    def test_handle_view_exception_generic_exception(self):
        """Test handling of generic Python exception."""
        exc = ValueError("Invalid game ID")
        response = handle_view_exception(exc, "test-request-id")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert data["status"] == "error"
        assert "Invalid game ID" in data["message"]
        assert data["request_id"] == "test-request-id"

    def test_create_success_response(self):
        """Test creating a standardized success response."""
        data = {"game_id": 123, "status": "complete"}
        response = create_success_response(
            data=data,
            message="Game analysis complete",
            status_code=status.HTTP_201_CREATED
        )
        
        assert isinstance(response, JsonResponse)
        assert response.status_code == status.HTTP_201_CREATED
        
        response_data = response.json()
        assert response_data["status"] == "success"
        assert response_data["data"] == data
        assert response_data["message"] == "Game analysis complete"


@pytest.mark.django_db
class TestCustomExceptions:
    """Tests for the custom exception classes."""

    def test_chess_service_error(self):
        """Test ChessServiceError exception."""
        exc = ChessServiceError("Lichess", "API rate limit exceeded")
        assert str(exc) == "Error communicating with Lichess: API rate limit exceeded"
        assert exc.status_code == status.HTTP_502_BAD_GATEWAY

    def test_resource_not_found_error(self):
        """Test ResourceNotFoundError exception."""
        exc = ResourceNotFoundError("Game", 123)
        assert str(exc) == "Game with ID 123 not found"
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        
        # Test without ID
        exc = ResourceNotFoundError("User profile")
        assert str(exc) == "User profile not found"

    def test_invalid_operation_error(self):
        """Test InvalidOperationError exception."""
        exc = InvalidOperationError("analyze game", "game is already being analyzed")
        assert str(exc) == "Cannot analyze game: game is already being analyzed"
        assert exc.status_code == status.HTTP_400_BAD_REQUEST

    def test_credit_limit_error(self):
        """Test CreditLimitError exception."""
        exc = CreditLimitError(10, 5)
        assert str(exc) == "This operation requires 10 credits, but you only have 5 credits"
        assert exc.status_code == status.HTTP_402_PAYMENT_REQUIRED

    def test_validation_error(self):
        """Test ValidationError exception."""
        errors = [
            {"field": "email", "message": "Invalid email format"},
            {"field": "password", "message": "Password too short"}
        ]
        exc = ValidationError(errors)
        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert exc.detail["message"] == "Validation failed"
        assert exc.detail["errors"] == errors


@api_error_handler
def sample_view_function(request, raise_error=False, error_type=None):
    """Sample view function for testing the error handler decorator."""
    if raise_error:
        if error_type == "chess_service":
            raise ChessServiceError("Chess.com", "API timeout")
        elif error_type == "resource_not_found":
            raise ResourceNotFoundError("Game", 123)
        elif error_type == "validation":
            errors = [{"field": "email", "message": "Invalid email format"}]
            raise ValidationError(errors)
        else:
            raise ValueError("Something went wrong")
    
    return create_success_response({"message": "Success"})


class TestErrorHandlerDecorator:
    """Tests for the api_error_handler decorator."""

    def test_successful_view(self):
        """Test decorator on a successful view function."""
        request = type('Request', (), {'request_id': 'test-id'})()
        response = sample_view_function(request)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "success"

    def test_api_exception_view(self):
        """Test decorator handling of API exceptions."""
        request = type('Request', (), {'request_id': 'test-id'})()
        response = sample_view_function(request, raise_error=True, error_type="chess_service")
        
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert response.json()["status"] == "error"
        assert "Chess.com" in response.json()["message"]

    def test_resource_not_found_view(self):
        """Test decorator handling of ResourceNotFoundError."""
        request = type('Request', (), {'request_id': 'test-id'})()
        response = sample_view_function(request, raise_error=True, error_type="resource_not_found")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["status"] == "error"
        assert "Game with ID 123 not found" in response.json()["message"]

    def test_validation_error_view(self):
        """Test decorator handling of ValidationError."""
        request = type('Request', (), {'request_id': 'test-id'})()
        response = sample_view_function(request, raise_error=True, error_type="validation")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["status"] == "error"
        assert "Validation failed" in str(response.json()["message"])

    def test_generic_exception_view(self):
        """Test decorator handling of generic exceptions."""
        request = type('Request', (), {'request_id': 'test-id'})()
        response = sample_view_function(request, raise_error=True)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["status"] == "error"
        assert "Something went wrong" in response.json()["message"] 