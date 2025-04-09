"""
Logging configuration for the ChessMate application.

This module provides a comprehensive logging configuration with:
- Console logging for development
- Rotating file logging for production
- Error-specific logging
- JSON logging for structured log analysis
- API request logging
- Sentry integration for error tracking (optional)
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict  # Add type imports

# Base directory for logs
LOGS_DIR = Path(os.environ.get("LOGS_DIR", "logs"))
LOGS_DIR.mkdir(exist_ok=True)

# Log levels based on environment
DEBUG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Sentry DSN (set this in environment variables for production)
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")

# Common log format with all necessary information
DETAILED_FORMAT = (
    "%(levelname)s %(asctime)s %(name)s %(process)d %(thread)d " "%(module)s:%(lineno)d [%(request_id)s] %(message)s"
)

# JSON format for machine processing
JSON_FORMAT = {
    "level": "%(levelname)s",
    "timestamp": "%(asctime)s",
    "name": "%(name)s",
    "process": "%(process)d",
    "thread": "%(thread)d",
    "module": "%(module)s",
    "line": "%(lineno)d",
    "request_id": "%(request_id)s",
    "message": "%(message)s",
}

# Configuration dictionary
LOGGING: Dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {
            "()": "core.middleware.RequestIDFilter",
        },
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "formatters": {
        "verbose": {
            "format": DETAILED_FORMAT,
            "style": "%",
        },
        "simple": {
            "format": "%(levelname)s %(message)s",
            "style": "%",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": DETAILED_FORMAT,
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "filters": ["request_id"],
        },
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "chessmate.log",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 10,
            "formatter": "verbose",
            "filters": ["request_id"],
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "error.log",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 10,
            "formatter": "verbose",
            "filters": ["request_id"],
        },
        "json_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "structured.log",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "formatter": "json",
            "filters": ["request_id"],
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "filters": ["require_debug_false", "request_id"],
            "include_html": True,
        },
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["console", "file", "error_file"],
        "level": DEBUG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "error_file", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console", "file"],
            "level": "INFO",  # Set to DEBUG to log all SQL queries
            "propagate": False,
        },
        "core": {
            "handlers": ["console", "file", "error_file", "json_file"],
            "level": DEBUG_LEVEL,
            "propagate": False,
        },
        "core.performance": {
            "handlers": ["console", "json_file"],
            "level": "INFO",
            "propagate": False,
        },
        "core.security": {
            "handlers": ["console", "error_file", "json_file", "mail_admins"],
            "level": "INFO",
            "propagate": False,
        },
        "core.api": {
            "handlers": ["console", "file", "json_file"],
            "level": "INFO",
            "propagate": False,
        },
        "core.cache": {
            "handlers": ["console", "file"],
            "level": DEBUG_LEVEL,
            "propagate": False,
        },
        "core.task_manager": {
            "handlers": ["console", "file", "json_file"],
            "level": "INFO",
            "propagate": False,
        },
        "core.health_checks": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "py.warnings": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# Add Sentry integration if DSN is provided and the package is available
if SENTRY_DSN:
    try:
        import sentry_sdk  # type: ignore
        from sentry_sdk.integrations.django import DjangoIntegration  # type: ignore
        from sentry_sdk.integrations.logging import LoggingIntegration  # type: ignore

        # Get the root level from LOGGING dict safely
        root_level = LOGGING.get("root", {}).get("level", DEBUG_LEVEL)
        
        # Get the numeric logging level for the specified level string
        root_level_int = getattr(logging, root_level) if isinstance(root_level, str) else root_level

        # Set up Sentry SDK
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                DjangoIntegration(),
                LoggingIntegration(
                    level=root_level_int,
                    event_level=logging.ERROR,  # Use the actual logging constant instead of string
                ),
            ],
            # Set traces_sample_rate to 1.0 to capture 100% of transactions for performance monitoring
            # We recommend adjusting this value in production
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            # Send environment to Sentry to differentiate between environments
            environment=os.environ.get("ENVIRONMENT", "development"),
            # If you wish to associate users to errors (assuming you are using
            # django.contrib.auth) you may enable sending PII data
            send_default_pii=True,
        )
    except ImportError:
        print("Sentry SDK not installed. Error tracking will be disabled.")
