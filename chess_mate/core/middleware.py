"""
Middleware for validating API requests.
This middleware validates incoming requests against a schema, ensuring they contain
required fields and have proper data formats before they reach the view functions.
"""

import json
import re
import logging
import uuid
import time
from typing import Any, Callable, Dict, List, Optional, Union, Tuple
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import resolve
from rest_framework import status
from rest_framework.request import Request
from rest_framework.exceptions import ValidationError
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from .rate_limiter import RateLimiter
from .error_handling import create_error_response

logger = logging.getLogger(__name__)

# Validation schemas defined as a mapping of URL patterns to required fields and their types
VALIDATION_SCHEMAS = {
    # Auth endpoints
    r'^/api/register/$': {
        'POST': {
            'required': ['email', 'password', 'username'],
            'optional': ['first_name', 'last_name'],
            'type_validation': {
                'email': str,
                'password': str,
                'username': str,
                'first_name': str,
                'last_name': str
            },
            'custom_validators': {
                'email': lambda x: re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', x),
                'password': lambda x: len(x) >= 8,
            }
        }
    },
    r'^/api/login/$': {
        'POST': {
            'required': ['email', 'password'],
            'type_validation': {
                'email': str,
                'password': str
            }
        }
    },
    
    # Game endpoints
    r'^/api/games/\d+/analyze/$': {
        'POST': {
            'optional': ['depth', 'lines'],
            'type_validation': {
                'depth': int,
                'lines': int
            },
            'value_validation': {
                'depth': lambda x: 1 <= x <= 30,
                'lines': lambda x: 1 <= x <= 5
            }
        }
    },
    r'^/api/games/fetch/$': {
        'POST': {
            'required': ['platform', 'username'],
            'optional': ['time_period', 'limit'],
            'type_validation': {
                'platform': str,
                'username': str,
                'time_period': str,
                'limit': int
            },
            'value_validation': {
                'limit': lambda x: 1 <= x <= 100,
                'platform': lambda x: x in ['chess.com', 'lichess']
            }
        }
    },
    
    # Profile endpoints
    r'^/api/profile/update/$': {
        'PUT': {
            'optional': ['username', 'first_name', 'last_name', 'bio', 'chess_com_username', 'lichess_username'],
            'type_validation': {
                'username': str,
                'first_name': str,
                'last_name': str,
                'bio': str,
                'chess_com_username': str,
                'lichess_username': str
            }
        }
    },
    
    # Batch analysis endpoints
    r'^/api/batch-analyze/$': {
        'POST': {
            'required': ['game_ids'],
            'optional': ['depth', 'lines'],
            'type_validation': {
                'game_ids': list,
                'depth': int,
                'lines': int
            },
            'value_validation': {
                'depth': lambda x: 1 <= x <= 30,
                'lines': lambda x: 1 <= x <= 5,
                'game_ids': lambda x: len(x) <= 50
            }
        }
    },
    
    # Feedback endpoints
    r'^/api/games/\d+/feedback/$': {
        'POST': {
            'optional': ['focus_areas'],
            'type_validation': {
                'focus_areas': list
            },
            'value_validation': {
                'focus_areas': lambda x: all(area in ['opening', 'middlegame', 'endgame', 'tactics', 'strategy', 'time_management'] for area in x)
            }
        }
    },
    r'^/api/feedback/comparative/$': {
        'POST': {
            'required': ['game_ids'],
            'type_validation': {
                'game_ids': list
            },
            'value_validation': {
                'game_ids': lambda x: 2 <= len(x) <= 10
            }
        }
    }
}

# Default response for validation errors
DEFAULT_ERROR_RESPONSE = {
    'status': 'error',
    'message': 'Invalid request data',
    'errors': []
}


class RequestIDMiddleware:
    """Middleware that adds a unique request ID to each request for traceability."""

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        
        # Add request ID to the request object
        request.request_id = request_id
        
        # Add request ID to thread-local storage for logger access
        # This requires thread_local from threading module if needed
        
        # Process the request
        response = self.get_response(request)
        
        # Add request ID to response headers
        response['X-Request-ID'] = request_id
        
        return response


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
            logger.warning(
                f"Request validation failed: {request.method} {request.path} - {errors}",
                extra={"request_id": getattr(request, "request_id", None)}
            )
            return self._create_error_response(errors)

        # Request is valid, continue processing
        return self.get_response(request)

    def _should_validate(self, request: HttpRequest) -> bool:
        """Determine if the request should be validated."""
        # Only validate API requests
        if not request.path.startswith('/api/'):
            return False

        # Skip validation for GET, HEAD and OPTIONS requests
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return False

        # Check if there's a validation schema for this path
        for pattern in VALIDATION_SCHEMAS:
            if re.match(pattern, request.path):
                # Check if there's a schema for this method
                method_schemas = VALIDATION_SCHEMAS[pattern]
                if request.method in method_schemas:
                    return True

        return False

    def _validate_request(self, request: HttpRequest) -> tuple:
        """Validate the request against the defined schema."""
        # Parse request body
        try:
            if request.body:
                body = json.loads(request.body)
            else:
                body = {}
        except json.JSONDecodeError:
            return False, [{'field': 'body', 'message': 'Invalid JSON format'}]

        # Find matching schema
        schema = None
        for pattern in VALIDATION_SCHEMAS:
            if re.match(pattern, request.path):
                method_schemas = VALIDATION_SCHEMAS[pattern]
                if request.method in method_schemas:
                    schema = method_schemas[request.method]
                    break

        if not schema:
            # No schema found, assume valid
            return True, []

        errors = []

        # Check required fields
        if 'required' in schema:
            for field in schema['required']:
                if field not in body:
                    errors.append({
                        'field': field,
                        'message': f"Field '{field}' is required"
                    })

        # Validate field types
        if 'type_validation' in schema:
            for field, expected_type in schema['type_validation'].items():
                if field in body and body[field] is not None:
                    # Check if field value is of expected type
                    if expected_type == list:
                        if not isinstance(body[field], list):
                            errors.append({
                                'field': field,
                                'message': f"Field '{field}' must be a list"
                            })
                    elif expected_type == bool:
                        if not isinstance(body[field], bool):
                            # Convert string representations to bool if needed
                            if isinstance(body[field], str):
                                if body[field].lower() in ('true', 'false'):
                                    body[field] = body[field].lower() == 'true'
                                else:
                                    errors.append({
                                        'field': field,
                                        'message': f"Field '{field}' must be a boolean"
                                    })
                            else:
                                errors.append({
                                    'field': field,
                                    'message': f"Field '{field}' must be a boolean"
                                })
                    elif expected_type == int:
                        if not isinstance(body[field], int):
                            # Try to convert string to int if needed
                            if isinstance(body[field], str) and body[field].isdigit():
                                body[field] = int(body[field])
                            else:
                                errors.append({
                                    'field': field,
                                    'message': f"Field '{field}' must be an integer"
                                })
                    elif not isinstance(body[field], expected_type):
                        errors.append({
                            'field': field,
                            'message': f"Field '{field}' must be of type {expected_type.__name__}"
                        })

        # Validate field values
        if 'value_validation' in schema:
            for field, validator in schema['value_validation'].items():
                if field in body and body[field] is not None:
                    if not validator(body[field]):
                        errors.append({
                            'field': field,
                            'message': f"Field '{field}' has an invalid value"
                        })

        # Run custom validators
        if 'custom_validators' in schema:
            for field, validator in schema['custom_validators'].items():
                if field in body and body[field] is not None:
                    if not validator(body[field]):
                        errors.append({
                            'field': field,
                            'message': f"Field '{field}' failed custom validation"
                        })

        # Update request with validated data
        if not errors:
            # For DRF requests, we need to update _request.data
            if hasattr(request, '_request'):
                request._request.POST = body
            else:
                request.POST = body

        return len(errors) == 0, errors

    def _create_error_response(self, errors: List[Dict[str, str]]) -> JsonResponse:
        """Create an error response for validation errors."""
        response_data = DEFAULT_ERROR_RESPONSE.copy()
        response_data['errors'] = errors
        return JsonResponse(
            response_data,
            status=status.HTTP_400_BAD_REQUEST
        )


class RateLimitMiddleware:
    """
    Middleware that applies rate limiting to API requests based on endpoint patterns.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        try:
            self.rate_limiter = RateLimiter()
            self.endpoint_patterns = getattr(settings, 'RATE_LIMIT_PATTERNS', {})
            logger.info("Rate limit middleware initialized")
        except Exception as e:
            logger.error(f"Failed to initialize rate limit middleware: {str(e)}")
            self.rate_limiter = None
            
    def _get_endpoint_type(self, path: str) -> str:
        """
        Determine the endpoint type based on the request path.
        Returns 'DEFAULT' if no matching pattern is found.
        """
        for endpoint_type, patterns in self.endpoint_patterns.items():
            for pattern in patterns:
                if re.match(pattern, path):
                    return endpoint_type
        return 'DEFAULT'
            
    def __call__(self, request):
        if not self.rate_limiter:
            return self.get_response(request)
            
        # Skip rate limiting for non-API requests
        if not request.path.startswith('/api/'):
            return self.get_response(request)
            
        # Skip rate limiting for excluded paths
        excluded_paths = getattr(settings, 'RATE_LIMIT_EXCLUDED_PATHS', [])
        for path in excluded_paths:
            if re.match(path, request.path):
                return self.get_response(request)
        
        # Determine client identifier (IP or user ID)
        if request.user.is_authenticated:
            client_id = f"user:{request.user.id}"
        else:
            client_id = f"ip:{request.META.get('REMOTE_ADDR', 'unknown')}"
            
        # Determine endpoint type and create rate limit key
        endpoint_type = self._get_endpoint_type(request.path)
        rate_limit_key = f"rate_limit:{client_id}:{endpoint_type}"
        
        # Check if rate limited
        if self.rate_limiter.is_rate_limited(rate_limit_key, endpoint_type):
            remaining_time = self.rate_limiter.get_reset_time(rate_limit_key, endpoint_type)
            logger.warning(f"Rate limit exceeded for {client_id} on endpoint {request.path}")
            
            return create_error_response(
                error_type="rate_limit_exceeded",
                message=f"Rate limit exceeded. Please try again in {remaining_time} seconds.",
                status_code=429,
                details={
                    "reset_time": remaining_time,
                    "endpoint_type": endpoint_type
                }
            )
            
        # Process the request
        response = self.get_response(request)
        
        # Add rate limit headers to response
        try:
            config = self.rate_limiter.get_rate_limit_config(endpoint_type)
            remaining = self.rate_limiter.get_remaining_requests(rate_limit_key, endpoint_type)
            reset_time = self.rate_limiter.get_reset_time(rate_limit_key, endpoint_type)
            
            response['X-RateLimit-Limit'] = str(config['MAX_REQUESTS'])
            response['X-RateLimit-Remaining'] = str(remaining)
            response['X-RateLimit-Reset'] = str(reset_time)
        except Exception as e:
            logger.error(f"Error adding rate limit headers: {str(e)}")
            
        return response
