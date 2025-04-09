"""
Middleware for collecting request-level telemetry data.
"""

import logging
import time
from typing import Any, Callable

from django.http import HttpRequest, HttpResponse

from . import config
from .collectors import database_collector, system_collector
from .metrics import REQUEST_METRICS

logger = logging.getLogger(__name__)


class TelemetryMiddleware:
    """Middleware for collecting request telemetry data."""

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self.metrics = REQUEST_METRICS

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not self._should_track_request(request):
            return self.get_response(request)

        # Start timing
        start_time = time.time()

        # Collect pre-request metrics
        self._collect_pre_request_metrics()

        # Process request
        response = self.get_response(request)

        # Collect post-request metrics
        self._collect_post_request_metrics(request, response, start_time)

        return response

    def _should_track_request(self, request: HttpRequest) -> bool:
        """Determine if request should be tracked based on configuration."""
        if not config["ENABLED"]:
            return False

        # Check if path is excluded
        path = request.path.rstrip("/")
        if path in config["EXCLUDED_PATHS"]:
            return False

        # Apply sampling rate
        if config["SAMPLE_RATE"] < 1.0:
            import random

            if random.random() > config["SAMPLE_RATE"]:
                return False

        return True

    def _collect_pre_request_metrics(self) -> None:
        """Collect metrics before processing the request."""
        try:
            # Collect system metrics
            system_collector.collect_memory_metrics()
            system_collector.collect_cpu_metrics()
        except Exception as e:
            logger.error(f"Error collecting pre-request metrics: {e}")

    def _collect_post_request_metrics(self, request: HttpRequest, response: HttpResponse, start_time: float) -> None:
        """Collect metrics after processing the request."""
        try:
            duration = time.time() - start_time

            # Record request count
            self.metrics["http_requests_total"].increment(
                labels={"method": request.method, "path": request.path, "status": str(response.status_code)}
            )

            # Record request duration
            self.metrics["http_request_duration_seconds"].observe(
                duration, labels={"method": request.method, "path": request.path}
            )

            # Collect database metrics
            database_collector.collect_query_metrics()

            # Log slow requests
            if duration > config["SLOW_REQUEST_THRESHOLD"]:
                logger.warning(f"Slow request detected: {request.method} {request.path} " f"took {duration:.2f}s")

        except Exception as e:
            logger.error(f"Error collecting post-request metrics: {e}")

    def process_exception(self, request: HttpRequest, exception: Exception) -> None:
        """Handle and record request exceptions."""
        try:
            # Record exception in metrics
            self.metrics["http_requests_total"].increment(
                labels={"method": request.method, "path": request.path, "status": "500"}
            )

            logger.error(f"Request exception: {request.method} {request.path} - {str(exception)}", exc_info=True)
        except Exception as e:
            logger.error(f"Error processing exception in middleware: {e}")

    def process_template_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Process template response for additional metrics."""
        try:
            # Add template rendering time if available
            if hasattr(response, "template_render_time"):
                self.metrics["template_render_duration_seconds"].observe(
                    response.template_render_time, labels={"template": str(response.template_name)}
                )
        except Exception as e:
            logger.error(f"Error processing template response: {e}")

        return response
