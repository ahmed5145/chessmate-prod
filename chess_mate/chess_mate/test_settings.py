"""
Test settings for the ChessMate project.
These settings are used for running tests to ensure the environment is properly isolated.
"""

# Import base settings
from .settings import *

# Use an in-memory SQLite database for testing
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}


# Disable migrations during tests for speed
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

# Use a fast password hasher during tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Turn off debugging for tests
DEBUG = False

# Use a simple cache for testing
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Use test runner
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# Disable Celery during tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable debug mode for testing
DEBUG = False

# Configure Celery for testing
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable cache for testing
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    },
    "local": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    },
}

# Mock external service keys
OPENAI_API_KEY = "test-key"
STRIPE_SECRET_KEY = "test-stripe-secret-key"
STRIPE_PUBLIC_KEY = "test-stripe-public-key"
STOCKFISH_PATH = "/mock/path/to/stockfish"

# Use console email backend for testing
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Disable CSRF protection for testing API endpoints
MIDDLEWARE = [m for m in MIDDLEWARE if m != "django.middleware.csrf.CsrfViewMiddleware"]
# Make sure RequestIDMiddleware is first
if "core.middleware.RequestIDMiddleware" not in MIDDLEWARE:
    MIDDLEWARE.insert(0, "core.middleware.RequestIDMiddleware")
MIDDLEWARE.append("core.middleware.RequestValidationMiddleware")  # Add validation middleware for testing

# Reduce rate limiting for tests
RATE_LIMIT = {
    "DEFAULT": {
        "MAX_REQUESTS": 1000,
        "TIME_WINDOW": 60,
    },
    "AUTH": {
        "MAX_REQUESTS": 1000,
        "TIME_WINDOW": 60,
    },
    "ANALYSIS": {
        "MAX_REQUESTS": 1000,
        "TIME_WINDOW": 60,
    },
    "CREDITS": {
        "MAX_REQUESTS": 1000,
        "TIME_WINDOW": 60,
    },
    "GAMES": {
        "MAX_REQUESTS": 1000,
        "TIME_WINDOW": 60,
    },
}

# Override OPENAI settings for testing
OPENAI_RATE_LIMIT = {
    "max_requests": 1000,
    "window_seconds": 60,
    "min_interval": 0.01,
}

# Disable celery during tests
CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

# Disable Redis rate limiting for tests
RATE_LIMIT_BACKEND = "django.core.cache.backends.locmem.LocMemCache"

# Test-specific logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "formatters": {
        "verbose": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["null"],
            "level": "WARNING",
            "propagate": False,
        },
        "core": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "celery": {
            "handlers": ["null"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# Test-specific Stockfish settings
STOCKFISH_PATH = "C:/Program Files/Stockfish/stockfish/stockfish-windows-x86-64-avx2.exe"
STOCKFISH_THREADS = 1
STOCKFISH_HASH_SIZE = 32
STOCKFISH_SKILL_LEVEL = 20
STOCKFISH_MOVE_OVERHEAD = 30

# Silence Django deprecation warnings
import warnings

from django.utils.deprecation import RemovedInDjango60Warning

warnings.filterwarnings("ignore", category=RemovedInDjango60Warning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# OpenAI Settings
USE_OPENAI = True  # Enable OpenAI for tests
OPENAI_MODEL = "gpt-3.5-turbo"
OPENAI_MAX_TOKENS = 500
OPENAI_TEMPERATURE = 0.7

# Redis settings for testing
REDIS_URL = None  # Disable Redis for testing
USE_REDIS = False

# Rate limiting settings
RATE_LIMIT = {
    "DEFAULT": {
        "MAX_REQUESTS": 100,
        "TIME_WINDOW": 60,
    },
    "AUTH": {
        "MAX_REQUESTS": 5,
        "TIME_WINDOW": 300,
    },
    "ANALYSIS": {
        "MAX_REQUESTS": 10,
        "TIME_WINDOW": 600,
    },
}
