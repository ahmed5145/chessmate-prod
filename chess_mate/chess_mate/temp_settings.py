from chess_mate.settings import *

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

# Disable Redis for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    },
    'local': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'local-memory',
    },
    'redis': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Redis settings for testing
REDIS_URL = 'redis://localhost:6379/0'
USE_REDIS = True

# Rate limiting settings
RATE_LIMIT_CONFIG = {
    'DEFAULT': {
        'MAX_REQUESTS': 100,
        'TIME_WINDOW': 3600,
    },
    'ANALYSIS': {
        'MAX_REQUESTS': 50,
        'TIME_WINDOW': 3600,
    },
    'LOGIN': {
        'MAX_REQUESTS': 5,
        'TIME_WINDOW': 300,
    }
}

STOCKFISH_PATH = 'C:/Users/PCAdmin/Downloads/stockfish-windows-x86-64-avx2/stockfish/stockfish-windows-x86-64-avx2.exe'
OPENAI_API_KEY = 'dummy-key' 