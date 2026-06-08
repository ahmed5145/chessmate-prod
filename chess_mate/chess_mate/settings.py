"""
Django settings for chess_mate project.
"""

import os
from datetime import timedelta
from pathlib import Path

import environ  # type: ignore
from django.core.exceptions import ImproperlyConfigured
from dotenv import dotenv_values, load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

# Initialize environ
env = environ.Env()

# Read .env files in precedence order so local overrides win while preserving
# any values already present in the process environment.
environment_name = os.environ.get("ENVIRONMENT", "development")
env_files = [
    os.path.join(PROJECT_ROOT, f".env.{environment_name}.local"),
    os.path.join(PROJECT_ROOT, ".env.local"),
    os.path.join(PROJECT_ROOT, f".env.{environment_name}"),
    os.path.join(PROJECT_ROOT, ".env"),
]
for env_file in env_files:
    if os.path.exists(env_file):
        # Load with python-dotenv first (preserve existing non-empty env vars),
        # then also load via django-environ so `env()` and `os.environ` are
        # consistently populated (django-environ writes into os.environ).
        load_dotenv(env_file, override=False)
        try:
            environ.Env.read_env(env_file)
        except Exception:
            # If django-environ fails to read, keep going — load_dotenv already ran.
            pass

# Testing mode flag - must be defined before any dependent settings
TESTING: bool = env("TESTING", default="False").lower() == "true"

# Environment detection
ENVIRONMENT = env("ENVIRONMENT", default="development")
IS_PRODUCTION = ENVIRONMENT.lower() == "production"

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
if IS_PRODUCTION and not TESTING:
    SECRET_KEY = env("SECRET_KEY", default="").strip()
    if not SECRET_KEY or SECRET_KEY.startswith("django-insecure"):
        raise ImproperlyConfigured("SECRET_KEY must be set to a strong value when ENVIRONMENT=production")
else:
    SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-only-change-me")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=False)

# OpenAI Settings
OPENAI_API_KEY = env("OPENAI_API_KEY", default="").strip()
if not OPENAI_API_KEY:
    for fallback_file in (
        os.path.join(PROJECT_ROOT, ".env.prod"),
        os.path.join(PROJECT_ROOT, ".env.production"),
    ):
        if os.path.exists(fallback_file):
            fallback_key = (dotenv_values(fallback_file).get("OPENAI_API_KEY") or "").strip()
            if fallback_key:
                OPENAI_API_KEY = fallback_key
                break
USE_OPENAI = bool(OPENAI_API_KEY)
OPENAI_MODEL = "gpt-3.5-turbo"
OPENAI_MAX_TOKENS = 500
OPENAI_TEMPERATURE = 0.7
OPENAI_RATE_LIMIT = {
    "max_requests": 100 if env("TEST_MODE", default="False").lower() == "true" else 50,
    "window_seconds": (60 if env("TEST_MODE", default="False").lower() == "true" else 3600),
    "min_interval": 0.1 if env("TEST_MODE", default="False").lower() == "true" else 0.5,
}
OPENAI_CACHE_KEY = "openai_rate_limit"
OPENAI_CACHE_TIMEOUT = 3600

# Stripe Settings
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=[
        "localhost",
        "127.0.0.1",
    ],
)
for host in [
    "chessmate-prod.us-east-2.elasticbeanstalk.com",
    "*",
]:
    if host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)

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
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.admin_security.AdminSecurityMiddleware",
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
            os.path.join(BASE_DIR, "templates"),
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
            "NAME": env("DB_NAME", default="chessmate"),
            "USER": env("DB_USER", default="postgres"),
            "PASSWORD": env("DB_PASSWORD", default=""),
            "HOST": env("DB_HOST", default="localhost"),
            "PORT": env("DB_PORT", default="5432"),
            "CONN_MAX_AGE": int(env("DB_CONN_MAX_AGE", default="300")),  # 5 minutes persistent connection
            "OPTIONS": {
                "connect_timeout": 10,  # Reduced timeout for faster error detection
                "client_encoding": "UTF8",
                "application_name": "ChessMate",  # Identify the application in PostgreSQL logs
                # Keepalive settings to detect and prevent stale connections
                "keepalives": 1,
                "keepalives_idle": 60,  # After 60s of inactivity, send keepalive
                "keepalives_interval": 10,  # Retry every 10s
                "keepalives_count": 5,  # Drop after 5 failed attempts
                # Performance optimizations: set as session options via libpq `options`
                # Use environment variables so these can be tuned without code changes.
                "options": " ".join(
                    filter(
                        None,
                        [
                            f"-c statement_timeout={int(env('DB_STATEMENT_TIMEOUT', default='30000'))}",
                            f"-c work_mem={int(env('DB_WORK_MEM', default='16'))}MB",
                            f"-c maintenance_work_mem={int(env('DB_MAINTENANCE_MEM', default='64'))}MB",
                            f"-c effective_cache_size={int(env('DB_CACHE_SIZE', default='4096'))}MB",
                        ],
                    )
                ),
            },
            # Connection pooling settings
            "POOL_OPTIONS": {
                "POOL_SIZE": int(env("DB_POOL_SIZE", default="20")),  # Increased pool size for higher concurrency
                "MAX_OVERFLOW": int(env("DB_MAX_OVERFLOW", default="30")),  # Allow more overflow connections under load
                "RECYCLE": int(env("DB_RECYCLE_SECONDS", default="300")),  # Recycle connections after 5 minutes
                "TIMEOUT": int(env("DB_POOL_TIMEOUT", default="30")),  # Timeout for acquiring connection from pool
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
        "max_overflow": int(env("DB_MAX_OVERFLOW", default="30")),
        "pool_size": int(env("DB_POOL_SIZE", default="20")),
        "recycle": int(env("DB_RECYCLE_SECONDS", default="300")),
        "retry_on_timeout": True,
        "max_retries": 3,
        "retry_delay": 0.1,
        "timeout": int(env("DB_POOL_TIMEOUT", default="30")),
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
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "frontend", "build", "static"),
]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
# CRA build assets (favicon, manifest) live outside frontend/build/static
WHITENOISE_ROOT = os.path.join(BASE_DIR, "frontend", "build")
WHITENOISE_INDEX_FILE = False  # SPA routes use spa_index view, not root index.html
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

# Media files configuration
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Redis settings
REDIS_HOST = os.getenv("REDIS_HOST", "localhost").strip()
REDIS_DISABLED = os.getenv("REDIS_DISABLED", "False").lower() == "true"
# EB/Docker without ElastiCache: avoid connecting to localhost:6379 in production
if (
    not REDIS_DISABLED
    and IS_PRODUCTION
    and REDIS_HOST in ("localhost", "127.0.0.1")
    and not os.getenv("REDIS_URL", "").strip()
):
    REDIS_DISABLED = True
REDIS_PORT = os.getenv("REDIS_PORT", "6379").strip()
REDIS_DB = os.getenv("REDIS_DB", "0").strip()
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "").strip()

_env_redis_url = os.getenv("REDIS_URL", "").strip()
if _env_redis_url:
    REDIS_URL = _env_redis_url
elif REDIS_PASSWORD:
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

REDIS_SOCKET_TIMEOUT = int(env("REDIS_SOCKET_TIMEOUT", default=5))
REDIS_SOCKET_CONNECT_TIMEOUT = int(env("REDIS_SOCKET_CONNECT_TIMEOUT", default=5))
REDIS_RETRY_ON_TIMEOUT = env("REDIS_RETRY_ON_TIMEOUT", default="true").lower() == "true"
REDIS_CONNECTION_POOL_SIZE = int(env("REDIS_CONNECTION_POOL_SIZE", default=20))
REDIS_MAX_CONNECTIONS = int(env("REDIS_MAX_CONNECTIONS", default=100))

# Basic REST Framework Configuration without imports that might cause circular dependencies
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": (
        ("rest_framework.renderers.JSONRenderer",)
        if not DEBUG
        else (
            "rest_framework.renderers.JSONRenderer",
            "rest_framework.renderers.BrowsableAPIRenderer",
        )
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# The rest of the REST_FRAMEWORK configuration will be set up during application initialization
# in chess_mate/core/apps.py to avoid circular imports

# Cache settings - use local memory when Redis is disabled
if REDIS_DISABLED:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "chessmate-default",
            "TIMEOUT": 300,
            "OPTIONS": {"MAX_ENTRIES": 1000, "CULL_FREQUENCY": 3},
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
            "TIMEOUT": 300,
        },
        # Legacy alias used by core.cache (CACHE_BACKEND_REDIS)
        "redis": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
            "TIMEOUT": 300,
        },
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

# Rate Limiting Settings (middleware — per IP + per user when authenticated)
RATE_LIMIT = {
    "DEFAULT": {"MAX_REQUESTS": 120, "TIME_WINDOW": 60, "BACKEND": "default"},
    "AUTH": {"MAX_REQUESTS": 15, "TIME_WINDOW": 60, "BACKEND": "default"},
    "ANALYSIS": {"MAX_REQUESTS": 8, "TIME_WINDOW": 60, "BACKEND": "default"},
    "FETCH": {"MAX_REQUESTS": 6, "TIME_WINDOW": 60, "BACKEND": "default"},
    "CREDITS": {"MAX_REQUESTS": 5, "TIME_WINDOW": 300, "BACKEND": "default"},
    "BATCH_OPS": {"MAX_REQUESTS": 3, "TIME_WINDOW": 300, "BACKEND": "default"},
    "PUBLIC": {"MAX_REQUESTS": 60, "TIME_WINDOW": 60, "BACKEND": "default"},
    "GAMES": {"MAX_REQUESTS": 40, "TIME_WINDOW": 60, "BACKEND": "default"},
}

RATE_LIMIT_BACKEND = "default"  # Use Redis cache for rate limiting

RATE_LIMIT_EXCLUDED_PATHS = [
    r"^/api/health/?$",
    r"^/api(?:/v1)?/health/",
    r"^/api(?:/v1)?/webhooks/",
    r"^/api(?:/v1)?/profile/webhook/",
]

RATE_LIMIT_ENDPOINT_PATTERNS = {
    "AUTH": [
        r"^/api(?:/v1)?/auth/(?:register|login|logout|token/refresh|reset-password|csrf)/?$",
        r"^/api(?:/v1)?/auth/reset-password/",
        r"^/api(?:/v1)?/(?:register|login|token/refresh)/?$",
    ],
    "FETCH": [
        r"^/api(?:/v1)?/games/(?:fetch|import|import/external)/?$",
        r"^/api(?:/v1)?/games/search/?$",
    ],
    "ANALYSIS": [
        r"^/api(?:/v1)?/games/\d+/analyze/?$",
        r"^/api(?:/v1)?/analysis/.*/?$",
        r"^/api(?:/v1)?/batches/?$",
        r"^/api(?:/v1)?/games/batch-analyze/?$",
    ],
    "BATCH_OPS": [
        r"^/api(?:/v1)?/batches/\d+/regenerate-coaching/?$",
    ],
    "CREDITS": [
        r"^/api(?:/v1)?/(?:purchase-credits|credits/purchase|confirm-purchase|credits/confirm)/?$",
        r"^/api(?:/v1)?/profile/credits/purchase/?$",
    ],
    "PUBLIC": [
        r"^/api(?:/v1)?/public/",
        r"^/api(?:/v1)?/batches/public/",
    ],
    "GAMES": [
        r"^/api(?:/v1)?/games/user/?$",
        r"^/api(?:/v1)?/games/\d+/(?:analysis|analysis/status)/?$",
        r"^/api(?:/v1)?/games/batch-(?:status|reports)/",
    ],
    "DEFAULT": [r"^/api/"],
}

# Abuse caps (business logic — see core/abuse_limits.py)
SIGNUP_RATE_LIMIT_MAX_PER_IP = env.int("SIGNUP_RATE_LIMIT_MAX_PER_IP", default=5)
SIGNUP_RATE_LIMIT_WINDOW_SECONDS = env.int("SIGNUP_RATE_LIMIT_WINDOW_SECONDS", default=3600)
LOGIN_FAILED_MAX_PER_IP = env.int("LOGIN_FAILED_MAX_PER_IP", default=20)
LOGIN_FAILED_WINDOW_SECONDS = env.int("LOGIN_FAILED_WINDOW_SECONDS", default=3600)
PASSWORD_RESET_MAX_PER_IP = env.int("PASSWORD_RESET_MAX_PER_IP", default=5)
PASSWORD_RESET_WINDOW_SECONDS = env.int("PASSWORD_RESET_WINDOW_SECONDS", default=3600)
PASSWORD_RESET_MAX_PER_EMAIL = env.int("PASSWORD_RESET_MAX_PER_EMAIL", default=3)
PASSWORD_RESET_EMAIL_WINDOW_SECONDS = env.int("PASSWORD_RESET_EMAIL_WINDOW_SECONDS", default=86400)
MAX_BATCHES_PER_USER_PER_DAY = env.int("MAX_BATCHES_PER_USER_PER_DAY", default=3)
ALLOW_CONCURRENT_BATCHES = env.bool("ALLOW_CONCURRENT_BATCHES", default=False)
MAX_GAME_IMPORTS_PER_USER_PER_DAY = env.int("MAX_GAME_IMPORTS_PER_USER_PER_DAY", default=100)
MAX_EXTERNAL_FETCH_REQUESTS_PER_USER_PER_DAY = env.int("MAX_EXTERNAL_FETCH_REQUESTS_PER_USER_PER_DAY", default=30)
MAX_SINGLE_ANALYSES_PER_USER_PER_DAY = env.int("MAX_SINGLE_ANALYSES_PER_USER_PER_DAY", default=50)
MAX_COACHING_REGENERATIONS_PER_USER_PER_DAY = env.int("MAX_COACHING_REGENERATIONS_PER_USER_PER_DAY", default=10)
MAX_COACHING_REGENERATIONS_PER_BATCH_PER_DAY = env.int("MAX_COACHING_REGENERATIONS_PER_BATCH_PER_DAY", default=3)
MAX_CHECKOUT_SESSIONS_PER_USER_PER_HOUR = env.int("MAX_CHECKOUT_SESSIONS_PER_USER_PER_HOUR", default=10)

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
ANALYSIS_COST = int(env("ANALYSIS_COST", default=5))  # Credits per analysis
ANALYSIS_DEPTH = int(env("ANALYSIS_DEPTH", default=20))  # Stockfish analysis depth
ANALYSIS_MOVE_TIME = int(env("ANALYSIS_MOVE_TIME", default=100))  # ms per move for Stockfish
MAX_POSITIONS_PER_GAME = int(env("MAX_POSITIONS_PER_GAME", default=300))  # Max positions to analyze per game

# Batch coach (launch product) — depth is internal only, not user-facing
BATCH_MIN_GAMES = env.int("BATCH_MIN_GAMES", default=5)
BATCH_MAX_GAMES = env.int("BATCH_MAX_GAMES", default=30)
BATCH_DEFAULT_GAMES = env.int("BATCH_DEFAULT_GAMES", default=10)
# Batch analysis is included for imported games; credits are charged on import (1/game).
BATCH_CREDITS_PER_GAME = env.int("BATCH_CREDITS_PER_GAME", default=0)
BATCH_ANALYSIS_DEPTH = env.int("BATCH_ANALYSIS_DEPTH", default=14)
BATCH_SEND_COMPLETE_EMAIL = env.bool("BATCH_SEND_COMPLETE_EMAIL", default=True)
# User-facing ETA hints (sequential Stockfish @ depth 14)
BATCH_ETA_MINUTES_PER_GAME_LOW = env.int("BATCH_ETA_MINUTES_PER_GAME_LOW", default=3)
BATCH_ETA_MINUTES_PER_GAME_HIGH = env.int("BATCH_ETA_MINUTES_PER_GAME_HIGH", default=5)
BATCH_ETA_COACHING_BUFFER_MINUTES = env.int("BATCH_ETA_COACHING_BUFFER_MINUTES", default=2)

# Use our custom Redis client
REDIS_CLIENT_CLASS = "chess_mate.core.redis_config.get_redis_client"

# Stockfish settings
STOCKFISH_PATH = env(
    "STOCKFISH_PATH",
    default=r"C:\Users\PCAdmin\Downloads\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe",
)  # Needs to be changed in prod
STOCKFISH_THREADS = int(env("STOCKFISH_THREADS", default=4))
STOCKFISH_HASH_SIZE = int(env("STOCKFISH_HASH_SIZE", default=128))  # MB

# Security configuration
# ALB terminates TLS and forwards HTTP to instances with X-Forwarded-Proto: https
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
# ELB/Beanstalk health checks hit HTTP /health/ — must not 301 or instances go unhealthy (502s).
SECURE_REDIRECT_EXEMPT = [r"^health/?$", r"^readiness/?$"]
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)
SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", default="31536000" if IS_PRODUCTION else "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=IS_PRODUCTION)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=IS_PRODUCTION)

# CSRF Configuration
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
    "https://chess-mate.online",
    "https://www.chess-mate.online",
    "https://chessmate-prod.us-east-2.elasticbeanstalk.com",
]
_env_csrf = env("CSRF_TRUSTED_ORIGINS", default="")
if _env_csrf:
    CSRF_TRUSTED_ORIGINS.extend([u.strip() for u in _env_csrf.split(",") if u.strip()])
else:
    for _host in ALLOWED_HOSTS:
        if _host in ("*", "localhost", "127.0.0.1") or _host.startswith("127."):
            continue
        for _scheme in ("http", "https"):
            _origin = f"{_scheme}://{_host}"
            if _origin not in CSRF_TRUSTED_ORIGINS:
                CSRF_TRUSTED_ORIGINS.append(_origin)

# CORS Configuration
CORS_ALLOWED_ORIGINS = list(CSRF_TRUSTED_ORIGINS)
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = [
    "Content-Type",
    "X-CSRFToken",
    "X-Request-ID",
    "X-RateLimit-Remaining",
    "X-RateLimit-Reset",
]
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
    "cache-control",
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

# JWT refresh lifetimes for login "remember me" (session vs persistent)
JWT_REFRESH_TOKEN_LIFETIME_REMEMBER = timedelta(days=int(os.getenv("JWT_REFRESH_REMEMBER_DAYS", "30")))
JWT_REFRESH_TOKEN_LIFETIME_SESSION = timedelta(hours=int(os.getenv("JWT_REFRESH_SESSION_HOURS", "12")))

# JWT Settings (with improved security and compatibility)
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),  # Increased for testing
    "REFRESH_TOKEN_LIFETIME": JWT_REFRESH_TOKEN_LIFETIME_REMEMBER,
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
    "django.contrib.auth.backends.ModelBackend",
]

# Set the login URL to point to the frontend login page instead of Django's default
LOGIN_URL = "/api/v1/auth/login/"
LOGIN_REDIRECT_URL = "/"

# Email (EB sets EMAIL_* env vars; production uses chess_mate.settings, not settings_prod)
if IS_PRODUCTION:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
    EMAIL_PORT = env.int("EMAIL_PORT", default=587)
    EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
    EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
    DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER)
else:
    EMAIL_BACKEND = env(
        "EMAIL_BACKEND",
        default="django.core.mail.backends.console.EmailBackend",
    )
    EMAIL_HOST = env("EMAIL_HOST", default="localhost")
    EMAIL_PORT = env.int("EMAIL_PORT", default=587)
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
    EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
    DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@localhost")

# Password reset links in email (must match template copy)
PASSWORD_RESET_TIMEOUT = env.int("PASSWORD_RESET_TIMEOUT", default=60 * 60 * 24)  # 24 hours
FRONTEND_URL = env("FRONTEND_URL", default="")
PAYMENT_SUCCESS_URL = env("PAYMENT_SUCCESS_URL", default="")
PAYMENT_CANCEL_URL = env("PAYMENT_CANCEL_URL", default="")

# Beta launch — free credits on signup (1 credit = 1 imported game; batch coach included)
SIGNUP_BONUS_CREDITS = env.int("SIGNUP_BONUS_CREDITS", default=15)
# Optional public share token for /example/batch-report (live demo; falls back to static fixture)
DEMO_BATCH_SHARE_TOKEN = env("DEMO_BATCH_SHARE_TOKEN", default="").strip()
SINGLE_GAME_ANALYSIS_CREDITS = env.int("SINGLE_GAME_ANALYSIS_CREDITS", default=1)

# Legal pages — set LEGAL_ENTITY_NAME when incorporated (e.g. "ChessMate Inc.")
LEGAL_ENTITY_NAME = env("LEGAL_ENTITY_NAME", default="").strip()
LEGAL_ENTITY_JURISDICTION = env(
    "LEGAL_ENTITY_JURISDICTION",
    default="",
).strip()
LEGAL_ENTITY_ADDRESS = env("LEGAL_ENTITY_ADDRESS", default="").strip()
REQUIRE_EMAIL_VERIFICATION = env.bool("REQUIRE_EMAIL_VERIFICATION", default=not DEBUG)
SUPPORT_EMAIL = env("SUPPORT_EMAIL", default="support@chess-mate.online")

# Stripe Checkout success redirect must survive EB restarts; use DB sessions when Redis is off.
if IS_PRODUCTION and REDIS_DISABLED:
    SESSION_ENGINE = "django.contrib.sessions.backends.db"

# Django admin hardening (public production)
from core.admin_security import resolve_admin_path

try:
    DJANGO_ADMIN_PATH = resolve_admin_path(
        is_production=IS_PRODUCTION,
        testing=TESTING,
        configured=env("DJANGO_ADMIN_PATH", default="admin" if (not IS_PRODUCTION or TESTING) else ""),
    )
except ValueError as exc:
    raise ImproperlyConfigured(str(exc)) from exc

ADMIN_URL_PREFIX = f"/{DJANGO_ADMIN_PATH}/"
ADMIN_HIDE_LEGACY_PATH = env.bool("ADMIN_HIDE_LEGACY_PATH", default=IS_PRODUCTION and not TESTING)
ADMIN_ALLOWED_IPS = env.list("ADMIN_ALLOWED_IPS", default=[])
ADMIN_LOGIN_MAX_ATTEMPTS = env.int("ADMIN_LOGIN_MAX_ATTEMPTS", default=5)
ADMIN_LOGIN_WINDOW_SECONDS = env.int("ADMIN_LOGIN_WINDOW_SECONDS", default=900)
