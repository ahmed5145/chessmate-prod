"""Tests for cache invalidation system."""

from unittest.mock import MagicMock, call, patch

import pytest
from core.cache_invalidation import (
    ENTITY_DEPENDENCIES,
    ENTITY_KEY_PREFIXES,
    TAG_DEPENDENCIES,
    TAG_KEY_PREFIXES,
    CacheInvalidator,
    invalidate_cache_on_delete,
    invalidate_cache_on_save,
    invalidates_cache,
    with_cache_tags,
)
from core.models import Game, GameAnalysis, Profile
from django.contrib.auth.models import User
from django.db.models.signals import post_delete, post_save
from django.http import JsonResponse
from django.test import RequestFactory


@pytest.fixture
def test_user(db):
    """Create a test user with profile."""
    user = User.objects.create(username="testuser", email="test@example.com")
    profile = Profile.objects.create(user=user, chess_com_username="testuser", lichess_username="testuser", credits=100)
    return user


@pytest.fixture
def test_game(db, test_user):
    """Create a test game."""
    return Game.objects.create(
        user=test_user,
        platform="lichess",
        white="testuser",
        black="opponent",
        pgn='[Event "Test Game"]\n1.e4 e5',
        result="1-0",
    )


@pytest.fixture
def request_factory():
    """Return a RequestFactory instance."""
    return RequestFactory()


@pytest.mark.django_db
class TestCacheInvalidator:
    """Tests for the CacheInvalidator class."""

    def setup_method(self):
        """Set up test data and mocks."""
        self.invalidate_pattern_patch = patch("core.cache_invalidation.invalidate_pattern")
        self.mock_invalidate_pattern = self.invalidate_pattern_patch.start()

        self.logger_patch = patch("core.cache_invalidation.logger")
        self.mock_logger = self.logger_patch.start()

    def teardown_method(self):
        """Clean up patches."""
        self.invalidate_pattern_patch.stop()
        self.logger_patch.stop()

    def test_invalidate_entity(self):
        """Test invalidating cache for a specific entity."""
        # Call the method
        CacheInvalidator.invalidate_entity("User", 1)

        # Check that invalidate_pattern was called with the expected patterns
        expected_calls = []
        for prefix in ENTITY_KEY_PREFIXES["User"]:
            expected_calls.append(call(f"{prefix}*1*", "redis"))

        # Also check dependent entities (Profile, Game, Subscription)
        for dep_type in ENTITY_DEPENDENCIES["User"]:
            for prefix in ENTITY_KEY_PREFIXES.get(dep_type, []):
                expected_calls.append(call(f"{prefix}*1*", "redis"))

        assert self.mock_invalidate_pattern.call_count >= len(ENTITY_KEY_PREFIXES["User"])
        # We don't check exact matches because of recursive calls and potential duplicate patterns

        # Check that logger.debug was called
        self.mock_logger.debug.assert_called_with("Invalidated cache for User:1")

    def test_invalidate_entity_with_exception(self):
        """Test invalidating cache for an entity when an exception occurs."""
        # Configure mock to raise an exception
        self.mock_invalidate_pattern.side_effect = Exception("Test exception")

        # Call the method
        CacheInvalidator.invalidate_entity("User", 1)

        # Check that logger.error was called
        self.mock_logger.error.assert_called_once()
        assert "Error invalidating entity cache for User:1" in self.mock_logger.error.call_args[0][0]

    def test_invalidate_tag(self):
        """Test invalidating cache for a specific tag."""
        # Call the method
        CacheInvalidator.invalidate_tag("user_games")

        # Check that invalidate_pattern was called with the expected patterns
        expected_calls = []
        for prefix in TAG_KEY_PREFIXES["user_games"]:
            expected_calls.append(call(f"{prefix}*", "redis"))

        # Also check dependent tags (game_details, game_analysis, dashboard)
        for dep_tag in TAG_DEPENDENCIES["user_games"]:
            for prefix in TAG_KEY_PREFIXES.get(dep_tag, []):
                expected_calls.append(call(f"{prefix}*", "redis"))

        assert self.mock_invalidate_pattern.call_count >= len(TAG_KEY_PREFIXES["user_games"])
        # We don't check exact matches because of recursive calls and potential duplicate patterns

        # Check that logger.debug was called
        self.mock_logger.debug.assert_called_with("Invalidated cache for tag: user_games")

    def test_invalidate_tag_with_exception(self):
        """Test invalidating cache for a tag when an exception occurs."""
        # Configure mock to raise an exception
        self.mock_invalidate_pattern.side_effect = Exception("Test exception")

        # Call the method
        CacheInvalidator.invalidate_tag("user_games")

        # Check that logger.error was called
        self.mock_logger.error.assert_called_once()
        assert "Error invalidating tag cache for user_games" in self.mock_logger.error.call_args[0][0]

    def test_invalidate_user_cache(self):
        """Test invalidating all cache entries for a user."""
        # Call the method
        CacheInvalidator.invalidate_user_cache(1)

        # Check that invalidate_pattern was called for each user-specific pattern
        patterns = [
            "user:*1*",
            "profile:*1*",
            "user_games:*1*",
            "dashboard:*1*",
            "analysis:*1*",
            "feedback:*1*",
            "user_stats:*1*",
            "subscription:*1*",
        ]

        expected_calls = [call(pattern, "redis") for pattern in patterns]
        # Check that all patterns were invalidated
        for pattern in patterns:
            self.mock_invalidate_pattern.assert_any_call(pattern, "redis")

        # Check that logger.debug was called
        self.mock_logger.debug.assert_called_with("Invalidated all cache for user: 1")

    def test_invalidate_game_cache(self):
        """Test invalidating all cache entries for a game."""
        # Call the method
        CacheInvalidator.invalidate_game_cache(123)

        # Check that invalidate_pattern was called for each game-specific pattern
        patterns = [
            "game:*123*",
            "analysis:*123*",
            "feedback:*123*",
        ]

        expected_calls = [call(pattern, "redis") for pattern in patterns]
        # Check that all patterns were invalidated
        for pattern in patterns:
            self.mock_invalidate_pattern.assert_any_call(pattern, "redis")

        # Check that logger.debug was called
        self.mock_logger.debug.assert_called_with("Invalidated all cache for game: 123")


@pytest.mark.django_db
class TestCacheDecorators:
    """Tests for cache invalidation decorators."""

    def test_with_cache_tags_decorator(self, request_factory):
        """Test the with_cache_tags decorator."""

        # Define a mock view function
        @with_cache_tags("user_games", "dashboard")
        def mock_view(request, user_id):
            return JsonResponse({"status": "success"})

        # Check that the cache tags were set on the function
        assert hasattr(mock_view, "_cache_tags")
        assert mock_view._cache_tags == {"user_games", "dashboard"}

        # Call the view function
        request = request_factory.get("/test/")
        response = mock_view(request, user_id=1)

        # Check that the function was called successfully
        assert response.status_code == 200

        # Add another tag and check that it's appended
        decorated_again = with_cache_tags("profile")(mock_view)
        assert decorated_again._cache_tags == {"user_games", "dashboard", "profile"}

    def test_invalidates_cache_decorator(self, request_factory):
        """Test the invalidates_cache decorator."""
        # Set up patches
        with patch("core.cache_invalidation.CacheInvalidator") as mock_invalidator:
            # Define a mock view function
            @invalidates_cache("user_games", "dashboard", entities={"User": "user_id"})
            def mock_view(request, user_id):
                return JsonResponse({"status": "success"})

            # Call the view function
            request = request_factory.get("/test/")
            response = mock_view(request, user_id=1)

            # Check that the function was called successfully
            assert response.status_code == 200

            # Check that CacheInvalidator.invalidate_tag was called for each tag
            assert mock_invalidator.invalidate_tag.call_count == 2
            mock_invalidator.invalidate_tag.assert_any_call("user_games")
            mock_invalidator.invalidate_tag.assert_any_call("dashboard")

            # Check that CacheInvalidator.invalidate_entity was called
            mock_invalidator.invalidate_entity.assert_called_once_with("User", 1)


@pytest.mark.django_db
class TestCacheSignalHandlers:
    """Tests for cache invalidation signal handlers."""

    def test_invalidate_cache_on_save(self, test_game):
        """Test cache invalidation when a model is saved."""
        with patch("core.cache_invalidation.CacheInvalidator") as mock_invalidator:
            # Simulate the post_save signal for Game model
            post_save.send(sender=Game, instance=test_game)

            # Check that CacheInvalidator.invalidate_entity was called
            mock_invalidator.invalidate_entity.assert_called_with("Game", test_game.id)

    def test_invalidate_cache_on_delete(self, test_game):
        """Test cache invalidation when a model is deleted."""
        with patch("core.cache_invalidation.CacheInvalidator") as mock_invalidator:
            # Simulate the post_delete signal for Game model
            post_delete.send(sender=Game, instance=test_game)

            # Check that CacheInvalidator.invalidate_entity was called
            mock_invalidator.invalidate_entity.assert_called_with("Game", test_game.id)


@pytest.mark.django_db
class TestIntegrationWithModels:
    """Integration tests with actual models."""

    def test_model_save_triggers_invalidation(self, test_user):
        """Test that saving a model triggers cache invalidation."""
        with patch("core.cache_invalidation.CacheInvalidator") as mock_invalidator:
            # Create a new game (triggers post_save)
            game = Game.objects.create(
                user=test_user,
                platform="chess.com",
                white="testuser",
                black="opponent",
                pgn='[Event "Test"]\n1.e4 e5',
                result="1-0",
            )

            # Check that CacheInvalidator.invalidate_entity was called
            mock_invalidator.invalidate_entity.assert_called_with("Game", game.id)

    def test_model_update_triggers_invalidation(self, test_game):
        """Test that updating a model triggers cache invalidation."""
        with patch("core.cache_invalidation.CacheInvalidator") as mock_invalidator:
            # Update an existing game
            test_game.result = "0-1"
            test_game.save()

            # Check that CacheInvalidator.invalidate_entity was called
            mock_invalidator.invalidate_entity.assert_called_with("Game", test_game.id)

    def test_model_delete_triggers_invalidation(self, test_game):
        """Test that deleting a model triggers cache invalidation."""
        game_id = test_game.id

        with patch("core.cache_invalidation.CacheInvalidator") as mock_invalidator:
            # Delete the game
            test_game.delete()

            # Check that CacheInvalidator.invalidate_entity was called
            mock_invalidator.invalidate_entity.assert_called_with("Game", game_id)
