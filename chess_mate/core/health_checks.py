"""
Health check utilities for monitoring system status.

This module provides functions to check the health of various components:
- Database connectivity
- Cache responsiveness
- Redis availability
- Celery operation
- Storage access
- External service reachability
- DNS resolution

It also includes Django views for exposing health information through HTTP endpoints.
"""

import json
import logging
import os
import platform
import socket
import sys
import time
from datetime import datetime
from importlib import import_module
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import requests
from django.conf import settings
from django.core.cache import cache
from django.db import connections
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

# Import Redis connection function
from .cache import get_redis_connection

logger = logging.getLogger(__name__)

# Health check types
DB_CHECK = "database"
CACHE_CHECK = "cache"
REDIS_CHECK = "redis"
CELERY_CHECK = "celery"
STORAGE_CHECK = "storage"
EXTERNAL_SERVICE_CHECK = "external_service"

# Health check status
STATUS_OK = "ok"
STATUS_WARNING = "warning"
STATUS_CRITICAL = "critical"
STATUS_UNKNOWN = "unknown"

# Threshold for response times (in seconds)
RESPONSE_TIME_WARNING = 0.5
RESPONSE_TIME_CRITICAL = 2.0


def check_database(database: str = "default") -> Dict[str, Any]:
    """
    Check if the database is reachable and responsive.

    Args:
        database: Name of the database connection to check

    Returns:
        Dict with status information
    """
    start_time = time.time()
    status = STATUS_UNKNOWN
    message = ""

    try:
        # Get a cursor and execute a simple query
        connection = connections[database]
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        row = cursor.fetchone()

        if row and row[0] == 1:
            status = STATUS_OK
            message = "Database is operational"
        else:
            status = STATUS_CRITICAL
            message = "Database returned unexpected result"

    except Exception as e:
        status = STATUS_CRITICAL
        message = f"Database error: {str(e)}"
        logger.error(f"Database health check failed: {str(e)}")

    response_time = time.time() - start_time

    # Adjust status based on response time
    if status == STATUS_OK and response_time > RESPONSE_TIME_CRITICAL:
        status = STATUS_WARNING
        message = f"Database is slow (took {response_time:.2f}s)"

    return {
        "component": DB_CHECK,
        "status": status,
        "message": message,
        "response_time": round(response_time, 3),
        "timestamp": timezone.now().isoformat(),
    }


def check_cache(cache_name: str = "default") -> Dict[str, Any]:
    """
    Check if the cache is reachable and responsive.

    Args:
        cache_name: Name of the cache to check

    Returns:
        Dict with status information
    """
    start_time = time.time()
    status = STATUS_UNKNOWN
    message = ""

    try:
        # Set and get a simple value
        test_key = f"health_check:{int(time.time())}"
        test_value = f"test_{time.time()}"

        cache.set(test_key, test_value, 10)  # 10 second timeout
        retrieved_value = cache.get(test_key)

        if retrieved_value == test_value:
            status = STATUS_OK
            message = "Cache is operational"
        else:
            status = STATUS_WARNING
            message = "Cache retrieval failed"

        # Clean up
        cache.delete(test_key)

    except Exception as e:
        status = STATUS_CRITICAL
        message = f"Cache error: {str(e)}"
        logger.error(f"Cache health check failed: {str(e)}")

    response_time = time.time() - start_time

    # Adjust status based on response time
    if status == STATUS_OK and response_time > RESPONSE_TIME_WARNING:
        status = STATUS_WARNING
        message = f"Cache is slow (took {response_time:.2f}s)"

    return {
        "component": CACHE_CHECK,
        "status": status,
        "message": message,
        "response_time": round(response_time, 3),
        "timestamp": timezone.now().isoformat(),
    }


def check_redis() -> Dict[str, Any]:
    """
    Check if Redis is reachable and responsive.

    Returns:
        Dict with status information
    """
    # Import here to avoid circular imports
    from .cache import is_redis_available

    start_time = time.time()
    status = STATUS_UNKNOWN
    message = ""
    version = ""
    details = {}

    try:
        # First check if Redis is available using our utility function
        if is_redis_available():
            redis_client = get_redis_connection()
            status = STATUS_OK
            message = "Redis is operational"

            # Get Redis info for additional context
            try:
                info = redis_client.info()  # type: ignore
                if isinstance(info, dict):
                    version = info.get("redis_version", "unknown")
                    if not isinstance(version, str):
                        version = str(version)

                    # Add more details from Redis info
                    details = {
                        "uptime_days": round(float(info.get("uptime_in_seconds", 0)) / 86400, 2),
                        "memory_used": info.get("used_memory_human", "unknown"),
                        "clients_connected": info.get("connected_clients", 0),
                        "keys_count": sum(
                            db.get("keys", 0)
                            for name, db in info.items()
                            if name.startswith("db") and isinstance(db, dict)
                        ),
                    }
            except Exception as e:
                # We can still be operational even if we can't get detailed info
                logger.warning(f"Error getting Redis info: {str(e)}")
        else:
            status = STATUS_CRITICAL
            message = "Redis is not available"

    except Exception as e:
        status = STATUS_CRITICAL
        message = f"Redis error: {str(e)}"
        logger.error(f"Redis health check failed: {str(e)}")

    response_time = time.time() - start_time

    # Adjust status based on response time
    if status == STATUS_OK and response_time > RESPONSE_TIME_WARNING:
        status = STATUS_WARNING
        message = f"Redis is slow (took {response_time:.2f}s)"

    result = {
        "component": REDIS_CHECK,
        "status": status,
        "message": message,
        "response_time": round(response_time, 3),
        "timestamp": timezone.now().isoformat(),
        "version": version,
    }

    # Add additional details if available
    if details:
        result["details"] = details

    return result


def check_celery() -> Dict[str, Any]:
    """
    Check if Celery is operational by sending a simple task.

    Returns:
        Dict with status information
    """
    start_time = time.time()
    status = STATUS_UNKNOWN
    message = ""

    try:
        # Import here to avoid circular imports
        from .tasks import health_check_task

        # Submit a simple task
        task = health_check_task.delay()
        result = task.get(timeout=5)  # Wait up to 5 seconds for result

        if result == "ok":
            status = STATUS_OK
            message = "Celery is operational"
        else:
            status = STATUS_WARNING
            message = f"Celery returned unexpected result: {result}"

    except ImportError:
        status = STATUS_UNKNOWN
        message = "Celery task not available"
    except Exception as e:
        status = STATUS_CRITICAL
        message = f"Celery error: {str(e)}"
        logger.error(f"Celery health check failed: {str(e)}")

    response_time = time.time() - start_time

    return {
        "component": CELERY_CHECK,
        "status": status,
        "message": message,
        "response_time": round(response_time, 3),
        "timestamp": timezone.now().isoformat(),
    }


def check_storage(path: Optional[str] = None) -> Dict[str, Any]:
    """
    Check if the storage is accessible and writable.

    Args:
        path: Path to check (defaults to MEDIA_ROOT)

    Returns:
        Dict with status information
    """
    start_time = time.time()
    status = STATUS_UNKNOWN
    message = ""

    if not path:
        path = getattr(settings, "MEDIA_ROOT", os.path.join(settings.BASE_DIR, "media"))

    try:
        # Check if path exists
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

        # Check if path is writable by creating a temp file
        test_file = os.path.join(path, f"health_check_{int(time.time())}.txt")
        with open(test_file, "w") as f:
            f.write("health check")

        # Clean up
        os.remove(test_file)

        status = STATUS_OK
        message = "Storage is accessible and writable"

    except Exception as e:
        status = STATUS_CRITICAL
        message = f"Storage error: {str(e)}"
        logger.error(f"Storage health check failed: {str(e)}")

    response_time = time.time() - start_time

    return {
        "component": STORAGE_CHECK,
        "status": status,
        "message": message,
        "response_time": round(response_time, 3),
        "timestamp": timezone.now().isoformat(),
        "path": path,
    }


def check_external_service(url: str, expected_status: int = 200, timeout: int = 5) -> Dict[str, Any]:
    """
    Check if an external service is reachable.

    Args:
        url: URL to check
        expected_status: Expected HTTP status code
        timeout: Timeout in seconds

    Returns:
        Dict with status information
    """
    start_time = time.time()
    status = STATUS_UNKNOWN
    message = ""

    try:
        # Make request
        response = requests.get(url, timeout=timeout)

        if response.status_code == expected_status:
            status = STATUS_OK
            message = f"Service at {url} is operational"
        else:
            status = STATUS_WARNING
            message = f"Service at {url} returned status {response.status_code}, expected {expected_status}"

    except requests.exceptions.Timeout:
        status = STATUS_CRITICAL
        message = f"Service at {url} timed out after {timeout}s"
    except requests.exceptions.ConnectionError:
        status = STATUS_CRITICAL
        message = f"Could not connect to service at {url}"
    except Exception as e:
        status = STATUS_CRITICAL
        message = f"Error checking service at {url}: {str(e)}"
        logger.error(f"External service health check failed for {url}: {str(e)}")

    response_time = time.time() - start_time

    return {
        "component": EXTERNAL_SERVICE_CHECK,
        "status": status,
        "message": message,
        "response_time": round(response_time, 3),
        "timestamp": timezone.now().isoformat(),
        "url": url,
    }


def check_dns(hostname: str, port: int = 80, timeout: int = 5) -> Dict[str, Any]:
    """
    Check if a hostname is resolvable and reachable.

    Args:
        hostname: Hostname to check
        port: Port to check
        timeout: Timeout in seconds

    Returns:
        Dict with status information
    """
    start_time = time.time()
    status = STATUS_UNKNOWN
    message = ""

    try:
        # Try to resolve hostname
        ip_address = socket.gethostbyname(hostname)

        # Try to connect to the host
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        result = sock.connect_ex((ip_address, port))
        sock.close()

        if result == 0:
            status = STATUS_OK
            message = f"Host {hostname} is reachable on port {port}"
        else:
            status = STATUS_WARNING
            message = f"Host {hostname} is not reachable on port {port}"

    except socket.gaierror:
        status = STATUS_CRITICAL
        message = f"Could not resolve hostname {hostname}"
    except Exception as e:
        status = STATUS_CRITICAL
        message = f"Error checking DNS for {hostname}: {str(e)}"
        logger.error(f"DNS health check failed for {hostname}: {str(e)}")

    response_time = time.time() - start_time

    return {
        "component": "dns",
        "status": status,
        "message": message,
        "response_time": round(response_time, 3),
        "timestamp": timezone.now().isoformat(),
        "hostname": hostname,
        "port": port,
    }


def run_all_checks() -> Dict[str, Any]:
    """
    Run all health checks and return aggregated results.

    Returns:
        Dict with all health check results and overall status
    """
    results = {"database": check_database(), "cache": check_cache(), "redis": check_redis()}

    # Add more optional checks
    if getattr(settings, "CELERY_BROKER_URL", None):
        results["celery"] = check_celery()

    if getattr(settings, "MEDIA_ROOT", None):
        results["storage"] = check_storage()

    # Check external service dependencies
    external_services = getattr(settings, "HEALTH_CHECK_SERVICES", {})
    for name, url in external_services.items():
        results[f"service_{name}"] = check_external_service(url)

    # Determine overall status
    status = STATUS_OK

    for check in results.values():
        if check["status"] == STATUS_CRITICAL:
            status = STATUS_CRITICAL
            break
        elif check["status"] == STATUS_WARNING and status != STATUS_CRITICAL:
            status = STATUS_WARNING

    # Compile the response
    response = {"status": status, "timestamp": timezone.now().isoformat(), "checks": results}

    return response


def get_system_info() -> Dict[str, Any]:
    """
    Get system information.

    Returns:
        Dict with system information
    """
    import multiprocessing
    import platform
    import sys

    # Get Django and Python info
    info = {
        "platform": platform.platform(),
        "python_version": sys.version,
        "django_version": settings.DJANGO_VERSION if hasattr(settings, "DJANGO_VERSION") else "unknown",
        "cpu_count": multiprocessing.cpu_count(),
        "hostname": socket.gethostname(),
        "timestamp": timezone.now().isoformat(),
    }

    # Add application-specific info
    info["app_name"] = getattr(settings, "APP_NAME", "ChessMate")
    info["app_version"] = getattr(settings, "APP_VERSION", "1.0.0")
    info["environment"] = getattr(settings, "ENVIRONMENT", "development" if settings.DEBUG else "production")

    return info


def health_check_view(request):
    """
    Basic health check endpoint.

    This endpoint is used by load balancers and monitoring tools to check
    if the application is running. It simply returns HTTP 200 with "ok"
    in the response body.

    Returns:
        HttpResponse: Simple "ok" response with status 200 if healthy
    """
    # This is a minimal check - just verify the app is running
    # For more comprehensive checks, use the detailed health check endpoint
    return HttpResponse("ok", content_type="text/plain")


def readiness_check_view(request):
    """
    Readiness check endpoint.

    This endpoint checks if the application is ready to serve requests
    by verifying that its dependencies (database, cache, etc.) are available.

    Returns:
        JsonResponse: JSON with "ready" status if all dependencies are available,
                     or "not_ready" with details if any dependency is not available
    """
    # Check critical dependencies: database and cache
    db_status = check_database()
    cache_status = check_cache()
    redis_status = check_redis()

    # If any critical dependency is not available, return not ready
    if (
        db_status["status"] == STATUS_CRITICAL
        or cache_status["status"] == STATUS_CRITICAL
        or redis_status["status"] == STATUS_CRITICAL
    ):

        # Determine which component is causing the issue
        failing_components = []
        if db_status["status"] == STATUS_CRITICAL:
            failing_components.append(db_status["message"])
        if cache_status["status"] == STATUS_CRITICAL:
            failing_components.append(cache_status["message"])
        if redis_status["status"] == STATUS_CRITICAL:
            failing_components.append(redis_status["message"])

        return JsonResponse(
            {"status": "not_ready", "message": f"Not ready: {', '.join(failing_components)}"}, status=503
        )  # Service Unavailable

    # All critical dependencies are available
    return JsonResponse({"status": "ready"})


def detailed_health_check_view(request):
    """
    Detailed health check endpoint.

    This endpoint performs comprehensive checks on all system components
    and returns detailed status information.

    Returns:
        JsonResponse: JSON with detailed health check information
    """
    start_time = time.time()

    # Get health status for all components
    health_result = run_all_checks()

    # Add system information
    system_info = get_system_info()

    # Add request duration
    duration_ms = int((time.time() - start_time) * 1000)

    # Determine HTTP status code based on health status
    if health_result["status"] == STATUS_CRITICAL:
        status_code = 503  # Service Unavailable
    elif health_result["status"] == STATUS_WARNING:
        status_code = 207  # Multi-Status
    else:
        status_code = 200  # OK

    # Build response
    response_data = {
        "status": health_result["status"],
        "environment": "development" if settings.DEBUG else "production",
        "timestamp": timezone.now().isoformat(),
        "request_duration_ms": duration_ms,
        "version": getattr(settings, "APP_VERSION", "1.0.0"),
        "checks": health_result["checks"],
        "system_info": system_info,
    }

    return JsonResponse(response_data, status=status_code)


def system_status_view(request):
    """
    System status endpoint for administrators.

    This endpoint provides detailed system status information for administrators,
    including cache statistics, Celery task statistics, and other operational metrics.

    Returns:
        JsonResponse: JSON with detailed system status information
    """
    # Check if user is authenticated and is an admin
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    # Get health status for all components
    health_result = run_all_checks()

    # Build response with additional system information
    response_data = {
        "status": health_result["status"],
        "environment": "development" if settings.DEBUG else "production",
        "timestamp": timezone.now().isoformat(),
        "version": getattr(settings, "APP_VERSION", "1.0.0"),
        "health": health_result,
        "tasks": {
            "pending": 0,  # Replace with actual Celery task statistics
            "running": 0,
            "completed": 0,
            "failed": 0,
        },
        "cache": {
            "default": {
                "type": "redis",
                "location": getattr(settings, "REDIS_URL", "redis://localhost:6379/0"),
                "version": get_redis_connection().info().get("redis_version", "unknown"),
                "clients": get_redis_connection().info().get("connected_clients", 0),
                "memory": f"{get_redis_connection().info().get('used_memory_human', '0')}",
            }
        },
        "system": get_system_info(),
    }

    return JsonResponse(response_data)
