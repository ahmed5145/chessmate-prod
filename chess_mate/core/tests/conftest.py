"""
Pytest configuration for Django tests.

This file provides fixtures for Django-integrated tests.
"""

import os
import sys

import django
import pytest

# Add the project root to the path for relative imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Try to configure Django for testing
try:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chess_mate.test_settings")
    django.setup()
except ImportError:
    pass


# Only import Django components when not in standalone mode
def pytest_configure(config):
    """Configure test environment based on mode."""
    is_standalone = any(x.startswith("-p") and "no:django" in x for x in config.invocation_params.args)
    if is_standalone:
        # Skip Django imports
        return

    # Import Django components when not in standalone mode
    global Client, User, TestCase
    from django.contrib.auth.models import User
    from django.test import Client, TestCase


# Django test fixtures - only available when not in standalone mode
@pytest.fixture
def client():
    """Django test client."""
    from django.test import Client

    return Client()


@pytest.fixture
def django_user_model():
    """Django User model."""
    from django.contrib.auth.models import User

    return User


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


# Define TestCase at module level when not in standalone mode
def pytest_sessionstart(session):
    """Set up TestCase when session starts."""
    try:
        from django.test import TestCase

        globals()["TestCase"] = TestCase
    except ImportError:
        pass


# Model fixtures - these depend on models being properly imported
try:
    from chess_mate.core.models import Game, Profile

    @pytest.fixture
    def test_game(db, test_user):
        """Create a test game."""
        return Game.objects.create(
            user=test_user,
            platform="lichess",
            white="testuser",
            black="opponent",
            pgn='[Event "Test Game"]\n[Site "https://lichess.org"]\n[White "testuser"]\n[Black "opponent"]\n[Result "1-0"]\n\n1.e4 e5 2.Nf3 Nc6 3.Bb5 a6 4.Ba4 Nf6 5.O-O Be7 6.d3 d6 7.c3 O-O 8.Re1 Nb8 9.Nbd2 Nbd7 10.Nf1 c6 11.Bc2 Qc7 12.Ng3 Re8 13.d4 Bf8 14.Nh4 g6 15.f4 Bg7 16.f5 1-0',
            result="1-0",
        )

    @pytest.fixture
    def test_profile(db, test_user):
        """Create a test profile."""
        return Profile.objects.create(user=test_user, chess_com_username="testuser", lichess_username="testuser")

except (ImportError, ModuleNotFoundError):
    # If models cannot be imported, create dummy fixtures
    @pytest.fixture
    def test_game(db, test_user):
        """Dummy test game fixture."""
        return None

    @pytest.fixture
    def test_profile(db, test_user):
        """Dummy test profile fixture."""
        return None
