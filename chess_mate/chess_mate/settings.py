"""
Django settings for chess_mate project.
"""

import logging
import os
import platform
from datetime import timedelta
from pathlib import Path
from typing import Union
import environ  # type: ignore

from dotenv import load_dotenv

from .logging_config import LOGGING

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

# Initialize environ
env = environ.Env()

# Read .env file if it exists
# First try environment-specific .env file
env_file = os.path.join(PROJECT_ROOT, f".env.{os.environ.get('ENVIRONMENT', 'development')}")
if os.path.exists(env_file):
    env.read_env(env_file)
else:
    # Fallback to regular .env file
    env.read_env(os.path.join(PROJECT_ROOT, ".env"))

# Testing mode flag - must be defined before any dependent settings
TESTING: bool = env('TESTING', default='False').lower() == "true"

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='django-insecure-p1*dz5cqu(21e+w9a%d15i-syw9!$2+*q7%oqg$a!^n*bw00ki')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DEBUG', default=False)

ENVIRONMENT = env('ENVIRONMENT', default='production')

# Environment detection
IS_PRODUCTION = ENVIRONMENT.lower() == "production"

# OpenAI Settings
OPENAI_API_KEY = env('OPENAI_API_KEY', default='')
USE_OPENAI = bool(OPENAI_API_KEY)
OPENAI_MODEL = "gpt-3.5-turbo"
OPENAI_MAX_TOKENS = 500
OPENAI_TEMPERATURE = 0.7
OPENAI_RATE_LIMIT = {
    "max_requests": 100 if env('TEST_MODE', default='False').lower() == "true" else 50,
    "window_seconds": 60 if env('TEST_MODE', default='False').lower() == "true" else 3600,
    "min_interval": 0.1 if env('TEST_MODE', default='False').lower() == "true" else 0.5,
}
OPENAI_CACHE_KEY = "openai_rate_limit"
OPENAI_CACHE_TIMEOUT = 3600

# Stripe Settings
STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY', default='')
STRIPE_PUBLISHABLE_KEY = env('STRIPE_PUBLISHABLE_KEY', default='')
STRIPE_WEBHOOK_SECRET = env('STRIPE_WEBHOOK_SECRET', default='')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# Application definition
INSTALLED_APPS = [
    "corsheaders",  # Must be at the top
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "core.apps.CoreConfig",  # Use our custom AppConfig
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # Must be first
    "core.middleware.RequestIDMiddleware",  # Add request ID to each request
    "core.middleware.RequestFixMiddleware",  # Fix request headers like Authorization
    "django.middleware.common.CommonMiddleware",  # Must be right after CORS
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.RequestValidationMiddleware",  # New validation middleware
    "core.middleware.RateLimitMiddleware",  # Add rate limiting middleware
    "core.middleware.SecurityHeadersMiddleware",  # Add security headers middleware
    "core.cache_middleware.CacheInvalidationMiddleware",  # Cache invalidation middleware
]

ROOT_URLCONF = "chess_mate.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, "frontend", "build"),
            os.path.join(BASE_DIR, "core", "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "chess_mate.wsgi.application"

# Database configuration - use SQLite by default for development, PostgreSQL for production
if TESTING:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "test_db.sqlite3",
        }
    }
elif IS_PRODUCTION:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env('DB_NAME', default='chessmate'),
            "USER": env('DB_USER', default='postgres'),
            "PASSWORD": env('DB_PASSWORD', default=''),
            "HOST": env('DB_HOST', default='localhost'),
            "PORT": env('DB_PORT', default='5432'),
            "CONN_MAX_AGE": int(env('DB_CONN_MAX_AGE', default='300')),  # 5 minutes persistent connection
            "OPTIONS": {
                "connect_timeout": 10,  # Reduced timeout for faster error detection
                "client_encoding": "UTF8",
                "application_name": "ChessMate",  # Identify the application in PostgreSQL logs
                # Keepalive settings to detect and prevent stale connections
                "keepalives": 1,
                "keepalives_idle": 60,  # After 60s of inactivity, send keepalive
                "keepalives_interval": 10,  # Retry every 10s
                "keepalives_count": 5,  # Drop after 5 failed attempts
                # Performance optimizations
                "statement_timeout": 30000,  # 30s statement timeout to prevent long-running queries
                "effective_cache_size": int(env('DB_CACHE_SIZE', default='4096')),  # Cache size for query planning
                "work_mem": int(env('DB_WORK_MEM', default='16')),  # Memory for internal sort operations (MB)
                "maintenance_work_mem": int(
                    env('DB_MAINTENANCE_MEM', default='64')
                ),  # Memory for maintenance operations (MB)
                "max_connections": int(env('DB_MAX_CONNECTIONS', default='100')),  # Maximum concurrent connections
            },
            # Connection pooling settings
            "POOL_OPTIONS": {
                "POOL_SIZE": int(env('DB_POOL_SIZE', default='20')),  # Increased pool size for higher concurrency
                "MAX_OVERFLOW": int(env('DB_MAX_OVERFLOW', default='30')),  # Allow more overflow connections under load
                "RECYCLE": int(env('DB_RECYCLE_SECONDS', default='300')),  # Recycle connections after 5 minutes
                "TIMEOUT": int(env('DB_POOL_TIMEOUT', default='30')),  # Timeout for acquiring connection from pool
                "RETRY_ON_TIMEOUT": True,  # Retry on connection timeout
                "MAX_RETRIES": 3,  # Maximum number of retries
                "RETRY_DELAY": 0.1,  # Delay between retries (seconds)
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Database connection pooling configuration - used by django-db-connection-pool
if IS_PRODUCTION:
    DATABASE_POOL_ARGS = {
        "max_overflow": int(env('DB_MAX_OVERFLOW', default='30')),
        "pool_size": int(env('DB_POOL_SIZE', default='20')),
        "recycle": int(env('DB_RECYCLE_SECONDS', default='300')),
        "retry_on_timeout": True,
        "max_retries": 3,
        "retry_delay": 0.1,
        "timeout": int(env('DB_POOL_TIMEOUT', default='30')),
        "echo": DEBUG,
        "echo_pool": DEBUG,
    }

# Database indexes
INDEXES = {
    "core.Game": {
        "fields": ["user", "date_played", "platform", "result"],
    },
    "core.Profile": {
        "fields": ["user", "rating"],
    },
    "core.GameAnalysis": {
        "fields": ["game", "created_at"],
    },
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files configuration
STATIC_URL = "static/"
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "frontend", "build", "static"),
]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Media files configuration
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Redis settings
REDIS_DISABLED = os.getenv('REDIS_DISABLED', 'False').lower() == 'true'
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost').strip()
REDIS_PORT = os.getenv('REDIS_PORT', '6379').strip()
REDIS_DB = os.getenv('REDIS_DB', '0').strip()
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '').strip()

# Construct Redis URL
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
if REDIS_PASSWORD:
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

REDIS_SOCKET_TIMEOUT = int(env('REDIS_SOCKET_TIMEOUT', default=5))
REDIS_SOCKET_CONNECT_TIMEOUT = int(env('REDIS_SOCKET_CONNECT_TIMEOUT', default=5))
REDIS_RETRY_ON_TIMEOUT = env('REDIS_RETRY_ON_TIMEOUT', default='true').lower() == "true"
REDIS_CONNECTION_POOL_SIZE = int(env('REDIS_CONNECTION_POOL_SIZE', default=20))
REDIS_MAX_CONNECTIONS = int(env('REDIS_MAX_CONNECTIONS', default=100))

# Basic REST Framework Configuration without imports that might cause circular dependencies
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ) if not DEBUG else (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# The rest of the REST_FRAMEWORK configuration will be set up during application initialization
# in chess_mate/core/apps.py to avoid circular imports

# Cache settings - use local memory when Redis is disabled
if REDIS_DISABLED:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'chessmate-default',
            'TIMEOUT': 300,
            'OPTIONS': {
                'MAX_ENTRIES': 1000,
                'CULL_FREQUENCY': 3
            }
        }
    }
else:
    CACHES = {
        'default': {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
            'TIMEOUT': 300,
        }
    }

# Cache timeouts (in seconds)
CACHE_TIMEOUTS = {
    "user_profile": 60 * 60,  # 1 hour
    "user_games": 60 * 15,  # 15 minutes
    "game_details": 60 * 60,  # 1 hour
    "game_analysis": 60 * 60 * 24,  # 24 hours
    "leaderboard": 60 * 5,  # 5 minutes
    "static_content": 60 * 60 * 24,  # 24 hours
    "task_status": 60 * 5,  # 5 minutes
}

# Default cache
DEFAULT_CACHE = "default"

# Analysis Cache TTL (24 hours)
ANALYSIS_CACHE_TTL = 86400

# Cache time to live is 15 minutes
CACHE_TTL = 60 * 15

# Rate Limiting Settings
RATE_LIMIT = {
    "DEFAULT": {
        "MAX_REQUESTS": 100,
        "TIME_WINDOW": 60,
        "BACKEND": "default",  # Use Redis cache for rate limiting
    },
    "AUTH": {
        "MAX_REQUESTS": 5,
        "TIME_WINDOW": 60,
        "BACKEND": "default",  # Use Redis cache for rate limiting
    },
    "ANALYSIS": {
        "MAX_REQUESTS": 3,
        "TIME_WINDOW": 60,
        "BACKEND": "default",  # Use Redis cache for rate limiting
    },
    "CREDITS": {
        "MAX_REQUESTS": 5,
        "TIME_WINDOW": 60,
        "BACKEND": "default",  # Use Redis cache for rate limiting
    },
    "GAMES": {
        "MAX_REQUESTS": 10,
        "TIME_WINDOW": 60,
        "BACKEND": "default",  # Use Redis cache for rate limiting
    },
}

RATE_LIMIT_BACKEND = "default"  # Use Redis cache for rate limiting

# Logging Configuration
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "chessmate.log",
            "maxBytes": 10485760,  # 10 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "error.log",
            "maxBytes": 10485760,  # 10 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True,
        },
        "django.server": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "core": {
            "handlers": ["console", "file", "error_file"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# Session settings
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Celery Configuration
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 240
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_IMPORTS = ("core.tasks",)

# Game Analysis settings
ANALYSIS_COST = int(env('ANALYSIS_COST', default=5))  # Credits per analysis
ANALYSIS_DEPTH = int(env('ANALYSIS_DEPTH', default=20))  # Stockfish analysis depth
ANALYSIS_MOVE_TIME = int(env('ANALYSIS_MOVE_TIME', default=100))  # ms per move for Stockfish
MAX_POSITIONS_PER_GAME = int(env('MAX_POSITIONS_PER_GAME', default=300))  # Max positions to analyze per game

# Use our custom Redis client
REDIS_CLIENT_CLASS = "chess_mate.core.redis_config.get_redis_client"

# Stockfish settings
STOCKFISH_PATH = env('STOCKFISH_PATH', default=r'C:\Users\PCAdmin\Downloads\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe') # Needs to be changed in prod
STOCKFISH_THREADS = int(env('STOCKFISH_THREADS', default=4))
STOCKFISH_HASH_SIZE = int(env('STOCKFISH_HASH_SIZE', default=128))  # MB

# CSRF Configuration
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = False  # Frontend needs access to CSRF cookie
CSRF_COOKIE_SAMESITE = "Lax"  # Allows the cookie to be sent with same-site requests
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "https://chessmate.com",
    "https://www.chessmate.com",
    "https://api.chessmate.com",
]

# CORS Configuration
CORS_ALLOWED_ORIGINS = CSRF_TRUSTED_ORIGINS
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = ["Content-Type", "X-CSRFToken", "X-Request-ID", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "access-control-allow-credentials",
    "baggage",
    "sentry-trace",
    "cache-control"
]
CORS_PREFLIGHT_MAX_AGE = 86400  # Cache preflight requests for 24 hours
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

# JWT Settings (with improved security and compatibility)
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),   # Increased for testing
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id", 
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
}

# Authentication and authorization
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Set the login URL to point to the frontend login page instead of Django's default
LOGIN_URL = '/api/v1/auth/login/'
LOGIN_REDIRECT_URL = '/'
