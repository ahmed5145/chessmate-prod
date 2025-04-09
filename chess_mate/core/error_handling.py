"""
Error handling utilities for the ChessMate application.

Provides standardized error responses, exception handling, and custom exceptions.
"""

import functools
import logging
import threading
import traceback
import uuid
from typing import Any, Callable, Dict, List, Optional, Type, Union, Literal, TypedDict, cast
from functools import wraps

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import (
    APIException, 
    AuthenticationFailed, 
    PermissionDenied, 
    Throttled,
    ValidationError as DRFValidationError
)
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

logger = logging.getLogger(__name__)

# Thread-local storage for request_id
_thread_local = threading.local()

def get_request_id():
    """
    Get the current request ID from thread-local storage.
    If not set, returns a default value.
    """
    return getattr(_thread_local, "request_id", "no_request_id")

# Define types for error response structure
class ErrorResponseDict(TypedDict):
    status: Literal["error"]
    code: Optional[str]
    message: Optional[str]
    details: Optional[Any]
    request_id: Optional[str]

# Standard error response structure
ERROR_RESPONSE_STRUCTURE: ErrorResponseDict = {
    "status": "error", 
    "code": None, 
    "message": None, 
    "details": None, 
    "request_id": None
}

# Error code mapping
ERROR_CODES = {
    # Authentication errors
    "authentication_failed": "AUTH_001",
    "invalid_token": "AUTH_002",
    "token_expired": "AUTH_003",
    "missing_token": "AUTH_004",
    "permission_denied": "AUTH_005",
    # Validation errors
    "validation_failed": "VAL_001",
    "missing_required_field": "VAL_002",
    "invalid_field_format": "VAL_003",
    "invalid_field_value": "VAL_004",
    # Resource errors
    "resource_not_found": "RES_001",
    "resource_already_exists": "RES_002",
    "resource_deleted": "RES_003",
    "resource_locked": "RES_004",
    # External service errors
    "external_service_error": "EXT_001",
    "chess_com_api_error": "EXT_002",
    "lichess_api_error": "EXT_003",
    "stockfish_error": "EXT_004",
    "openai_api_error": "EXT_005",
    "stripe_api_error": "EXT_006",
    # Rate limiting errors
    "rate_limit_exceeded": "RATE_001",
    "credit_limit_exceeded": "RATE_002",
    # Server errors
    "server_error": "SRV_001",
    "database_error": "SRV_002",
    "cache_error": "SRV_003",
    "task_queue_error": "SRV_004",
    # Task errors
    "task_error": "TASK_001",
    "task_not_found": "TASK_002",
    "task_already_exists": "TASK_003",
    "task_failed": "TASK_004",
    "task_timeout": "TASK_005",
    # Unsupported operations
    "method_not_allowed": "OP_001",
    "unsupported_operation": "OP_002",
    "feature_not_available": "OP_003",
    # Generic errors
    "bad_request": "GEN_001",
    "internal_error": "GEN_002",
    "not_implemented": "GEN_003",
    "unavailable": "GEN_004",
}


def create_error_response(
    error_type: str,
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    details: Optional[Any] = None,
    request_id: Optional[str] = None,
) -> JsonResponse:
    """
    Create a standardized error response.

    Args:
        error_type: The type of error (key from ERROR_CODES)
        message: Human-readable error message
        status_code: HTTP status code
        details: Additional error details
        request_id: Optional request ID for tracking

    Returns:
        JsonResponse with standardized error format
    """
    error_code = ERROR_CODES.get(error_type, ERROR_CODES["internal_error"])

    response_data = ERROR_RESPONSE_STRUCTURE.copy()
    response_data.update({"code": error_code, "message": message, "details": details, "request_id": request_id})

    return JsonResponse(response_data, status=status_code)


def handle_view_exception(exc: Exception, request_id: Optional[str] = None) -> JsonResponse:
    """
    Handle exceptions raised in view functions.

    Args:
        exc: The exception that was raised
        request_id: Optional request ID for tracking

    Returns:
        JsonResponse with appropriate error details
    """
    # Log the exception with traceback
    logger.error(f"Error handling request: {str(exc)}", exc_info=True, extra={"request_id": request_id})

    # Handle different types of exceptions
    if isinstance(exc, APIException):
        # Handle REST framework exceptions
        status_code = exc.status_code
        error_type = "bad_request"
        message = str(exc.detail)
        details = None

        # Map exception types to error codes
        if status_code == status.HTTP_401_UNAUTHORIZED:
            error_type = "authentication_failed"
        elif status_code == status.HTTP_403_FORBIDDEN:
            error_type = "permission_denied"
        elif status_code == status.HTTP_404_NOT_FOUND:
            error_type = "resource_not_found"
        elif status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
            error_type = "method_not_allowed"
        elif status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            error_type = "rate_limit_exceeded"
    else:
        # Handle generic exceptions
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_type = "internal_error"

        # Use generic message in production for security
        if settings.DEBUG:
            message = str(exc)
            details = traceback.format_exc()
        else:
            message = "An unexpected error occurred"
            details = None

    return create_error_response(
        error_type=error_type, message=message, status_code=status_code, details=details, request_id=request_id
    )


def api_error_handler(view_func: Callable) -> Callable:
    """
    Decorator to handle exceptions in API views consistently.

    Args:
        view_func: The view function to wrap

    Returns:
        Wrapped function with error handling
    """

    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Generate request ID if not present
        request_id = getattr(request, "request_id", None)

        try:
            return view_func(request, *args, **kwargs)
        except Exception as exc:
            return handle_view_exception(exc, request_id)

    return wrapper


def handle_api_error(exc: Exception, request_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Handle API exceptions and return a standardized error response dictionary.

    Args:
        exc: The exception that was raised
        request_id: Optional request ID for tracking

    Returns:
        Dictionary with standardized error format
    """
    # Log the exception with traceback
    logger.error(f"API Error: {str(exc)}", exc_info=True, extra={"request_id": request_id})

    # Handle different types of exceptions
    if isinstance(exc, BaseError):
        # Use the error's own attributes
        status_code = exc.status_code
        error_type = exc.error_type
        message = str(exc)
        details = exc.details
    elif isinstance(exc, APIException):
        # Handle REST framework exceptions
        status_code = exc.status_code
        error_type = "bad_request"
        message = str(exc.detail)
        details = None

        # Map exception types to error codes
        if status_code == status.HTTP_401_UNAUTHORIZED:
            error_type = "authentication_failed"
        elif status_code == status.HTTP_403_FORBIDDEN:
            error_type = "permission_denied"
        elif status_code == status.HTTP_404_NOT_FOUND:
            error_type = "resource_not_found"
        elif status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
            error_type = "method_not_allowed"
        elif status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            error_type = "rate_limit_exceeded"
    else:
        # Handle generic exceptions
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_type = "internal_error"

        # Use generic message in production for security
        if settings.DEBUG:
            message = str(exc)
            details = str(traceback.format_exc())  # Convert to string instead of keeping as object
        else:
            message = "An unexpected error occurred"
            details = None

    error_code = ERROR_CODES.get(error_type, ERROR_CODES["internal_error"])

    response_data = ERROR_RESPONSE_STRUCTURE.copy()
    response_data["code"] = error_code
    response_data["message"] = message
    response_data["details"] = details
    response_data["request_id"] = request_id

    return cast(Dict[str, Any], response_data)


def exception_handler(exc: Exception, context: Dict[str, Any]) -> JsonResponse:
    """
    Custom exception handler for Django REST Framework.

    Args:
        exc: The exception that was raised
        context: The exception context

    Returns:
        JsonResponse with standardized error format
    """
    # Try the default REST framework exception handler first
    response = drf_exception_handler(exc, context)
    if response is not None:
        # Convert to our standardized format
        status_code = response.status_code
        error_type = "bad_request"

        # Map status code to error type
        if status_code == status.HTTP_401_UNAUTHORIZED:
            error_type = "authentication_failed"
        elif status_code == status.HTTP_403_FORBIDDEN:
            error_type = "permission_denied"
        elif status_code == status.HTTP_404_NOT_FOUND:
            error_type = "resource_not_found"
        elif status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
            error_type = "method_not_allowed"
        elif status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            error_type = "rate_limit_exceeded"

        # Extract message and details
        details: Optional[Any] = None
        if hasattr(response, "data"):
            if isinstance(response.data, dict):
                if "detail" in response.data:
                    message = str(response.data["detail"])
                    # Extract all fields except 'detail' as additional details
                    other_fields = {k: v for k, v in response.data.items() if k != "detail"}
                    details = other_fields if other_fields else None
                else:
                    message = "Validation error"
                    details = response.data
            else:
                message = str(response.data)
        else:
            message = "An error occurred"

        # Get request ID if available
        request = context.get("request")
        request_id = getattr(request, "request_id", None) if request else None

        # Create standardized response
        error_response = create_error_response(
            error_type=error_type, message=message, status_code=status_code, details=details, request_id=request_id
        )

        return error_response

    # Handle non-DRF exceptions with our custom handler
    request = context.get("request")
    request_id = getattr(request, "request_id", None) if request else None
    return handle_view_exception(exc, request_id)


class BaseError(APIException):
    """Base class for custom API exceptions."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "An error occurred"
    error_type = "internal_error"

    def __init__(self, detail: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.

        Args:
            detail: Human-readable error message
            details: Additional error details
        """
        self.details = details
        super().__init__(detail or self.default_detail)


class AuthenticationError(BaseError):
    """Exception for authentication failures."""

    status_code: int = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication failed"
    error_type = "authentication_failed"


class PermissionDeniedError(BaseError):
    """Exception for authorization failures."""

    status_code: int = status.HTTP_403_FORBIDDEN
    default_detail = "Permission denied"
    error_type = "permission_denied"


class RateLimitExceededError(BaseError):
    """Exception for rate limit violations."""

    status_code: int = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Rate limit exceeded"
    error_type = "rate_limit_exceeded"

    def __init__(self, detail: Optional[str] = None, retry_after: Optional[int] = None):
        """
        Initialize the exception.

        Args:
            detail: Human-readable error message
            retry_after: Seconds until the client can retry
        """
        details = {"retry_after": retry_after} if retry_after else None
        super().__init__(detail, details)


class ServiceUnavailableError(BaseError):
    """Exception for service unavailability."""

    status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Service temporarily unavailable"
    error_type = "unavailable"


class ChessServiceError(APIException):
    """Exception for errors communicating with external chess services."""

    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Error communicating with external chess service"

    def __init__(self, service_name: str, detail: Optional[str] = None):
        self.service_name = service_name
        super().__init__(detail or f"Error communicating with {service_name}")


class ResourceNotFoundError(APIException):
    """Exception for when a requested resource doesn't exist."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "The requested resource was not found"

    def __init__(self, resource_type: str, resource_id: Optional[Any] = None):
        self.resource_type = resource_type
        self.resource_id = resource_id
        detail = f"{resource_type} not found"
        if resource_id is not None:
            detail += f" (ID: {resource_id})"
        super().__init__(detail)


class InvalidOperationError(APIException):
    """Exception for when an operation is invalid in the current context."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid operation"

    def __init__(self, operation: str, reason: str):
        self.operation = operation
        detail = f"Invalid operation '{operation}': {reason}"
        super().__init__(detail)


class CreditLimitError(APIException):
    """Exception for when a user doesn't have enough credits."""

    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = "Not enough credits to perform this operation"

    def __init__(self, required: int, available: int):
        self.required = required
        self.available = available
        detail = f"Not enough credits: {required} required, {available} available"
        super().__init__(detail)


class ValidationError(APIException):
    """Exception for detailed validation errors."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Validation error"

    def __init__(self, errors: List[Dict[str, str]]):
        # Create a structured validation error response
        self.errors = errors
        if len(errors) == 1 and "message" in errors[0]:
            detail = errors[0]["message"]
        else:
            detail = "Validation failed with multiple errors"
        super().__init__(detail)


class TaskError(APIException):
    """Exception for task-related errors."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Task error occurred"

    def __init__(self, detail: str):
        super().__init__(detail or self.default_detail)


class ExternalServiceError(APIException):
    """Exception for external service errors."""

    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "External service error occurred"

    def __init__(self, detail: str):
        super().__init__(detail or self.default_detail)


def create_success_response(
    data: Any = None, message: Optional[str] = None, status_code: int = status.HTTP_200_OK
) -> JsonResponse:
    """
    Create a standardized success response.

    Args:
        data: Response data
        message: Optional success message
        status_code: HTTP status code

    Returns:
        JsonResponse with standardized success format
    """
    response_data = {"status": "success", "data": data if data is not None else {}}

    if message:
        response_data["message"] = message

    return JsonResponse(response_data, status=status_code)


# Standardized error responses for auth issues
def create_auth_error_response(message=None, detail=None, status_code=401):
    """
    Create a standardized authentication error response.
    
    Args:
        message: Human-readable error message
        detail: Additional error details
        status_code: HTTP status code
        
    Returns:
        Response object with standardized error format
    """
    if message is None:
        message = "Authentication required"
        
    error_data = {
        "status": "error",
        "code": "authentication_error",
        "message": message,
        "details": detail if detail else {},
        "request_id": get_request_id(),
    }
    
    return Response(error_data, status=status_code)


# Enhanced error handlers for specific auth scenarios
def handle_token_error(error, context=None):
    """
    Handle JWT token errors with descriptive messages.
    
    Args:
        error: The token error exception
        context: Additional context about where the error occurred
        
    Returns:
        Standardized error response
    """
    logger.warning(f"Token error: {str(error)} | Context: {context}")
    
    # Map common token errors to user-friendly messages
    error_str = str(error).lower()
    if "expired" in error_str:
        message = "Your session has expired. Please log in again."
        code = "token_expired"
    elif "invalid" in error_str:
        message = "Invalid authentication token."
        code = "token_invalid"
    elif "not valid" in error_str:
        message = "Your authentication token is not valid."
        code = "token_invalid"
    else:
        message = "Authentication error. Please log in again."
        code = "token_error"
    
    error_data = {
        "status": "error",
        "code": code,
        "message": message,
        "details": {
            "error": str(error),
            "context": context
        },
        "request_id": get_request_id(),
    }
    
    return Response(error_data, status=status.HTTP_401_UNAUTHORIZED)


def handle_permission_error(message=None, detail=None):
    """
    Handle permission errors with descriptive messages.
    
    Args:
        message: Human-readable error message
        detail: Additional error details
        
    Returns:
        Standardized error response
    """
    if message is None:
        message = "You don't have permission to perform this action."
        
    error_data = {
        "status": "error",
        "code": "permission_denied",
        "message": message,
        "details": detail if detail else {},
        "request_id": get_request_id(),
    }
    
    return Response(error_data, status=status.HTTP_403_FORBIDDEN)


def handle_throttled_error(wait_time=None, scope=None):
    """
    Handle rate limit errors with wait time information.
    
    Args:
        wait_time: Time to wait before retrying (in seconds)
        scope: The rate limiting scope that was exceeded
        
    Returns:
        Standardized error response
    """
    message = "Too many requests. Please slow down."
    if wait_time:
        message += f" Try again in {wait_time} seconds."
    
    error_data = {
        "status": "error",
        "code": "rate_limit_exceeded",
        "message": message,
        "details": {
            "wait_time": wait_time,
            "scope": scope
        },
        "request_id": get_request_id(),
    }
    
    headers = {}
    if wait_time:
        headers["Retry-After"] = str(int(wait_time))
    
    return Response(error_data, status=status.HTTP_429_TOO_MANY_REQUESTS, headers=headers)


# Add this decorator for standardized auth error handling
def auth_error_handler(func):
    """
    Decorator for handling authentication-related errors consistently.
    Similar to api_error_handler but specifically for auth views.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TokenError as e:
            return handle_token_error(e, context=func.__name__)
        except InvalidToken as e:
            return handle_token_error(e, context=func.__name__)
        except AuthenticationFailed as e:
            return create_auth_error_response(message=str(e))
        except PermissionDenied as e:
            return handle_permission_error(message=str(e))
        except Throttled as e:
            return handle_throttled_error(wait_time=getattr(e, 'wait', None))
        except DRFValidationError as e:
            return create_error_response(
                error_type="validation_failed",
                message=str(e),
                details={"errors": e.detail if hasattr(e, 'detail') else []},
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unhandled error in {func.__name__}: {str(e)}", exc_info=True)
            return create_error_response(
                error_type="auth_error",
                message="An unexpected error occurred during authentication.",
                details={"error": str(e)} if settings.DEBUG else {},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    return wrapper


class AnalysisError(Exception):
    """Exception raised when game analysis fails."""
    pass


class MetricsError(Exception):
    """Exception raised when metrics calculation fails."""
    pass
