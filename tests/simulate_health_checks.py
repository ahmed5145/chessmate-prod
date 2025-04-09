#!/usr/bin/env python
"""
Script to simulate health checks in a test environment.

This script mocks the health check implementation to test its functionality
without requiring a running server.
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List

# Mock components status
components = {"database": True, "cache": True, "redis": True, "celery": True, "storage": True}

# Mock settings
settings = {
    "DEBUG": True,
    "APP_VERSION": "1.0.0",
    "APP_NAME": "ChessMate (Test)",
    "RESPONSE_TIME_WARNING": 0.5,
    "RESPONSE_TIME_CRITICAL": 2.0,
}

# Status constants
STATUS_OK = "ok"
STATUS_WARNING = "warning"
STATUS_CRITICAL = "critical"
STATUS_UNKNOWN = "unknown"


def simulate_delay(component: str) -> float:
    """Simulate response delay for a component."""
    delays = {"database": 0.1, "cache": 0.05, "redis": 0.02, "celery": 0.3, "storage": 0.08}
    return delays.get(component, 0.01)


def check_component(component: str, working: bool = True) -> Dict[str, Any]:
    """Simulate checking a component's health."""
    start_time = time.time()

    # Simulate component check delay
    time.sleep(simulate_delay(component))

    if not working:
        status = STATUS_CRITICAL
        message = f"{component} is not operational"
    else:
        status = STATUS_OK
        message = f"{component} is operational"

    response_time = time.time() - start_time

    # Get threshold values with proper type conversion to ensure they're floats
    critical_threshold = float(settings.get("RESPONSE_TIME_CRITICAL", 2.0))
    warning_threshold = float(settings.get("RESPONSE_TIME_WARNING", 0.5))

    # Adjust status based on response time
    if status == STATUS_OK and response_time > critical_threshold:
        status = STATUS_CRITICAL
        message = f"{component} is too slow (took {response_time:.2f}s)"
    elif status == STATUS_OK and response_time > warning_threshold:
        status = STATUS_WARNING
        message = f"{component} is slow (took {response_time:.2f}s)"

    return {
        "component": component,
        "status": status,
        "message": message,
        "response_time": round(response_time, 3),
        "timestamp": datetime.now().isoformat(),
    }


def get_system_info() -> Dict[str, Any]:
    """Get mock system information."""
    return {
        "platform": "Test Platform",
        "python_version": "3.10.0 (Test)",
        "django_version": "4.2.5",
        "cpu_count": 4,
        "hostname": "test-host",
        "timestamp": datetime.now().isoformat(),
        "app_name": settings["APP_NAME"],
        "app_version": settings["APP_VERSION"],
        "environment": "development" if settings["DEBUG"] else "production",
    }


def run_all_checks() -> Dict[str, Any]:
    """Run all simulated health checks."""
    checks = {}

    for component, working in components.items():
        checks[component] = check_component(component, working)

    # Determine overall status
    status = STATUS_OK

    for check in checks.values():
        if check["status"] == STATUS_CRITICAL:
            status = STATUS_CRITICAL
            break
        elif check["status"] == STATUS_WARNING and status != STATUS_CRITICAL:
            status = STATUS_WARNING

    return {"status": status, "timestamp": datetime.now().isoformat(), "checks": checks}


def simulate_health_check() -> Dict[str, str]:
    """Simulate basic health check endpoint."""
    return {"status": "ok"}


def simulate_readiness_check() -> Dict[str, Any]:
    """Simulate readiness check endpoint."""
    for component, working in components.items():
        if not working:
            return {"status": "not_ready", "message": f"Not ready: {component} is not operational"}

    return {"status": "ready"}


def simulate_detailed_health_check() -> Dict[str, Any]:
    """Simulate detailed health check endpoint."""
    start_time = time.time()

    # Get health status for all components
    health_result = run_all_checks()

    # Add request duration
    duration_ms = int((time.time() - start_time) * 1000)

    # Build response
    return {
        "status": health_result["status"],
        "environment": "development" if settings["DEBUG"] else "production",
        "timestamp": datetime.now().isoformat(),
        "request_duration_ms": duration_ms,
        "version": settings["APP_VERSION"],
        "checks": health_result["checks"],
        "system_info": get_system_info(),
    }


def simulate_system_status() -> Dict[str, Any]:
    """Simulate system status endpoint for admins."""
    health_result = run_all_checks()

    return {
        "status": health_result["status"],
        "environment": "development" if settings["DEBUG"] else "production",
        "timestamp": datetime.now().isoformat(),
        "version": settings["APP_VERSION"],
        "health": health_result,
        "tasks": {"pending": 5, "running": 2, "completed": 120, "failed": 3},
        "cache": {
            "default": {
                "type": "redis",
                "location": "redis://localhost:6379/1",
                "version": "6.2.6",
                "clients": 5,
                "memory": "24.56M",
            }
        },
        "system": get_system_info(),
    }


def test_health_checks() -> None:
    """Run all health check simulations and display the results."""
    print("\n=== Basic Health Check ===")
    print(json.dumps(simulate_health_check(), indent=2))

    print("\n=== Readiness Check ===")
    print(json.dumps(simulate_readiness_check(), indent=2))

    print("\n=== Detailed Health Check ===")
    result = simulate_detailed_health_check()
    print(
        json.dumps(
            {
                "status": result["status"],
                "environment": result["environment"],
                "version": result["version"],
                "request_duration_ms": result["request_duration_ms"],
                # Only show a sample of the checks to keep output manageable
                "checks_sample": {"database": result["checks"]["database"], "cache": result["checks"]["cache"]},
            },
            indent=2,
        )
    )

    print("\n=== System Status ===")
    system_result = simulate_system_status()
    print(
        json.dumps(
            {
                "status": system_result["status"],
                "environment": system_result["environment"],
                "version": system_result["version"],
                "tasks": system_result["tasks"],
                "cache": system_result["cache"],
            },
            indent=2,
        )
    )


def test_failing_component() -> None:
    """Test health checks with a failing component."""
    print("\n=== Test with Failed Component ===")

    # Simulate database failure
    components["database"] = False

    print("\n=== Readiness Check (with failure) ===")
    print(json.dumps(simulate_readiness_check(), indent=2))

    print("\n=== Detailed Health Check (with failure) ===")
    result = simulate_detailed_health_check()
    print(
        json.dumps(
            {
                "status": result["status"],
                "environment": result["environment"],
                "version": result["version"],
                # Only show the failing component
                "failing_component": result["checks"]["database"],
            },
            indent=2,
        )
    )

    # Reset the database status
    components["database"] = True


def test_slow_component() -> None:
    """Test health checks with a slow component."""
    print("\n=== Test with Slow Component ===")

    # Store original delay function
    original_delay = simulate_delay

    # Define new delay function
    def modified_delay(component: str) -> float:
        if component == "redis":
            return 0.6  # Just over the warning threshold
        return original_delay(component)

    # Replace delay function
    global_delays = globals()
    global_delays["simulate_delay"] = modified_delay

    print("\n=== Detailed Health Check (with slow component) ===")
    result = simulate_detailed_health_check()
    print(
        json.dumps(
            {
                "status": result["status"],
                "environment": result["environment"],
                "version": result["version"],
                # Only show the slow component
                "slow_component": result["checks"]["redis"],
            },
            indent=2,
        )
    )

    # Reset the delay function
    global_delays["simulate_delay"] = original_delay


if __name__ == "__main__":
    print("=== ChessMate Health Check Simulation ===")
    test_health_checks()
    test_failing_component()
    test_slow_component()
    print("\n=== Simulation Complete ===")
