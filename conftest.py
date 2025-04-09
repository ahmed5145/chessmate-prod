"""
Unified pytest configuration for ChessMate project.

This file provides fixtures and configuration for both:
1. Standalone tests (no Django dependencies)
2. Django-integrated tests

The file automatically detects the test mode and configures the environment accordingly.
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Add the project root to the Python path for relative imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------------------------------------------------------------------------------
# Django Configuration
# -------------------------------------------------------------------------------


def pytest_configure(config):
    """Configure pytest based on command line options."""
    # Check if running standalone tests
    is_standalone = any(x.startswith("-p") and "no:django" in x for x in config.invocation_params.args)

    if is_standalone:
        print("Running in standalone mode without Django")
        return

    print("Setting up Django test environment")
    # Set up Django environment
    os.environ.setdefault("TESTING", "True")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chess_mate.test_settings")

    # Try to set up Django
    try:
        import django

        django.setup()
        from django.conf import settings

        # Apply migrations if needed
        if not getattr(settings, "DISABLE_MIGRATIONS_FOR_TESTS", False):
            print("Applying migrations for tests")
            from django.core.management import call_command

            call_command("migrate", "-v", "0")
    except ImportError:
        print("Django not available or PYTHONPATH not correctly set")
    except Exception as e:
        print(f"Error setting up Django: {str(e)}")


# -------------------------------------------------------------------------------
# Django-specific Fixtures (Only available when Django is active)
# -------------------------------------------------------------------------------


# Only define these fixtures when not in standalone mode
def pytest_sessionstart(session):
    """Set up Django TestCase when session starts."""
    # Check if we're running in Django mode
    if "django" not in session.config.pluginmanager.list_name_plugin():
        return

    try:
        # Import Django components
        from django.contrib.auth.models import User
        from django.test import Client, TestCase

        # Make them available globally
        globals()["TestCase"] = TestCase
        globals()["Client"] = Client
        globals()["User"] = User
    except ImportError:
        # Django not available
        pass


@pytest.fixture
def client():
    """Django test client."""
    try:
        from django.test import Client

        return Client()
    except ImportError:
        pytest.skip("Django not available")


@pytest.fixture
def django_user_model():
    """Django User model."""
    try:
        from django.contrib.auth.models import User

        return User
    except ImportError:
        pytest.skip("Django not available")


@pytest.fixture
def test_user(db, django_user_model):
    """Create a test user."""
    return django_user_model.objects.create_user(username="testuser", email="test@example.com", password="password123")


@pytest.fixture
def test_superuser(db, django_user_model):
    """Create a test superuser."""
    return django_user_model.objects.create_superuser(
        username="admin", email="admin@example.com", password="adminpass123"
    )


@pytest.fixture
def authenticated_client(client, test_user):
    """Client authenticated as a regular user."""
    client.force_login(test_user)
    return client


@pytest.fixture
def admin_client(client, test_superuser):
    """Client authenticated as an admin user."""
    client.force_login(test_superuser)
    return client


# Model fixtures - These are wrapped in try/except to handle standalone mode
@pytest.fixture
def test_game(db, test_user):
    """Create a test game."""
    try:
        from chess_mate.core.models import Game

        return Game.objects.create(
            user=test_user,
            platform="lichess",
            white="testuser",
            black="opponent",
            pgn='[Event "Test Game"]\n[Site "https://lichess.org"]\n[White "testuser"]\n[Black "opponent"]\n[Result "1-0"]\n\n1.e4 e5 2.Nf3 Nc6 3.Bb5 a6 4.Ba4 Nf6 5.O-O Be7 6.d3 d6 7.c3 O-O 8.Re1 Nb8 9.Nbd2 Nbd7 10.Nf1 c6 11.Bc2 Qc7 12.Ng3 Re8 13.d4 Bf8 14.Nh4 g6 15.f4 Bg7 16.f5 1-0',
            result="1-0",
        )
    except (ImportError, ModuleNotFoundError):
        pytest.skip("Game model not available")


@pytest.fixture
def test_profile(db, test_user):
    """Create a test profile."""
    try:
        from chess_mate.core.models import Profile

        return Profile.objects.create(user=test_user, chess_com_username="testuser", lichess_username="testuser")
    except (ImportError, ModuleNotFoundError):
        pytest.skip("Profile model not available")


# -------------------------------------------------------------------------------
# Universal Fixtures (Available in both modes)
# -------------------------------------------------------------------------------


@pytest.fixture(scope="session")
def redis_mock():
    """
    Provide a Redis mock for testing.
    """
    try:
        import fakeredis

        server = fakeredis.FakeServer()
        redis_client = fakeredis.FakeStrictRedis(server=server, decode_responses=True)

        # Clear all data before session
        redis_client.flushall()

        return redis_client
    except ImportError:
        pytest.skip("fakeredis not available")


@pytest.fixture
def cache_mock(redis_mock):
    """
    Provides a simple cache implementation using the Redis mock.
    """

    class SimpleCache:
        """A simple cache implementation for testing."""

        def __init__(self, redis_client):
            self.redis = redis_client
            self.default_ttl = 3600  # 1 hour

        def get(self, key, default=None):
            """Get a value from the cache."""
            data = self.redis.get(key)
            if data is None:
                return default

            # Handle JSON deserialization
            if isinstance(data, bytes):
                try:
                    return json.loads(data.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return data
            elif isinstance(data, str):
                try:
                    return json.loads(data)
                except (json.JSONDecodeError, TypeError):
                    return data
            return data

        def set(self, key, value, ttl=None):
            """Set a value in the cache with optional time-to-live."""
            if ttl is None:
                ttl = self.default_ttl

            # Convert complex types to JSON
            if not isinstance(value, (str, bytes, int, float, bool, type(None))):
                value = json.dumps(value)

            return self.redis.set(key, value, ex=ttl)

        def delete(self, key):
            """Delete a key from cache."""
            return self.redis.delete(key)

        def clear_all(self):
            """Clear all cache entries."""
            return self.redis.flushall()

        def get_by_pattern(self, pattern):
            """Get all keys matching a pattern."""
            keys = self.redis.keys(pattern)
            result = {}
            for key in keys:
                # Convert bytes key to string if needed
                key_str = key.decode("utf-8") if isinstance(key, bytes) else key
                result[key_str] = self.get(key)
            return result

    return SimpleCache(redis_mock)


@pytest.fixture
def mock_user():
    """Mock user fixture for testing."""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "is_active": True,
        "is_staff": False,
        "is_superuser": False,
    }


@pytest.fixture
def mock_game():
    """Mock game fixture for testing."""
    return {
        "id": 1,
        "user_id": 1,
        "pgn": '[Event "Test Game"]\n[White "Test User"]\n[Black "Opponent"]\n1. e4 e5 2. Nf3 Nc6',
        "result": "1-0",
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T01:00:00Z",
    }
