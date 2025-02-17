"""
Test settings for the ChessMate project.
"""

from .settings import *

# Test database settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'test_chessmate',
        'USER': 'postgres',
        'PASSWORD': 'admin',
        'HOST': 'localhost',
        'PORT': '5432',
        'ATOMIC_REQUESTS': True,
        'CONN_MAX_AGE': None,  # Keep connections alive
        'OPTIONS': {
            'client_encoding': 'UTF8',
            'connect_timeout': 10,
            'sslmode': 'disable',
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5
        },
        'TEST': {
            'NAME': 'test_chessmate',
            'SERIALIZE': False,
            'MIRROR': None,
            'DEPENDENCIES': []
        }
    }
}

# Test-specific settings
DEBUG = False
TESTING = True

# Disable Redis for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Use fast password hasher for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable celery during tests
CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

# Use in-memory cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Disable migrations for tests
# class DisableMigrations:
#     def __contains__(self, item):
#         return True
#     def __getitem__(self, item):
#         return None

# MIGRATION_MODULES = DisableMigrations()

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
    },
    'formatters': {
        'verbose': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'core': {
            'handlers': ['console'],
            'level': 'DEBUG',
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