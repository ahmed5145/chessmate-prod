"""
Django settings for chess_mate project.
"""
import os
from datetime import timedelta
from pathlib import Path
from typing import Union
from dotenv import load_dotenv
from .logging_config import LOGGING
import platform

# Load environment variables first
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Testing mode flag - must be defined before any dependent settings
TESTING: bool = os.environ.get('TESTING', 'False').lower() == 'true'

# Quick-start development settings - unsuitable for production
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-key-for-dev')
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

# OpenAI Settings
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
USE_OPENAI = bool(OPENAI_API_KEY)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = 'gpt-3.5-turbo'
OPENAI_MAX_TOKENS = 500
OPENAI_TEMPERATURE = 0.7
OPENAI_RATE_LIMIT = {
    'max_requests': 100 if os.getenv('TEST_MODE', 'False').lower() == 'true' else 50,
    'window_seconds': 60 if os.getenv('TEST_MODE', 'False').lower() == 'true' else 3600,
    'min_interval': 0.1 if os.getenv('TEST_MODE', 'False').lower() == 'true' else 0.5,
}
OPENAI_CACHE_KEY = 'openai_rate_limit'
OPENAI_CACHE_TIMEOUT = 3600


ALLOWED_HOSTS = [
    '3.133.97.72',
    'localhost',
    '127.0.0.1',
    'web',
    'ec2-3-133-97-72.us-east-2.compute.amazonaws.com'
]

# Application definition
INSTALLED_APPS = [
    'corsheaders',  # Must be at the top
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'core',
    "rest_framework_simplejwt",
    'rest_framework_simplejwt.token_blacklist',
]

MIDDLEWARE = [
    'core.middleware.RequestIDMiddleware',  # Add request ID to each request
    'corsheaders.middleware.CorsMiddleware',  # Must be first
    'django.middleware.common.CommonMiddleware',  # Must be right after CORS
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.RequestValidationMiddleware',  # New validation middleware
    'core.middleware.RateLimitMiddleware',  # Add rate limiting middleware
]

ROOT_URLCONF = 'chess_mate.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'frontend', 'build'),
            os.path.join(BASE_DIR, 'core', 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'chess_mate.wsgi.application'

# Database configuration
if TESTING:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'chessmate'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
            'CONN_MAX_AGE': 0,  # Disable persistent connections
            'OPTIONS': {
                'connect_timeout': 30,  # Increase timeout to 30 seconds
                'client_encoding': 'UTF8',
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5
            },
        }
    }

# Connection age settings
CONN_MAX_AGE = 0  # Disable persistent connections for better reliability

# Database indexes
INDEXES = {
    'core.Game': {
        'fields': ['user', 'date_played', 'platform', 'result'],
    },
    'core.Profile': {
        'fields': ['user', 'rating'],
    },
    'core.GameAnalysis': {
        'fields': ['game', 'created_at'],
    },
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files configuration
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'frontend', 'build', 'static'),
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Redis settings
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Cache settings
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
    },
    'local': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
    }
}

# Analysis Cache TTL (24 hours)
ANALYSIS_CACHE_TTL = 86400

# Cache time to live is 15 minutes
CACHE_TTL = 60 * 15

# Rate Limiting Settings
RATE_LIMIT = {
    'DEFAULT': {
        'MAX_REQUESTS': 100,
        'TIME_WINDOW': 60,
        'BACKEND': 'local',  # Use the local Redis cache for rate limiting
    },
    'AUTH': {
        'MAX_REQUESTS': 5,
        'TIME_WINDOW': 60,
        'BACKEND': 'local',  # Use the local Redis cache for rate limiting
    },
    'ANALYSIS': {
        'MAX_REQUESTS': 3,
        'TIME_WINDOW': 60,
    },
    'CREDITS': {
        'MAX_REQUESTS': 5,
        'TIME_WINDOW': 60,
    },
    'GAMES': {
        'MAX_REQUESTS': 10,
        'TIME_WINDOW': 60,
    },
}

RATE_LIMIT_BACKEND = "local"  # Use local memory cache for rate limiting

# Logging Configuration
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Session settings
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# JWT settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=24),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# CORS Configuration
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOW_METHODS = [
        'DELETE',
        'GET',
        'OPTIONS',
        'PATCH',
        'POST',
        'PUT',
    ]
    CORS_ALLOW_HEADERS = [
        'accept',
        'accept-encoding',
        'authorization',
        'content-type',
        'dnt',
        'origin',
        'user-agent',
        'x-csrftoken',
        'x-requested-with',
    ]

# CSRF Configuration
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CSRF_USE_SESSIONS = False
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'None' if DEBUG else 'Lax'
CSRF_COOKIE_SECURE = not DEBUG

# Security settings for development
if DEBUG:
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = 'None'
    CSRF_COOKIE_SECURE = False

# Stockfish configuration
STOCKFISH_PATH = os.getenv('STOCKFISH_PATH', 'C:/Users/PCAdmin/Downloads/stockfish-windows-x86-64-avx2/stockfish/stockfish-windows-x86-64-avx2.exe')
STOCKFISH_DEPTH = int(os.getenv('STOCKFISH_DEPTH', '20'))
STOCKFISH_THREADS = int(os.getenv('STOCKFISH_THREADS', '2'))
STOCKFISH_HASH_SIZE = int(os.getenv('STOCKFISH_HASH_SIZE', '128'))
STOCKFISH_CONTEMPT = int(os.getenv('STOCKFISH_CONTEMPT', '0'))
STOCKFISH_MIN_THINK_TIME = int(os.getenv('STOCKFISH_MIN_THINK_TIME', '20'))
STOCKFISH_SKILL_LEVEL = int(os.getenv('STOCKFISH_SKILL_LEVEL', '20'))

# Analysis Settings
MAX_ANALYSIS_TIME = int(os.getenv('MAX_ANALYSIS_TIME', '300'))  # seconds
MAX_BATCH_SIZE = int(os.getenv('MAX_BATCH_SIZE', '10'))  # games
ANALYSIS_CACHE_TTL = int(os.getenv('ANALYSIS_CACHE_TTL', '86400'))  # 24 hours 
# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'EXCEPTION_HANDLER': 'core.error_handling.custom_exception_handler',
}

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@chessmate.com')

# Stripe Configuration
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
PAYMENT_SUCCESS_URL = os.getenv('PAYMENT_SUCCESS_URL', 'http://localhost:3000/payment/success')
PAYMENT_CANCEL_URL = os.getenv('PAYMENT_CANCEL_URL', 'http://localhost:3000/payment/cancel')

# Celery Configuration
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 3600
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Add the following rate limiting configuration settings

# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    'DEFAULT': {'MAX_REQUESTS': 100, 'TIME_WINDOW': 3600},  # 100 requests per hour
    'AUTH': {'MAX_REQUESTS': 20, 'TIME_WINDOW': 3600},      # 20 requests per hour
    'GAME': {'MAX_REQUESTS': 50, 'TIME_WINDOW': 3600},      # 50 requests per hour
    'ANALYSIS': {'MAX_REQUESTS': 30, 'TIME_WINDOW': 3600},  # 30 requests per hour
    'FEEDBACK': {'MAX_REQUESTS': 20, 'TIME_WINDOW': 3600},  # 20 requests per hour
    'PROFILE': {'MAX_REQUESTS': 60, 'TIME_WINDOW': 3600},   # 60 requests per hour
    'DASHBOARD': {'MAX_REQUESTS': 60, 'TIME_WINDOW': 3600}, # 60 requests per hour
}

# Rate limiting patterns for different endpoint types
RATE_LIMIT_PATTERNS = {
    'AUTH': [
        r'^/api/(register|login|logout|token/refresh|reset-password|verify-email)/?.*$',
    ],
    'GAME': [
        r'^/api/games/?$',
        r'^/api/games/fetch/?$',
    ],
    'ANALYSIS': [
        r'^/api/games/\d+/analyze/?$',
        r'^/api/games/\d+/analysis/?$',
        r'^/api/batch-analyze/?$',
    ],
    'FEEDBACK': [
        r'^/api/games/\d+/feedback/?$',
        r'^/api/feedback/.*$',
    ],
    'PROFILE': [
        r'^/api/profile/?.*$',
        r'^/api/subscription/?.*$',
        r'^/api/credits/?.*$',
    ],
    'DASHBOARD': [
        r'^/api/dashboard/?.*$',
    ],
}

# Paths excluded from rate limiting
RATE_LIMIT_EXCLUDED_PATHS = [
    r'^/api/health/?$',
    r'^/api/csrf/?$',
    r'^/api/docs/?.*$',
    r'^/api/version/?$',
]

# Use Redis for rate limiting if available
USE_REDIS = os.environ.get('USE_REDIS', 'False').lower() == 'true'

# Cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'chessmate-cache',
    }
}

if USE_REDIS:
    CACHES['redis'] = {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
