"""Production settings for ChessMate."""
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from .settings import *  # noqa
from .logging import LOGGING  # Import logging configuration

# Debug should be False in production
DEBUG = False

# Security Settings
SECURE_SSL_REDIRECT = False  # Change to True when you add SSL
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = False  # Change to True when you add SSL
CSRF_COOKIE_SECURE = False  # Change to True when you add SSL
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

ALLOWED_HOSTS = ['3.133.97.72', 'ec2-3-133-97-72.us-east-2.compute.amazonaws.com']

# CORS Settings
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "http://3.133.97.72",
    "http://ec2-3-133-97-72.us-east-2.compute.amazonaws.com"
]

CSRF_TRUSTED_ORIGINS = [
    "http://3.133.97.72",
    "http://ec2-3-133-97-72.us-east-2.compute.amazonaws.com"
]

# Static and Media Files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Redis Settings
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "RETRY_ON_TIMEOUT": True,
            "MAX_CONNECTIONS": 1000,
            "IGNORE_EXCEPTIONS": True,
        },
        "KEY_PREFIX": "chessmate_prod"
    }
}

# Session Settings
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Email Settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL')

# Sentry Configuration
sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=True,
    environment=os.getenv('ENVIRONMENT', 'production'),
)

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'core': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Worker settings
WORKER_CONCURRENCY = int(os.getenv('WORKER_CONCURRENCY', '2'))
WORKER_TIMEOUT = int(os.getenv('WORKER_TIMEOUT', '600'))  # 10 minutes
WORKER_MAX_TASKS = int(os.getenv('WORKER_MAX_TASKS', '1000'))

# Telemetry Configuration
TELEMETRY_CONFIG = {
    'ENABLED': True,
    'SAMPLE_RATE': 1.0,  # Sample 100% of requests
    'SLOW_REQUEST_THRESHOLD': 1.0,  # seconds
    'EXCLUDED_PATHS': [
        '/health/',
        '/metrics/',
        '/static/',
        '/media/',
        '/favicon.ico'
    ],
    'EXPORTERS': ['prometheus', 'json', 'log']
}

# Add TelemetryMiddleware to MIDDLEWARE
MIDDLEWARE = [
    'chess_mate.telemetry.middleware.TelemetryMiddleware',
    # ... existing middleware ...
]

# Prometheus metrics endpoint
if TELEMETRY_CONFIG['ENABLED']:
    PROMETHEUS_METRICS_EXPORT_PORT = 8000
    PROMETHEUS_METRICS_EXPORT_ADDRESS = ''  # Listen on all addresses 