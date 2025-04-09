"""
Core views for ChessMate application.

This module provides core views and API endpoints for the ChessMate application,
including health checks, system status, and utility endpoints.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional, Union

from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from .cache import cache_get, cache_set
from .cache_invalidation import invalidates_cache, with_cache_tags
from .decorators import auth_csrf_exempt, validate_request
from .health_checks import (
    check_cache,
    check_celery,
    check_database,
    check_redis,
    check_storage,
    get_system_info,
    run_all_checks,
)
from .task_manager import TaskManager
from .tasks import health_check_task
from .error_handling import api_error_handler, create_error_response, create_success_response

logger = logging.getLogger(__name__)


@require_GET
@never_cache
def health_check(request: HttpRequest) -> HttpResponse:
    """
    Basic health check endpoint for load balancers and monitoring.

    Returns:
        HTTP 200 response with "ok" if the application is running
    """
    return HttpResponse("ok")


@require_GET
@never_cache
def readiness_check(request: HttpRequest) -> HttpResponse:
    """
    Readiness check that verifies core dependencies are available.

    Returns:
        HTTP 200 if all dependencies are ready, 503 otherwise
    """
    problems = []

    # Check database
    db_check = check_database()
    if db_check["status"] != "ok":
        problems.append(f"Database: {db_check['message']}")

    # If there are problems, return 503
    if problems:
        return HttpResponse(f"Not ready: {', '.join(problems)}", status=503, content_type="text/plain")

    return HttpResponse("ready")


@api_view(["GET"])
@never_cache
def detailed_health_check(request: HttpRequest) -> Response:
    """
    Detailed health check for monitoring and diagnostics.

    This endpoint performs comprehensive checks on all system components
    and returns detailed status information.

    Returns:
        JSON response with health status of all components
    """
    start_time = time.time()

    # Get health status for all components
    health_result = run_all_checks()

    # Include environment info
    is_debug = settings.DEBUG
    environment = "development" if is_debug else "production"

    # Add request duration
    duration_ms = int((time.time() - start_time) * 1000)

    # Build response
    response_data = {
        "status": health_result["status"],
        "environment": environment,
        "timestamp": datetime.utcnow().isoformat(),
        "request_duration_ms": duration_ms,
        "version": getattr(settings, "APP_VERSION", "unknown"),
        "checks": health_result["checks"],
        "system_info": get_system_info(),
    }

    # Determine HTTP status code
    http_status = 200
    if health_result["status"] == "critical":
        http_status = 503  # Service Unavailable
    elif health_result["status"] == "warning":
        http_status = 207  # Multi-Status

    return Response(response_data, status=http_status)


@api_view(["GET"])
@permission_classes([IsAdminUser])
@never_cache
def system_status(request: HttpRequest) -> Response:
    """
    Advanced system status endpoint for administrators.

    This endpoint provides detailed information about the system status,
    including performance metrics, resource usage, and operational metrics.

    Returns:
        JSON response with detailed system status
    """
    # Get all health checks
    health_result = run_all_checks()

    # Get task status
    task_manager = TaskManager()
    task_stats = task_manager.get_task_statistics()

    # Get cache stats if available
    try:
        cache_info = {}
        if hasattr(settings, "CACHES"):
            for cache_name, config in settings.CACHES.items():
                cache_type = config.get("BACKEND", "").split(".")[-1]
                cache_info[cache_name] = {
                    "type": cache_type,
                    "location": config.get("LOCATION", "unknown"),
                }

                # Try to get additional info for Redis
                if "Redis" in cache_type:
                    redis_check = check_redis()
                    if redis_check["status"] == "ok":
                        cache_info[cache_name].update(
                            {
                                "version": redis_check.get("version", "unknown"),
                                "clients": redis_check.get("clients", "unknown"),
                                "memory": redis_check.get("memory", "unknown"),
                            }
                        )
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        cache_info = {"error": str(e)}

    # System info
    system_info = get_system_info()

    # Response data
    response_data = {
        "status": health_result["status"],
        "environment": "development" if settings.DEBUG else "production",
        "timestamp": datetime.utcnow().isoformat(),
        "version": getattr(settings, "APP_VERSION", "unknown"),
        "health": health_result,
        "tasks": task_stats,
        "cache": cache_info,
        "system": system_info,
    }

    return Response(response_data)


@api_view(["POST"])
@permission_classes([IsAdminUser])
@invalidates_cache("global")
def clear_cache(request: HttpRequest) -> Response:
    """
    Clear the entire cache or specific cache keys.

    This endpoint allows administrators to clear the application cache,
    either entirely or for specific patterns/tags.

    Args:
        request: HTTP request object which may contain:
            - pattern: Optional cache key pattern to clear
            - tags: Optional list of cache tags to clear

    Returns:
        JSON response with the result of the operation
    """
    from .cache_invalidation import GLOBAL_TAG, cache_invalidator

    start_time = time.time()
    pattern = request.data.get("pattern")
    tags = request.data.get("tags")

    count = 0

    if tags:
        # If tags are provided, invalidate those specific tags
        if isinstance(tags, str):
            tags = [tags]
        count = cache_invalidator.invalidate_tags(tags)
    elif pattern:
        # If pattern is provided, invalidate that pattern
        from .cache import cache_delete_pattern

        count = cache_delete_pattern(pattern)
    else:
        # Otherwise, invalidate everything
        count = cache_invalidator.invalidate_tag(GLOBAL_TAG)

    duration_ms = int((time.time() - start_time) * 1000)

    return Response(
        {
            "status": "success",
            "message": f"Cache cleared successfully",
            "keys_cleared": count,
            "duration_ms": duration_ms,
        }
    )


@api_view(["POST"])
@permission_classes([IsAdminUser])
def run_health_check_task(request: HttpRequest) -> Response:
    """
    Trigger a health check task in Celery.

    This endpoint allows administrators to verify Celery is working
    by running a simple health check task.

    Returns:
        JSON response with the task result
    """
    try:
        # Run the health check task
        task = health_check_task.delay()

        # Try to get the result with a short timeout
        try:
            result = task.get(timeout=5)
            return Response(
                {
                    "status": "success",
                    "task_id": task.id,
                    "result": result,
                    "message": "Celery task completed successfully",
                }
            )
        except Exception as e:
            return Response(
                {"status": "pending", "task_id": task.id, "message": f"Task started but result not available: {str(e)}"}
            )
    except Exception as e:
        logger.error(f"Error running health check task: {str(e)}")
        return Response({"status": "error", "message": f"Failed to run Celery task: {str(e)}"}, status=500)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@validate_request(required_get_params=["task_id"])
def check_task_status(request: HttpRequest) -> Response:
    """
    Check the status of a background task.

    Args:
        request: HTTP request with task_id parameter

    Returns:
        JSON response with task status
    """
    task_id = request.GET.get("task_id")

    task_manager = TaskManager()
    status = task_manager.get_task_status(task_id)

    if not status:
        return Response({"status": "error", "message": f"Task {task_id} not found"}, status=404)

    return Response(status)


@with_cache_tags("system_info")
@api_view(["GET"])
@never_cache
def app_info(request: HttpRequest) -> Response:
    """
    Get basic application information.

    This endpoint provides general information about the application,
    including version, environment, and runtime configuration.

    Returns:
        JSON response with application information
    """
    # Use cache to avoid repeated calculations
    cache_key = "app_info"
    cached_info = cache_get(cache_key)

    if cached_info:
        return Response(cached_info)

    # Basic app info
    info = {
        "name": "ChessMate",
        "version": getattr(settings, "APP_VERSION", "unknown"),
        "environment": "development" if settings.DEBUG else "production",
        "api_version": "v1",
        "features": {
            "analysis": True,
            "feedback": True,
            "training": True,
            "multiplayer": getattr(settings, "ENABLE_MULTIPLAYER", False),
            "tournaments": getattr(settings, "ENABLE_TOURNAMENTS", False),
        },
        "endpoints": {
            "health": "/api/health/",
            "info": "/api/info/",
            "docs": "/api/docs/",
        },
    }

    # Cache the result
    cache_set(cache_key, info, timeout=3600)  # 1 hour

    return Response(info)


@api_view(["GET"])
@api_error_handler
def get_basic_profile(request):
    """
    Get basic profile information for the authenticated user.
    This is a simplified endpoint that avoids complex model relations.
    """
    try:
        # Check if user is authenticated
        if not request.user.is_authenticated:
            logger.warning("Unauthenticated user tried to access basic profile")
            return Response(
                {"status": "error", "message": "Authentication credentials were not provided"},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        # Create response with user data
        basic_data = {
            "user": {
                "id": request.user.id,
                "username": request.user.username,
                "email": request.user.email,
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "date_joined": request.user.date_joined.isoformat() if hasattr(request.user, 'date_joined') else None,
                "is_active": request.user.is_active
            },
            "profile": {"credits": 0}  # Default empty profile
        }
        
        # Try to access profile via the relation if it exists
        if hasattr(request.user, 'profile'):
            try:
                profile = request.user.profile
                profile_data = {
                    "credits": getattr(profile, 'credits', 0),
                    "chess_com_username": getattr(profile, 'chess_com_username', ""),
                    "lichess_username": getattr(profile, 'lichess_username', ""),
                    "email_verified": getattr(profile, 'email_verified', False),
                }
                basic_data["profile"] = profile_data
            except Exception as e:
                logger.error(f"Error accessing profile attributes: {str(e)}")
        
        return Response({"status": "success", "data": basic_data}, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in get_basic_profile: {str(e)}", exc_info=True)
        # Return a minimal response with error handling
        return Response(
            {
                "status": "success", 
                "data": {
                    "user": {
                        "username": getattr(request.user, "username", "unknown"),
                        "email": getattr(request.user, "email", "unknown")
                    },
                    "profile": {"credits": 0}
                }
            },
            status=status.HTTP_200_OK
        )
