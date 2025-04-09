"""
Utility views for the ChessMate application.
Including debug, health check, CSRF, and other auxiliary endpoints.
"""

import json

# Standard library imports
import logging
import os
import sys
import uuid
from typing import Any, Dict

# Django imports
from django.conf import settings
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from rest_framework import status

# Third-party imports
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .cache import cache_stats

# Local application imports
from .error_handling import api_error_handler, create_success_response

# Configure logging
logger = logging.getLogger(__name__)


@ensure_csrf_cookie
@api_view(["GET"])
def csrf(request):
    """
    Get a CSRF token for the client.
    """
    return Response({"detail": "CSRF cookie set"})


@api_view(["GET"])
def health_check(request):
    """
    Health check endpoint for monitoring and load balancers.

    Checks the health of:
    - Application (basic functionality)
    - Database connection
    - Redis connection (if configured)
    - Celery task queue (if configured)
    """
    health_data = {
        "status": "healthy",
        "timestamp": timezone.now().isoformat(),
        "version": getattr(settings, "VERSION", "1.0.0"),
        "environment": getattr(settings, "ENVIRONMENT", "development"),
        "components": {},
    }

    overall_status = True

    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        health_data["components"]["database"] = {"status": "healthy", "message": "Connected successfully"}
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        health_data["components"]["database"] = {"status": "unhealthy", "message": f"Connection failed: {str(e)}"}
        overall_status = False

    # Check Redis connection if configured
    if hasattr(settings, "USE_REDIS") and settings.USE_REDIS:
        try:
            import redis
            from django.core.cache import caches

            redis_cache = caches.get("redis")
            if redis_cache:
                # Try to perform a basic cache operation
                test_key = f"health_check_{uuid.uuid4()}"
                redis_cache.set(test_key, "test", 10)
                result = redis_cache.get(test_key)
                redis_cache.delete(test_key)

                if result == "test":
                    health_data["components"]["redis"] = {"status": "healthy", "message": "Connected successfully"}
                else:
                    raise Exception("Cache test failed - value mismatch")
            else:
                raise Exception("Redis cache not configured properly")

        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            health_data["components"]["redis"] = {"status": "unhealthy", "message": f"Connection failed: {str(e)}"}
            overall_status = False

    # Check Celery task queue if configured
    if "celery" in settings.INSTALLED_APPS or hasattr(settings, "CELERY_BROKER_URL"):
        try:
            from core.tasks import health_check as celery_health_check

            # Run a simple task synchronously for health checking
            task_result = celery_health_check.apply()
            celery_data = task_result.get(timeout=5)  # 5 second timeout

            if celery_data and celery_data.get("status") == "healthy":
                health_data["components"]["celery"] = {
                    "status": "healthy",
                    "message": "Task executed successfully",
                    "worker_timestamp": celery_data.get("timestamp"),
                }
            else:
                raise Exception("Task execution failed or returned unexpected result")

        except Exception as e:
            logger.error(f"Celery health check failed: {str(e)}")
            health_data["components"]["celery"] = {"status": "unhealthy", "message": f"Task execution failed: {str(e)}"}
            overall_status = False

    # Update overall status
    if not overall_status:
        health_data["status"] = "degraded"

    status_code = status.HTTP_200_OK if overall_status else status.HTTP_503_SERVICE_UNAVAILABLE
    return JsonResponse(health_data, status=status_code)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def debug_request(request):
    """
    Debug endpoint to show request information.
    Only available in debug mode.
    """
    if not settings.DEBUG:
        return Response({"error": "Debug endpoint only available in DEBUG mode"}, status=status.HTTP_403_FORBIDDEN)

    headers = {}
    for header, value in request.headers.items():
        headers[header] = value

    debug_info = {
        "method": request.method,
        "path": request.path,
        "user": str(request.user),
        "auth": str(request.auth),
        "headers": headers,
        "GET": dict(request.GET),
        "POST": dict(request.POST),
    }

    # Add request body if it's JSON
    if request.content_type == "application/json":
        try:
            debug_info["body"] = json.loads(request.body)
        except json.JSONDecodeError:
            debug_info["body"] = "Invalid JSON"

    return Response(debug_info)


@api_view(["GET"])
@permission_classes([AllowAny])
def api_info(request):
    """
    Get information about the API, endpoints, and versions.
    """
    info = {
        "name": "ChessMate API",
        "version": getattr(settings, "API_VERSION", "1.0.0"),
        "description": "API for chess game analysis and feedback",
        "endpoints": {
            "auth": [
                {"path": "/api/register/", "methods": ["POST"], "description": "Register new user"},
                {"path": "/api/login/", "methods": ["POST"], "description": "Login user"},
                {"path": "/api/logout/", "methods": ["POST"], "description": "Logout user"},
                {"path": "/api/token/refresh/", "methods": ["POST"], "description": "Refresh JWT token"},
                {"path": "/api/reset-password/", "methods": ["POST"], "description": "Request password reset"},
                {"path": "/api/reset-password/confirm/", "methods": ["POST"], "description": "Confirm password reset"},
                {"path": "/api/verify-email/<token>/", "methods": ["GET"], "description": "Verify email"},
            ],
            "user": [
                {"path": "/api/profile/", "methods": ["GET", "PATCH"], "description": "Get or update user profile"},
                {"path": "/api/statistics/", "methods": ["GET"], "description": "Get user statistics"},
            ],
            "games": [
                {"path": "/api/games/", "methods": ["GET"], "description": "Get user's games"},
                {"path": "/api/games/fetch/", "methods": ["POST"], "description": "Fetch games from chess platforms"},
                {"path": "/api/games/<game_id>/analyze/", "methods": ["POST"], "description": "Analyze a game"},
                {"path": "/api/games/<game_id>/analysis/", "methods": ["GET"], "description": "Get game analysis"},
                {"path": "/api/batch-analyze/", "methods": ["POST"], "description": "Analyze multiple games"},
            ],
            "feedback": [
                {
                    "path": "/api/games/<game_id>/feedback/",
                    "methods": ["POST", "GET"],
                    "description": "Generate or get AI feedback",
                },
                {
                    "path": "/api/feedback/comparative/",
                    "methods": ["POST"],
                    "description": "Generate comparative feedback",
                },
                {
                    "path": "/api/feedback/improvement/",
                    "methods": ["GET"],
                    "description": "Get improvement suggestions",
                },
            ],
            "dashboard": [
                {"path": "/api/dashboard/", "methods": ["GET"], "description": "Get dashboard data"},
                {"path": "/api/dashboard/refresh/", "methods": ["POST"], "description": "Refresh dashboard data"},
                {
                    "path": "/api/dashboard/performance-trend/",
                    "methods": ["GET"],
                    "description": "Get performance trend data",
                },
                {"path": "/api/dashboard/mistake-analysis/", "methods": ["GET"], "description": "Get mistake analysis"},
            ],
            "system": [
                {"path": "/api/health/", "methods": ["GET"], "description": "Health check"},
                {"path": "/api/csrf/", "methods": ["GET"], "description": "Get CSRF token"},
                {"path": "/api/info/", "methods": ["GET"], "description": "API information"},
            ],
        },
        "documentation": "/api/docs/",
    }

    return Response(info)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_system_constants(request):
    """
    Get system constants and configuration values for the client.
    """
    constants = {
        "MAX_BATCH_SIZE": getattr(settings, "MAX_BATCH_SIZE", 10),
        "RATE_LIMITS": {
            "FETCH": getattr(settings, "RATE_LIMIT_FETCH", 10),
            "ANALYZE": getattr(settings, "RATE_LIMIT_ANALYZE", 30),
        },
        "DEFAULT_CREDITS": getattr(settings, "DEFAULT_CREDITS", 5),
        "FEEDBACK_COST": 2,
        "COMPARATIVE_FEEDBACK_COST": 3,
        "IMPROVEMENT_SUGGESTIONS_COST": 5,
        "GAME_ANALYSIS_COST": 1,
        "SUPPORTED_PLATFORMS": ["chess.com", "lichess"],
        "SUPPORTED_GAME_TYPES": ["blitz", "rapid", "classical", "bullet"],
        "MAX_GAMES_FETCH": 50,
    }

    return Response(constants)


@csrf_exempt
@api_view(["GET"])
def check_version(request):
    """
    Check if client version is up to date.
    """
    client_version = request.GET.get("version", "0.0.0")
    latest_version = getattr(settings, "CLIENT_VERSION", "1.0.0")

    # Parse version strings
    client_parts = [int(x) for x in client_version.split(".")]
    latest_parts = [int(x) for x in latest_version.split(".")]

    # Fill with zeros if lengths don't match
    while len(client_parts) < len(latest_parts):
        client_parts.append(0)
    while len(latest_parts) < len(client_parts):
        latest_parts.append(0)

    # Compare versions
    needs_update = False
    for i in range(len(latest_parts)):
        if latest_parts[i] > client_parts[i]:
            needs_update = True
            break
        elif client_parts[i] > latest_parts[i]:
            # Client is somehow ahead (development build?)
            break

    return Response(
        {
            "client_version": client_version,
            "latest_version": latest_version,
            "needs_update": needs_update,
            "update_url": getattr(settings, "CLIENT_UPDATE_URL", None) if needs_update else None,
            "force_update": getattr(settings, "FORCE_CLIENT_UPDATE", False) and needs_update,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_server_time(request):
    """
    Get the current server time.
    Useful for debugging time-related issues.
    """
    return Response({"server_time": timezone.now().isoformat(), "timezone": str(timezone.get_current_timezone())})


@api_view(["GET"])
@api_error_handler
def version_check(request):
    """
    Return the current API version.
    """
    return create_success_response(
        {"version": settings.VERSION, "release_date": settings.RELEASE_DATE, "environment": settings.ENVIRONMENT}
    )


@api_view(["GET"])
def api_documentation(request):
    """
    Serve API documentation using Swagger UI.
    """
    return render(
        request,
        "api/swagger.html",
        {"title": "ChessMate API Documentation", "openapi_url": settings.STATIC_URL + "openapi.json"},
    )


@api_view(["GET"])
def openapi_spec(request, format="json"):
    """
    Serve the OpenAPI specification in JSON or YAML format.
    """
    if format not in ["json", "yaml"]:
        return HttpResponse(status=404)

    static_dir = os.path.join(settings.BASE_DIR, "static")
    file_path = os.path.join(static_dir, f"openapi.{format}")

    try:
        with open(file_path, "r") as f:
            content = f.read()

        content_type = "application/json" if format == "json" else "application/yaml"
        return HttpResponse(content, content_type=content_type)
    except FileNotFoundError:
        logger.error(f"OpenAPI specification file not found: {file_path}")
        return HttpResponse("OpenAPI specification not found", status=404)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def cache_stats_view(request):
    """
    Endpoint to retrieve cache statistics for monitoring.
    Only accessible to admin users.
    """
    stats_data = cache_stats()
    return JsonResponse(stats_data)
