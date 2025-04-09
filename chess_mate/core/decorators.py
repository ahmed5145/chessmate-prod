import functools
import json
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, Union, cast

from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import rotate_token
from django.views.decorators.csrf import csrf_exempt
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)

# Type variable for the decorated function
F = TypeVar("F", bound=Callable[..., Any])


def rate_limit(endpoint_type: str = "DEFAULT") -> Callable[[F], F]:
    """
    Decorator to apply rate limiting to a view.
    This is a simplified decorator that delegates to the RateLimitMiddleware for actual enforcement.

    Args:
        endpoint_type: Type of endpoint to limit (DEFAULT, ANALYSIS, GAMES, etc.)

    Returns:
        The decorated function
    """

    def decorator(view_func: F) -> F:
        @wraps(view_func)
        def wrapped_view(request: Any, *args: Any, **kwargs: Any) -> Any:
            # Store the endpoint_type for the RateLimitMiddleware
            request.rate_limit_endpoint_type = endpoint_type  # type: ignore

            # Proceed with the view
            return view_func(request, *args, **kwargs)

        return cast(F, wrapped_view)

    return decorator


def auth_csrf_exempt(view_func):
    """
    Enhanced CSRF exempt decorator that still maintains CSRF protection for authenticated users.
    This is a more secure version of Django's csrf_exempt that only exempts unauthenticated requests.

    For authenticated users, full CSRF protection is enforced.
    For anonymous users, CSRF is exempted to support API clients that don't have access to the CSRF token.
    Always exempts OPTIONS requests for CORS preflight compatibility.
    Also exempts requests with Bearer token authentication, used for JWT auth.
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # If this is an OPTIONS request (CORS preflight), exempt CSRF
        if request.method == "OPTIONS":
            csrf_exempt_view = csrf_exempt(view_func)
            return csrf_exempt_view(request, *args, **kwargs)
            
        # Check for Bearer token auth - exempt CSRF for API clients using JWT
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header and auth_header.startswith('Bearer '):
            csrf_exempt_view = csrf_exempt(view_func)
            return csrf_exempt_view(request, *args, **kwargs)
            
        # If the user is authenticated with session (not API), enforce CSRF
        if hasattr(request, "user") and request.user.is_authenticated:
            # Use the view function directly, without CSRF exemption
            return view_func(request, *args, **kwargs)

        # For anonymous users, apply CSRF exemption
        csrf_exempt_view = csrf_exempt(view_func)
        return csrf_exempt_view(request, *args, **kwargs)

    return wrapped_view


def track_request_time(view_func: F) -> F:
    """
    Decorator to track request time and log it.

    Args:
        view_func: The view function to decorate

    Returns:
        The decorated function
    """

    @wraps(view_func)
    def wrapped_view(request: Any, *args: Any, **kwargs: Any) -> Any:
        start_time = time.time()

        # Call the view function
        response = view_func(request, *args, **kwargs)

        # Calculate and log request time
        request_time = time.time() - start_time
        logger.info(
            f"Request time: {request_time:.4f}s for {request.method} {request.path}",
            extra={
                "request_time": request_time,
                "request_method": request.method,
                "request_path": request.path,
                "request_id": getattr(request, "request_id", None),
            },
        )

        # Add request time to response headers
        if hasattr(response, "headers"):
            response["X-Request-Time"] = f"{request_time:.4f}s"

        return response

    return cast(F, wrapped_view)


def validate_request(
    required_fields: Optional[List[str]] = None,
    optional_fields: Optional[List[str]] = None,
    required_get_params: Optional[List[str]] = None,
    optional_get_params: Optional[List[str]] = None,
) -> Callable[[F], F]:
    """
    Decorator to validate request fields.

    Args:
        required_fields: List of required fields in request body (for POST/PUT)
        optional_fields: List of optional fields in request body (for POST/PUT)
        required_get_params: List of required GET parameters (for GET)
        optional_get_params: List of optional GET parameters (for GET)

    Returns:
        The decorated function
    """

    def decorator(view_func: F) -> F:
        @wraps(view_func)
        def wrapped_view(request: Any, *args: Any, **kwargs: Any) -> Any:
            errors = []

            # Check if it's a GET request
            if request.method == "GET" and required_get_params:
                for param in required_get_params:
                    if not request.GET.get(param):
                        errors.append({"field": param, "message": f"Required GET parameter missing: {param}"})

            # Check if it's a POST/PUT request with JSON body
            elif request.method in ["POST", "PUT", "PATCH"] and required_fields:
                # Try to parse JSON body
                try:
                    if request.body:
                        data = json.loads(request.body)

                        # Validate required fields
                        for field in required_fields:
                            if field not in data:
                                errors.append({"field": field, "message": f"Required field missing: {field}"})
                except json.JSONDecodeError:
                    errors.append({"field": "body", "message": "Invalid JSON format in request body"})

            # If there are validation errors, return error response
            if errors:
                logger.warning(f"Validation failed for {request.path}: {errors}")
                return JsonResponse({"status": "error", "message": "Validation failed", "errors": errors}, status=400)

            # No validation errors, proceed with the view
            return view_func(request, *args, **kwargs)

        return cast(F, wrapped_view)

    return decorator


def api_login_required(view_func: F) -> F:
    """
    Decorator for API views that checks that the user is logged in via JWT.
    More suitable for REST API views than the standard login_required.
    """
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Try to authenticate with JWT
        try:
            jwt_auth = JWTAuthentication()
            user_auth_tuple = jwt_auth.authenticate(request)
            if user_auth_tuple:
                user, _ = user_auth_tuple
                request.user = user
                # User is authenticated, proceed with the view
                return view_func(request, *args, **kwargs)
            
            # No valid JWT token found, return 401
            return JsonResponse(
                {"status": "error", "message": "Authentication required"}, 
                status=401
            )
            
        except AuthenticationFailed:
            # Invalid token
            return JsonResponse(
                {"status": "error", "message": "Invalid or expired token"}, 
                status=401
            )
        except Exception as e:
            logger.error(f"Error in api_login_required: {str(e)}", exc_info=True)
            return JsonResponse(
                {"status": "error", "message": "Authentication error"}, 
                status=401
            )
    
    return cast(F, wrapped_view)
