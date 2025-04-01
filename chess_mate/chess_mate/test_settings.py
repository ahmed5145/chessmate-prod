"""
Test settings for the ChessMate project.
"""

from .settings import *

# Test database settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # Use in-memory database for tests
    }
}

# Test-specific settings
DEBUG = False
TESTING = True

# Celery test settings
CELERY_TASK_ALWAYS_EAGER = True  # Execute tasks synchronously
CELERY_TASK_EAGER_PROPAGATES = True  # Propagate exceptions
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache'
CELERY_CACHE_BACKEND = 'memory'

# Disable Redis for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    },
    'local': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'local-memory',
    }
}

# Use fast password hasher for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable celery during tests
CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

# Disable migrations for tests
class DisableMigrations:
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Disable Redis rate limiting for tests
RATE_LIMIT_BACKEND = 'django.core.cache.backends.locmem.LocMemCache'

# Test-specific logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'formatters': {
        'verbose': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['null'],
            'level': 'WARNING',
            'propagate': False,
        },
        'core': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'celery': {
            'handlers': ['null'],
            'level': 'WARNING',
            'propagate': False,
        },
    }
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
warnings.filterwarnings('ignore', category=RemovedInDjango60Warning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

# OpenAI Settings
OPENAI_API_KEY = 'test-key'
USE_OPENAI = True  # Enable OpenAI for tests
OPENAI_MODEL = 'gpt-3.5-turbo'
OPENAI_MAX_TOKENS = 500
OPENAI_TEMPERATURE = 0.7

# Redis settings for testing
REDIS_URL = None  # Disable Redis for testing
USE_REDIS = False

# Rate limiting settings
RATE_LIMIT = {
    'DEFAULT': {
        'MAX_REQUESTS': 100,
        'TIME_WINDOW': 60,
    },
    'AUTH': {
        'MAX_REQUESTS': 5,
        'TIME_WINDOW': 300,
    },
    'ANALYSIS': {
        'MAX_REQUESTS': 10,
        'TIME_WINDOW': 600,
    }
} 