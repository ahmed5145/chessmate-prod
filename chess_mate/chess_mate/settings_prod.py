"""
Production settings for ChessMate project.
"""

import os
from datetime import timedelta
from pathlib import Path
from typing import Optional

import sentry_sdk
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
from sentry_sdk.integrations.django import DjangoIntegration

# Load environment variables
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if not SECRET_KEY or SECRET_KEY.startswith("django-insecure"):
    raise ImproperlyConfigured("SECRET_KEY must be configured in production and cannot use insecure defaults")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Default allowed hosts for production. Prefer an explicit comma-separated
# `ALLOWED_HOSTS` environment variable (set in Elastic Beanstalk) to control
# hosts precisely. If not provided, fall back to a conservative list and
# always include the EB environment domain.
_env_allowed = os.getenv("ALLOWED_HOSTS", "").strip()
if _env_allowed:
    # Support comma-separated list in env var
    ALLOWED_HOSTS = [h.strip() for h in _env_allowed.split(",") if h.strip()]
else:
    ALLOWED_HOSTS = [
        "3.133.97.72",
        "ec2-3-133-97-72.us-east-2.compute.amazonaws.com",
        "localhost",
        "127.0.0.1",
        "chess-mate.online",
        "www.chess-mate.online",
        "chessmate.com",
        "www.chessmate.com",
        "api.chessmate.com",
    ]

# Ensure the Elastic Beanstalk environment domain is allowed
eb_host = "chessmate-prod.us-east-2.elasticbeanstalk.com"
if eb_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(eb_host)

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
    "core",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
]

# Security Settings
# Allow toggling HTTPS redirect via env var. Default to True in production.
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() == "true"
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "True").lower() == "true"
SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "True").lower() == "true"
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
# Only enable cookie security flags when HTTPS redirect is enabled (or explicit env)
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "").lower() == "true" or SECURE_SSL_REDIRECT
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "").lower() == "true" or SECURE_SSL_REDIRECT
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_HTTPONLY = True

# Internationalization
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-us"
USE_I18N = True
USE_TZ = True

# Session and CSRF settings
# Build CSRF_TRUSTED_ORIGINS from env or derive from ALLOWED_HOSTS so that
# HTTPS frontends (ALB/CloudFront) are accepted. Allow overriding via
# `CSRF_TRUSTED_ORIGINS` env var (comma-separated).
_env_csrf = os.getenv("CSRF_TRUSTED_ORIGINS", "").strip()
if _env_csrf:
    CSRF_TRUSTED_ORIGINS = [u.strip() for u in _env_csrf.split(",") if u.strip()]
else:
    CSRF_TRUSTED_ORIGINS = []
    scheme = "https" if SECURE_SSL_REDIRECT else "http"
    for host in ALLOWED_HOSTS:
        # skip localhost/internal addresses
        if host.startswith("localhost") or host.startswith("127."):
            continue
        CSRF_TRUSTED_ORIGINS.append(f"{scheme}://{host}")

# Ensure core app is in INSTALLED_APPS
if "core" not in INSTALLED_APPS:
    INSTALLED_APPS = ["core"] + list(INSTALLED_APPS)

# Add django-prometheus to INSTALLED_APPS
INSTALLED_APPS = [
    "django_prometheus",
] + INSTALLED_APPS

# Redis settings
# Prefer a single `REDIS_URL` if provided by the environment (Elastic Beanstalk can set that).
# If `REDIS_URL` is not present, build one from the individual REDIS_HOST/PORT/DB/USERNAME/PASSWORD vars.
_env_redis_url = os.getenv("REDIS_URL")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = os.getenv("REDIS_DB", "0")
REDIS_USERNAME = os.getenv("REDIS_USERNAME", "")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
if _env_redis_url and _env_redis_url.strip():
    REDIS_URL = _env_redis_url
else:
    # Construct a URL safely; include username/password only when provided
    auth = ""
    if REDIS_USERNAME:
        auth = REDIS_USERNAME
        if REDIS_PASSWORD:
            auth = f"{REDIS_USERNAME}:{REDIS_PASSWORD}"
        auth = auth + "@"
    elif REDIS_PASSWORD:
        # Uncommon, but handle password without username
        auth = f":{REDIS_PASSWORD}@"

    REDIS_URL = f"redis://{auth}{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Cache settings
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "RETRY_ON_TIMEOUT": True,
            "MAX_CONNECTIONS": 20,
            "CONNECTION_POOL_KWARGS": {"max_connections": 10},
            "KEY_PREFIX": "cm",
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "SERIALIZER": "django_redis.serializers.json.JSONSerializer",
        },
    },
    "local": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "chessmate-local",
        "TIMEOUT": 300,
        "OPTIONS": {"MAX_ENTRIES": 1000},
    },
}

# Session settings - use database instead of cache
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# Cache time to live settings
CACHE_TTL = 3600  # 1 hour default

# Rate Limiting Settings - use local memory cache
RATE_LIMIT_BACKEND = "local"  # Use local memory cache for rate limiting

# Middleware configuration
MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

# Celery Configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
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

# JWT settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
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
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=30),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
}

# CORS settings
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://3.133.97.72",
    "http://ec2-3-133-97-72.us-east-2.compute.amazonaws.com",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "capacitor://localhost",
    "http://localhost",
    "ionic://localhost",
]

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
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
]

# CSRF settings
CSRF_COOKIE_SAMESITE = "None"  # Required for mobile apps
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript access
CSRF_USE_SESSIONS = False  # Use cookie-based CSRF
CSRF_COOKIE_NAME = "csrftoken"
CSRF_HEADER_NAME = "HTTP_X_CSRFTOKEN"
CSRF_COOKIE_AGE: Optional[int] = None  # Session length
CSRF_FAILURE_VIEW = "django.views.csrf.csrf_failure"

# Static and Media Files
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "frontend", "build", "static"),
]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
WHITENOISE_ROOT = os.path.join(BASE_DIR, "frontend", "build")
WHITENOISE_INDEX_FILE = False
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# Email Settings
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)

# Sentry Configuration
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=True,
    environment=os.getenv("ENVIRONMENT", "production"),
)

# Logging Configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "logs/django.log",
            "formatter": "verbose",
        },
    },
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "core": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Worker settings
WORKER_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "2"))
WORKER_TIMEOUT = int(os.getenv("WORKER_TIMEOUT", "600"))  # 10 minutes
WORKER_MAX_TASKS = int(os.getenv("WORKER_MAX_TASKS", "1000"))

# AI Feedback Settings
AI_FEEDBACK_RATE_LIMIT_MAX_REQUESTS = int(os.getenv("AI_FEEDBACK_RATE_LIMIT_MAX_REQUESTS", "100"))  # requests
AI_FEEDBACK_RATE_LIMIT_WINDOW = int(os.getenv("AI_FEEDBACK_RATE_LIMIT_WINDOW", "3600"))  # seconds
AI_FEEDBACK_CACHE_TTL = int(os.getenv("AI_FEEDBACK_CACHE_TTL", "86400"))  # 24 hours

# Test Mode Configuration
TEST_MODE = os.getenv("TEST_MODE", "False").lower() == "true"

# OpenAI Settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_OPENAI = bool(OPENAI_API_KEY)  # Enable OpenAI if API key is present
OPENAI_MODEL = "gpt-3.5-turbo"
OPENAI_MAX_TOKENS = 500
OPENAI_TEMPERATURE = 0.7
OPENAI_RATE_LIMIT = {
    "max_requests": 100 if os.getenv("TEST_MODE", "False").lower() == "true" else 50,
    "window_seconds": 60 if os.getenv("TEST_MODE", "False").lower() == "true" else 3600,
    "min_interval": 0.1 if os.getenv("TEST_MODE", "False").lower() == "true" else 0.5,
}
OPENAI_CACHE_KEY = "openai_rate_limit"
OPENAI_CACHE_TIMEOUT = 3600

# Stockfish Settings
STOCKFISH_PATH = os.getenv("STOCKFISH_PATH", "/usr/games/stockfish")
STOCKFISH_DEPTH = int(os.getenv("STOCKFISH_DEPTH", "20"))
STOCKFISH_THREADS = int(os.getenv("STOCKFISH_THREADS", "2"))
STOCKFISH_HASH_SIZE = int(os.getenv("STOCKFISH_HASH_SIZE", "128"))
STOCKFISH_CONTEMPT = int(os.getenv("STOCKFISH_CONTEMPT", "0"))
STOCKFISH_MIN_THINK_TIME = int(os.getenv("STOCKFISH_MIN_THINK_TIME", "20"))
STOCKFISH_SKILL_LEVEL = int(os.getenv("STOCKFISH_SKILL_LEVEL", "20"))

# Analysis Settings
MAX_ANALYSIS_TIME = int(os.getenv("MAX_ANALYSIS_TIME", "300"))  # seconds
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "10"))  # games
ANALYSIS_CACHE_TTL = int(os.getenv("ANALYSIS_CACHE_TTL", "86400"))  # 24 hours

# Database configuration for RDS
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "chessmate_prod"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": 0,  # Disable persistent connections
        "OPTIONS": {
            "connect_timeout": 30,
            "client_encoding": "UTF8",
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
            "sslmode": "require" if not DEBUG else "prefer",
        },
    }
}
