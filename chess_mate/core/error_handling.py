"""
Error handling utilities for the ChessMate API.

This module provides standardized error response formats, utility functions,
and decorators for consistent error handling across all API endpoints.
"""

import logging
import functools
import traceback
from typing import Any, Callable, Dict, List, Optional, Type, Union

from django.conf import settings
from django.http import JsonResponse
from rest_framework import status
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)

# Standard error response structure
ERROR_RESPONSE_STRUCTURE = {
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
    request_id: Optional[str] = None
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
    response_data.update({
        "code": error_code,
        "message": message,
        "details": details,
        "request_id": request_id
    })
    
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
    logger.error(
        f"Error handling request: {str(exc)}",
        exc_info=True,
        extra={"request_id": request_id}
    )
    
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
        error_type=error_type,
        message=message,
        status_code=status_code,
        details=details,
        request_id=request_id
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
        request_id = getattr(request, 'request_id', None)
        
        try:
            return view_func(request, *args, **kwargs)
        except Exception as exc:
            return handle_view_exception(exc, request_id)
            
    return wrapper


def custom_exception_handler(exc: Exception, context: Dict) -> JsonResponse:
    """
    Custom exception handler for DRF.
    
    This function can be used as the EXCEPTION_HANDLER setting in DRF
    to provide consistent error handling for all API views.
    
    Args:
        exc: The exception that was raised
        context: The exception context provided by DRF
        
    Returns:
        JsonResponse with standardized error format
    """
    # Try the DRF exception handler first
    response = drf_exception_handler(exc, context)
    
    # If DRF couldn't handle it or there's no response, use our handler
    if response is None:
        request = context.get('request')
        request_id = getattr(request, 'request_id', None)
        return handle_view_exception(exc, request_id)
    
    # If DRF did handle it but we want to standardize the format
    status_code = response.status_code
    
    error_type = "bad_request"
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
    elif status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        error_type = "server_error"
    
    # Create our standard error response
    request = context.get('request')
    request_id = getattr(request, 'request_id', None)
    
    response_data = ERROR_RESPONSE_STRUCTURE.copy()
    response_data.update({
        "code": ERROR_CODES.get(error_type, ERROR_CODES["internal_error"]),
        "message": str(response.data),
        "details": response.data if isinstance(response.data, dict) else None,
        "request_id": request_id
    })
    
    response.data = response_data
    return response


# Custom exception classes for specific error scenarios
class ChessServiceError(APIException):
    """Exception for errors communicating with external chess services."""
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Error communicating with external chess service"
    
    def __init__(self, service_name: str, detail: Optional[str] = None):
        if detail is None:
            detail = f"Error communicating with {service_name}"
        super().__init__(detail)


class ResourceNotFoundError(APIException):
    """Exception for when a requested resource doesn't exist."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "The requested resource was not found"
    
    def __init__(self, resource_type: str, resource_id: Optional[Any] = None):
        detail = f"{resource_type} not found"
        if resource_id is not None:
            detail = f"{resource_type} with ID {resource_id} not found"
        super().__init__(detail)


class InvalidOperationError(APIException):
    """Exception for when an operation is invalid in the current context."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid operation"
    
    def __init__(self, operation: str, reason: str):
        detail = f"Cannot {operation}: {reason}"
        super().__init__(detail)


class CreditLimitError(APIException):
    """Exception for when a user doesn't have enough credits."""
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = "Not enough credits to perform this operation"
    
    def __init__(self, required: int, available: int):
        detail = f"This operation requires {required} credits, but you only have {available} credits"
        super().__init__(detail)


class ValidationError(APIException):
    """Exception for detailed validation errors."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Validation error"
    
    def __init__(self, errors: List[Dict[str, str]]):
        # Create a structured validation error response
        detail = {
            "message": "Validation failed",
            "errors": errors
        }
        super().__init__(detail)


# Create success response with consistent format
def create_success_response(
    data: Any = None,
    message: Optional[str] = None,
    status_code: int = status.HTTP_200_OK
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
    response_data = {
        "status": "success",
        "data": data
    }
    
    if message is not None:
        response_data["message"] = message
        
    return JsonResponse(response_data, status=status_code) 