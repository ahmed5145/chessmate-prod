# ChessMate Monitoring and Health Checks

This document explains the monitoring and health check systems implemented in the ChessMate application.

## Health Check Endpoints

### Basic Health Check

Endpoint: `/health/`

This is a simple endpoint that returns a `200 OK` status with "ok" in the response body. It's designed for load balancers and basic monitoring systems that just need to know if the application is running.

### Readiness Check

Endpoint: `/readiness/`

This endpoint verifies that the application's core dependencies (database, cache, etc.) are available and functioning. It returns:
- `200 OK` with "ready" if all dependencies are available
- `503 Service Unavailable` with details of the issues if any dependency is not available

### Detailed Health Check

Endpoint: `/api/v1/health/detailed/`

This endpoint performs comprehensive checks on all system components and returns detailed status information in JSON format. The response includes:

- Overall status: "ok", "warning", or "critical"
- Environment information
- Timestamp
- Request duration
- Version information
- Status of each component
- System information

The endpoint returns different HTTP status codes based on the overall status:
- `200 OK` if all checks pass
- `207 Multi-Status` if some checks have warnings
- `503 Service Unavailable` if any check is critical

Example response:

```json
{
  "status": "ok",
  "environment": "development",
  "timestamp": "2024-05-28T12:34:56.789Z",
  "request_duration_ms": 123,
  "version": "1.0.0",
  "checks": {
    "database": {
      "component": "database",
      "status": "ok",
      "message": "Database is operational",
      "response_time": 0.015,
      "timestamp": "2024-05-28T12:34:56.789Z"
    },
    "cache": {
      "component": "cache",
      "status": "ok",
      "message": "Cache is operational",
      "response_time": 0.005,
      "timestamp": "2024-05-28T12:34:56.789Z"
    },
    "redis": {
      "component": "redis",
      "status": "ok",
      "message": "Redis is operational",
      "response_time": 0.003,
      "timestamp": "2024-05-28T12:34:56.789Z",
      "version": "6.2.6"
    },
    "celery": {
      "component": "celery",
      "status": "ok",
      "message": "Celery is operational",
      "response_time": 0.245,
      "timestamp": "2024-05-28T12:34:56.789Z"
    },
    "storage": {
      "component": "storage",
      "status": "ok",
      "message": "Storage is accessible and writable",
      "response_time": 0.008,
      "timestamp": "2024-05-28T12:34:56.789Z",
      "path": "/app/media"
    }
  },
  "system_info": {
    "platform": "Linux-5.10.0-x86_64-with-glibc2.31",
    "python_version": "3.10.6",
    "django_version": "4.2.5",
    "cpu_count": 4,
    "hostname": "web-1",
    "timestamp": "2024-05-28T12:34:56.789Z",
    "app_name": "ChessMate",
    "app_version": "1.0.0",
    "environment": "development"
  }
}
```

### System Status (Admin Only)

Endpoint: `/api/v1/system/status/`

This endpoint provides detailed system status information for administrators, including cache statistics, Celery task statistics, and other operational metrics.

## Testing Health Checks

The `tests/test_health_checks.py` script can be used to test the health check endpoints. See `tests/README.md` for details.

## Configuring Health Checks

Health checks can be configured in the application settings:

```python
# Health check settings
HEALTH_CHECK_SERVICES = {
    'example_api': 'https://api.example.com/status',
}

# Response time thresholds (in seconds)
RESPONSE_TIME_WARNING = 0.5
RESPONSE_TIME_CRITICAL = 2.0
```

## Celery Health Checks

The `/api/v1/health/run-check-task/` endpoint can be used to test Celery by running a simple health check task. The task will return "ok" if Celery is working.

The application also includes a `monitor_system_task` Celery task that can be scheduled to periodically check the system health and send alerts for critical issues.

## Monitoring in Production

For production monitoring, it's recommended to:

1. Set up periodic health check requests using a monitoring system like Prometheus, Nagios, or Datadog.
2. Configure alerting based on the health check responses.
3. Schedule the `monitor_system_task` to run every few minutes.
4. Set up log aggregation to collect and analyze logs from all components.
5. Use a performance monitoring tool to track response times and resource usage.

## Health Check Status Codes

The health check system uses the following status codes:

- `ok`: The component is functioning normally
- `warning`: The component is functioning but with degraded performance or other non-critical issues
- `critical`: The component is not functioning or has critical issues
- `unknown`: The status of the component could not be determined

## Customizing Health Checks

To add a new health check:

1. Create a new function in `health_checks.py` that performs the check
2. Add the check to the `run_all_checks` function
3. Update the relevant endpoints to include the new check

Example:

```python
def check_my_service() -> Dict[str, Any]:
    """Check if my service is working."""
    start_time = time.time()

    try:
        # Perform check
        # ...
        status = STATUS_OK
        message = "My service is operational"
    except Exception as e:
        status = STATUS_CRITICAL
        message = f"My service error: {str(e)}"

    return {
        'component': 'my_service',
        'status': status,
        'message': message,
        'response_time': time.time() - start_time,
        'timestamp': timezone.now().isoformat()
    }

def run_all_checks() -> Dict[str, Any]:
    """Run all health checks."""
    results = {
        # Existing checks...
        'my_service': check_my_service()
    }
    # ...
```
