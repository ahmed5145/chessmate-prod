"""
Middleware components for the ChessMate application.

This module includes middleware for:
1. Request validation against defined schemas
2. Rate limiting API requests
3. Request ID tracking for better debugging
4. Security headers for HTTP responses
5. Logging request IDs for correlation
"""

import json
import logging
import re
import threading
import time
import uuid
from datetime import datetime
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Tuple,
    TypedDict,
    Union,
    cast,
)

import redis
from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from django.utils.cache import add_never_cache_headers

from .cache import CACHE_BACKEND_REDIS, cache_delete, cache_get, cache_set
from .error_handling import create_error_response
from .rate_limiting import limiter

logger = logging.getLogger(__name__)

# Thread-local storage for request_id
_thread_local = threading.local()


# Define TypedDict classes for schema validation
class TypeValidation(TypedDict, total=False):
    """Type hints for type validation in schema."""

    email: type
    password: type
    username: type
    first_name: type
    last_name: type
    platform: type
    time_period: type
    limit: type
    depth: type
    lines: type
    focus_areas: type
    game_ids: type
    bio: type
    chess_com_username: type
    lichess_username: type


class ValueValidation(TypedDict, total=False):
    """Type hints for value validation in schema."""

    depth: Callable[[int], bool]
    lines: Callable[[int], bool]
    limit: Callable[[int], bool]
    platform: Callable[[str], bool]
    game_ids: Callable[[List], bool]
    focus_areas: Callable[[List], bool]


class CustomValidators(TypedDict, total=False):
    """Type hints for custom validators in schema."""

    email: Callable[[str], bool]
    password: Callable[[str], bool]


class SchemaOptions(TypedDict, total=False):
    """Type hints for schema options."""

    required: List[str]
    optional: List[str]
    type_validation: TypeValidation
    value_validation: ValueValidation
    custom_validators: CustomValidators


class MethodSchema(TypedDict, total=False):
    """Type hints for HTTP method schemas."""

    POST: SchemaOptions
    PUT: SchemaOptions
    GET: SchemaOptions
    DELETE: SchemaOptions


# Validation schemas defined as a mapping of URL patterns to required fields and their types
VALIDATION_SCHEMAS: Dict[str, MethodSchema] = {
    # Auth endpoints
    r"^/api/register/$": {
        "POST": {
            "required": ["email", "password", "username"],
            "optional": ["first_name", "last_name"],
            "type_validation": {"email": str, "password": str, "username": str, "first_name": str, "last_name": str},
            "custom_validators": {
                "email": lambda x: re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", x) is not None,
                "password": lambda x: len(x) >= 8,
            },
        }
    },
    r"^/api/login/$": {"POST": {"required": ["email", "password"], "type_validation": {"email": str, "password": str}}},
    # Game endpoints
    r"^/api/games/\d+/analyze/$": {
        "POST": {
            "optional": ["depth", "lines"],
            "type_validation": {"depth": int, "lines": int},
            "value_validation": {"depth": lambda x: 1 <= x <= 30, "lines": lambda x: 1 <= x <= 5},
        }
    },
    r"^/api/games/fetch/$": {
        "POST": {
            "required": ["platform", "username"],
            "optional": ["time_period", "limit"],
            "type_validation": {"platform": str, "username": str, "time_period": str, "limit": int},
            "value_validation": {"limit": lambda x: 1 <= x <= 100, "platform": lambda x: x in ["chess.com", "lichess"]},
        }
    },
    # Profile endpoints
    r"^/api/profile/update/$": {
        "PUT": {
            "optional": ["username", "first_name", "last_name", "bio", "chess_com_username", "lichess_username"],
            "type_validation": {
                "username": str,
                "first_name": str,
                "last_name": str,
                "bio": str,
                "chess_com_username": str,
                "lichess_username": str,
            },
        }
    },
    # Batch analysis endpoints
    r"^/api/batch-analyze/$": {
        "POST": {
            "required": ["game_ids"],
            "optional": ["depth", "lines"],
            "type_validation": {"game_ids": list, "depth": int, "lines": int},
            "value_validation": {
                "depth": lambda x: 1 <= x <= 30,
                "lines": lambda x: 1 <= x <= 5,
                "game_ids": lambda x: len(x) <= 50,
            },
        }
    },
    # Feedback endpoints
    r"^/api/games/\d+/feedback/$": {
        "POST": {
            "optional": ["focus_areas"],
            "type_validation": {"focus_areas": list},
            "value_validation": {
                "focus_areas": lambda x: all(
                    area in ["opening", "middlegame", "endgame", "tactics", "strategy", "time_management"] for area in x
                )
            },
        }
    },
    r"^/api/feedback/comparative/$": {
        "POST": {
            "required": ["game_ids"],
            "type_validation": {"game_ids": list},
            "value_validation": {"game_ids": lambda x: 2 <= len(x) <= 10},
        }
    },
}


# Define error response type
class ErrorDetail(TypedDict):
    field: str
    message: str
    detail: Optional[str]


# Default response for validation errors
DEFAULT_ERROR_RESPONSE: Dict[str, Any] = {"status": "error", "message": "Invalid request data", "errors": []}


class RequestIDMiddleware:
    """
    Middleware that adds a unique ID to each request.
    
    This ID is stored in both the request object and thread-local storage,
    allowing it to be accessed anywhere during the request/response cycle.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        
        # Store the request ID in the request object
        request.request_id = request_id
        
        # Also store in thread-local for access in other parts of the app
        set_request_id(request_id)
        
        # Add the request ID as response header
        response = self.get_response(request)
        if hasattr(response, "headers"):
            response.headers["X-Request-ID"] = request_id
        
        # Clean up thread-local storage after request is complete
        clear_request_id()
        
        return response


def get_method_schema(method_schemas: MethodSchema, method: str) -> Optional[SchemaOptions]:
    """Get schema options for a specific HTTP method safely."""
    if method == "POST" and "POST" in method_schemas:
        return method_schemas["POST"]
    elif method == "PUT" and "PUT" in method_schemas:
        return method_schemas["PUT"]
    elif method == "GET" and "GET" in method_schemas:
        return method_schemas["GET"]
    elif method == "DELETE" and "DELETE" in method_schemas:
        return method_schemas["DELETE"]
    return None


class RequestValidationMiddleware:
    """Middleware for validating API requests against defined schemas."""

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not self._should_validate(request):
            return self.get_response(request)

        # Validate the request
        is_valid, errors = self._validate_request(request)
        if not is_valid:
            logger.warning(f"Request validation failed: {errors}")
            return self._create_error_response(errors)

        # Request is valid, continue processing
        return self.get_response(request)

    def _should_validate(self, request: HttpRequest) -> bool:
        """Determine if the request should be validated."""
        # Only validate API requests
        if not request.path.startswith("/api/"):
            return False

        # Skip validation for GET, HEAD and OPTIONS requests
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return False

        # Check if there's a validation schema for this path
        for pattern in VALIDATION_SCHEMAS:
            if re.match(pattern, request.path):
                # Check if there's a schema for this method
                method_schemas = VALIDATION_SCHEMAS[pattern]
                if request.method in method_schemas:
                    return True

        return False

    def _validate_request(self, request: HttpRequest) -> Tuple[bool, List[ErrorDetail]]:
        """Validate request data against schema."""
        errors: List[ErrorDetail] = []

        try:
            # Parse JSON data if content-type is application/json
            if request.content_type == "application/json":
                if not request.body:
                    return True, []  # Empty body is fine for some requests
                try:
                    data = json.loads(request.body)
                except json.JSONDecodeError as e:
                    errors.append({"field": "body", "message": "Invalid JSON data", "detail": str(e)})
                    return False, errors
            else:
                # Use POST/PUT data as dictionary
                data = getattr(request, request.method, {})

            # Find matching schema
            for pattern in VALIDATION_SCHEMAS:
                if re.match(pattern, request.path):
                    method_schemas = VALIDATION_SCHEMAS[pattern]
                    if request.method in method_schemas:
                        schema = get_method_schema(method_schemas, request.method)
                        if not schema:
                            continue

                        # Validate required fields
                        for field in schema.get("required", []):
                            if field not in data:
                                errors.append({"field": field, "message": "Field is required", "detail": None})

                        # Validate field types
                        type_validation = schema.get("type_validation", {})
                        for field, field_type in type_validation.items():
                            if field in data and data[field] is not None:
                                try:
                                    # Use isinstance to check types, handling special cases
                                    is_valid_type = isinstance(data[field], field_type)
                                    
                                    if not is_valid_type:
                                        type_name = field_type.__name__ if hasattr(field_type, "__name__") else str(field_type)
                                        value_type = type(data[field]).__name__
                                        
                                        errors.append({
                                            "field": field,
                                            "message": f"Field must be of type {type_name}",
                                            "detail": f"Got {value_type}",
                                        })
                                except Exception as e:
                                    errors.append({
                                        "field": field, 
                                        "message": "Type validation error", 
                                        "detail": str(e)
                                    })

                        # Validate field values
                        value_validation = schema.get("value_validation", {})
                        for field, validator in value_validation.items():
                            if field in data and data[field] is not None:
                                try:
                                    if callable(validator) and not validator(data[field]):
                                        errors.append({
                                            "field": field, 
                                            "message": "Field failed validation",
                                            "detail": "Value did not meet the requirements"
                                        })
                                except Exception as e:
                                    errors.append({
                                        "field": field, 
                                        "message": "Validation error", 
                                        "detail": str(e)
                                    })

                        # Apply custom validators
                        custom_validators = schema.get("custom_validators", {})
                        for field, validator in custom_validators.items():
                            if field in data and data[field] is not None:
                                try:
                                    if callable(validator) and not validator(data[field]):
                                        errors.append({
                                            "field": field, 
                                            "message": "Invalid value",
                                            "detail": "Value did not meet custom validation rules"
                                        })
                                except Exception as e:
                                    errors.append({
                                        "field": field, 
                                        "message": "Value validation error", 
                                        "detail": str(e)
                                    })

                        # Break after first matching schema
                        break

            return len(errors) == 0, errors

        except Exception as e:
            logger.error(f"Error during request validation: {str(e)}", exc_info=True)
            errors.append({"field": "request", "message": "Internal validation error", "detail": str(e)})
            return False, errors

    def _create_error_response(self, errors: List[ErrorDetail]) -> HttpResponse:
        """Create an error response with validation errors."""
        response_data = DEFAULT_ERROR_RESPONSE.copy()
        response_data["errors"] = errors
        return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)


class RateLimitMiddleware:
    """Middleware for rate limiting API requests."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limits = getattr(settings, 'RATE_LIMITS', {})
        logger.debug(f"Rate limit middleware initialized with {len(self.rate_limits)} endpoint patterns")

    def __call__(self, request):
        """Process the request and apply rate limiting."""
        # Skip rate limiting for certain paths
        if not self._should_rate_limit(request.path):
            return self.get_response(request)

        # Get endpoint type and rate limit keys
        endpoint_type = self._get_endpoint_type(request.path)
        keys = self._get_rate_limit_keys(request, endpoint_type)

        # Check rate limits for each key
        for key_type, identifier in keys.items():
            if not self._check_rate_limit(key_type, identifier, endpoint_type):
                return self._rate_limit_response(request)

        # Rate limit not exceeded, process request
        response = self.get_response(request)
        
        # Add rate limit headers
        self._add_rate_limit_headers(response, keys, endpoint_type)
        
        return response

    def _should_rate_limit(self, path):
        """Determine if the request should be rate limited."""
        # Check for specific endpoint patterns
        for pattern in self.rate_limits.get('endpoint_patterns', {}).keys():
            if re.search(pattern, path):
                return True
        return False

    def _get_endpoint_type(self, path):
        """Determine the endpoint type based on the request path."""
        # Check for specific endpoint patterns
        for pattern, endpoint_type in self.rate_limits.get('endpoint_patterns', {}).items():
            if re.search(pattern, path):
                return endpoint_type
        
        # Default endpoint type
        return "DEFAULT"

    def _get_rate_limit_keys(self, request, endpoint_type):
        """Get the keys for rate limiting based on request."""
        keys = {}
        
        # Always add IP-based rate limiting
        keys["ip"] = request.META.get('REMOTE_ADDR', '127.0.0.1')
        
        # Add user-based rate limiting if authenticated
        if hasattr(request, 'user') and request.user.is_authenticated:
            keys["user"] = str(request.user.id)
        
        return keys

    def _get_rate_limit_config(self, endpoint_type):
        """Get rate limit configuration for endpoint type."""
        # Get configuration from settings
        config = self.rate_limits.get(endpoint_type, self.rate_limits.get('DEFAULT', {}))
        
        # Default values if not specified
        default_config = {
            'rate': '100/3600',  # 100 requests per hour
            'window': 3600,      # 1 hour window
            'backend': 'default'  # Default cache backend
        }
        
        # Update defaults with configured values
        default_config.update(config)
        
        return default_config

    def _check_rate_limit(self, key_type, identifier, endpoint_type):
        """Check if request exceeds rate limits."""
        config = self._get_rate_limit_config(endpoint_type)
        rate = config.get('rate', '100/3600')
        
        # Check if rate limited
        is_limited = limiter.is_rate_limited(key_type, identifier, rate)
        
        # Increment counter if not limited
        if not is_limited:
            limiter.increment(key_type, identifier, rate)
        
        return is_limited

    def _add_rate_limit_headers(self, response, keys, endpoint_type):
        """Add rate limit headers to response."""
        # Get the most restrictive limit (lowest remaining requests)
        min_remaining = None
        
        for key_type, identifier in keys.items():
            config = self._get_rate_limit_config(endpoint_type)
            rate = config.get('rate', '100/3600')
            
            # Get remaining requests
            remaining = limiter.get_remaining(key_type, identifier, rate)
            
            # Update minimum remaining
            if min_remaining is None or remaining < min_remaining:
                min_remaining = remaining
        
        # Add headers if minimum remaining was determined
        if min_remaining is not None:
            response['X-RateLimit-Remaining'] = str(min_remaining)
        
        return response

    def _rate_limit_response(self, request):
        """Create response for rate-limited requests."""
        return JsonResponse(
            {
                'status': 'error',
                'code': 'rate_limit_exceeded',
                'message': 'Rate limit exceeded. Please try again later.'
            },
            status=429
        )


class SecurityHeadersMiddleware:
    """Middleware to add security headers to all responses."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger(__name__)
        self.logger.info("SecurityHeadersMiddleware initialized")
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers to HTTP responses
        if hasattr(response, 'headers'):
            # Only add these headers if not already present
            if 'X-Content-Type-Options' not in response:
                response['X-Content-Type-Options'] = 'nosniff'
            if 'X-Frame-Options' not in response:
                response['X-Frame-Options'] = 'DENY'
                
            # Add Access-Control-Allow-Headers if it exists
            if 'Access-Control-Allow-Headers' in response:
                # Ensure Access-Control-Allow-Credentials is in the allowed headers
                allowed_headers = response['Access-Control-Allow-Headers'].split(', ')
                if 'access-control-allow-credentials' not in [h.lower() for h in allowed_headers]:
                    allowed_headers.append('access-control-allow-credentials')
                    response['Access-Control-Allow-Headers'] = ', '.join(allowed_headers)
            
        return response


class RequestIDFilter(logging.Filter):
    """
    A logging filter that adds the request_id to log records.

    This filter retrieves the request_id from thread_local storage
    and adds it to each log record. If no request_id is found,
    it uses a default value.
    """

    def filter(self, record):
        """
        Add request_id to the log record.

        Args:
            record: The log record to modify

        Returns:
            True to include the record in the log output
        """
        # Add request_id to the record
        if not hasattr(record, "request_id"):
            record.request_id = getattr(_thread_local, "request_id", "no_request_id")

        return True


class RequestFixMiddleware:
    """Middleware to fix common request issues, particularly with authentication headers."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger(__name__)
        self.logger.info("RequestFixMiddleware initialized")
    
    def __call__(self, request):
        # Check for authentication headers in different formats and normalize them
        auth_header = None
        original_auth = None
        
        # First check for standard HTTP_AUTHORIZATION
        if 'HTTP_AUTHORIZATION' in request.META:
            auth_header = request.META['HTTP_AUTHORIZATION']
            original_auth = "HTTP_AUTHORIZATION"
            self.logger.debug(f"Found HTTP_AUTHORIZATION header: {auth_header[:20]}..." if auth_header else "None")
        
        # Then check for Authorization in headers (common with JavaScript fetch)
        elif hasattr(request, 'headers') and 'Authorization' in request.headers:
            auth_header = request.headers.get('Authorization')
            original_auth = "headers.Authorization"
            self.logger.debug(f"Found Authorization in request.headers: {auth_header[:20]}..." if auth_header else "None")
            
        # Next check for Authorization in cookies (possible alternative auth method)
        elif 'Authorization' in request.COOKIES:
            auth_header = request.COOKIES.get('Authorization')
            original_auth = "COOKIES.Authorization"
            self.logger.debug(f"Found Authorization in cookies: {auth_header[:20]}..." if auth_header else "None")
            
        # Check for access_token in cookies (used with simplejwt cookie auth)
        elif 'access_token' in request.COOKIES:
            auth_header = f"Bearer {request.COOKIES.get('access_token')}"
            original_auth = "COOKIES.access_token"
            self.logger.debug(f"Found access_token in cookies, converted to Bearer format: {auth_header[:20]}..." if auth_header else "None")
            
        # Check if token is in the request GET parameters (not recommended for production but useful for debugging)
        elif 'token' in request.GET:
            auth_header = f"Bearer {request.GET.get('token')}"
            original_auth = "GET.token"
            self.logger.debug(f"Found token in GET parameters, converted to Bearer format: {auth_header[:20]}..." if auth_header else "None")
            
        # Check if access_token is in the request POST data (sometimes used in form submissions)
        elif 'access_token' in request.POST:
            auth_header = f"Bearer {request.POST.get('access_token')}"
            original_auth = "POST.access_token"
            self.logger.debug(f"Found access_token in POST data, converted to Bearer format: {auth_header[:20]}..." if auth_header else "None")
        
        # If an auth header was found in any form, normalize it and add to META
        if auth_header:
            # Ensure it has Bearer prefix if it's a JWT token
            if not auth_header.startswith('Bearer ') and ' ' not in auth_header:
                # Looks like a raw token without 'Bearer' prefix
                auth_header = f"Bearer {auth_header}"
                self.logger.debug(f"Added Bearer prefix to raw token: {auth_header[:20]}..." if auth_header else "None")
            
            # Set the authorization header in multiple places to ensure it's recognized
            request.META['HTTP_AUTHORIZATION'] = auth_header
            
            # For Django REST Framework specifically
            if hasattr(request, '_request'):
                request._request.META['HTTP_AUTHORIZATION'] = auth_header
                
            # Make sure it's also in the standard headers dict
            if hasattr(request, 'headers') and isinstance(request.headers, dict):
                request.headers['Authorization'] = auth_header
                
            # Fix Django 3.x vs Django 4.x compatibility issues
            # Django 4.x uses Authorization directly in some cases
            request.META['Authorization'] = auth_header
            
            # Log the token for debugging
            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header
            self.logger.debug(f"Auth normalized from {original_auth} - Token: {token[:15]}..." if token else "None")
            
            # Try to decode the token payload (without verification) for debugging
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                try:
                    import base64
                    import json
                    
                    # Get the payload part (second segment of JWT)
                    parts = token.split('.')
                    if len(parts) >= 2:
                        # Add padding if needed
                        payload = parts[1]
                        padding_needed = 4 - (len(payload) % 4)
                        if padding_needed < 4:
                            payload += '=' * padding_needed
                        
                        # Decode and log user_id
                        try:
                            decoded = base64.urlsafe_b64decode(payload).decode('utf-8')
                            payload_data = json.loads(decoded)
                            if 'user_id' in payload_data:
                                self.logger.debug(f"Token contains user_id: {payload_data['user_id']}")
                                
                                # For debugging only - load user info
                                try:
                                    from django.contrib.auth.models import User
                                    user = User.objects.get(id=payload_data['user_id'])
                                    self.logger.debug(f"Found user: {user.username}")
                                    
                                    # For JWT auth specifically, set user on request
                                    # This helps with authentication issues
                                    request.user = user
                                    request._force_auth_user = user
                                except Exception as user_e:
                                    self.logger.debug(f"Could not load user from token: {str(user_e)}")
                            elif 'id' in payload_data:
                                self.logger.debug(f"Token contains id: {payload_data['id']}")
                        except Exception as e:
                            self.logger.debug(f"Error decoding token payload: {str(e)}")
                except Exception as e:
                    self.logger.debug(f"Error processing token (for debugging only): {str(e)}")
        
        # Process the request
        response = self.get_response(request)
        
        # Add security headers to response
        if hasattr(response, 'headers'):
            # Only add these headers if not already present
            if 'X-Content-Type-Options' not in response:
                response['X-Content-Type-Options'] = 'nosniff'
            if 'X-Frame-Options' not in response:
                response['X-Frame-Options'] = 'DENY'
            
        return response


def get_request_id() -> str:
    """
    Get the current request ID from thread-local storage.
    If no request ID is set, returns a default value.
    
    Returns:
        str: The current request ID or a default value
    """
    return getattr(_thread_local, "request_id", "no_request_id")

def set_request_id(request_id: str) -> None:
    """
    Set the request ID in thread-local storage.
    
    Args:
        request_id: The request ID to store
    """
    setattr(_thread_local, "request_id", request_id)

def clear_request_id() -> None:
    """
    Clear the request ID from thread-local storage.
    """
    if hasattr(_thread_local, "request_id"):
        delattr(_thread_local, "request_id")


class CacheInvalidationMiddleware:
    """
    Middleware to handle cache invalidation.
    This is mainly for future extensions - most invalidation happens via signals.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response
