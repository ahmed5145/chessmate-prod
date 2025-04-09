"""
ChessMate Telemetry Package

This package provides telemetry and monitoring capabilities for the ChessMate application.
It includes middleware for request tracking, metric collectors, and exporters for various
monitoring systems.
"""

from django.conf import settings

# Default configuration
DEFAULT_CONFIG = {
    "ENABLED": True,
    "SAMPLE_RATE": 1.0,  # Sample 100% of requests
    "SLOW_REQUEST_THRESHOLD": 1.0,  # seconds
    "EXCLUDED_PATHS": ["/health/", "/metrics/"],
    "EXPORTERS": ["prometheus"],
}

# Initialize configuration
config = getattr(settings, "TELEMETRY_CONFIG", DEFAULT_CONFIG)

# Version
__version__ = "1.0.0"
