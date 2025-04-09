"""Tests for cache invalidation middleware."""

import json
from unittest.mock import MagicMock, call, patch

import pytest
from core.cache_middleware import (
    MODEL_CACHE_MAPPING,
    CacheInvalidationMiddleware,
    get_related_values,
    invalidate_cache_on_delete,
    invalidate_cache_on_save,
    setup_cache_invalidation,
)
from core.models import Game, GameAnalysis, Player, Profile
from django.contrib.auth.models import User
from django.db.models.signals import post_delete, post_save
from django.test import TestCase


@pytest.mark.django_db
class TestCacheInvalidation:
    """Tests for cache invalidation functionality."""

    def setup_method(self):
        """Set up test data and mocks before each test."""
        # Patch the cache functions
        self.invalidate_by_tags_patch = patch("core.cache_middleware.redis_invalidate_by_tags")
        self.invalidate_game_patch = patch("core.cache_middleware.invalidate_game_cache")
        self.invalidate_user_games_patch = patch("core.cache_middleware.invalidate_user_games_cache")
        self.invalidate_analysis_patch = patch("core.cache_middleware.invalidate_analysis_cache")
        self.invalidate_prefix_patch = patch("core.cache_middleware.redis_invalidate_by_prefix")

        # Start patches
        self.mock_invalidate_by_tags = self.invalidate_by_tags_patch.start()
        self.mock_invalidate_game = self.invalidate_game_patch.start()
        self.mock_invalidate_user_games = self.invalidate_user_games_patch.start()
        self.mock_invalidate_analysis = self.invalidate_analysis_patch.start()
        self.mock_invalidate_prefix = self.invalidate_prefix_patch.start()

        # Create mock return values
        self.mock_invalidate_by_tags.return_value = 1
        self.mock_invalidate_game.return_value = True
        self.mock_invalidate_user_games.return_value = True
        self.mock_invalidate_analysis.return_value = True
        self.mock_invalidate_prefix.return_value = 1

    def teardown_method(self):
        """Clean up after each test."""
        # Stop patches
        self.invalidate_by_tags_patch.stop()
        self.invalidate_game_patch.stop()
        self.invalidate_user_games_patch.stop()
        self.invalidate_analysis_patch.stop()
        self.invalidate_prefix_patch.stop()

    @patch("core.cache_middleware.logger")
    def test_model_cache_mapping_structure(self, mock_logger):
        """Test that the model cache mapping structure is valid."""
        # Verify model mapping keys
        assert "Game" in MODEL_CACHE_MAPPING
        assert "Player" in MODEL_CACHE_MAPPING
        assert "GameAnalysis" in MODEL_CACHE_MAPPING
        assert "Profile" in MODEL_CACHE_MAPPING

        # Verify mapping structure for each model
        for model_name, mapping in MODEL_CACHE_MAPPING.items():
            assert "tags" in mapping
            assert "invalidate_functions" in mapping
            assert "related_invalidations" in mapping

    def test_get_related_values_simple_field(self):
        """Test getting related values for a simple field."""
        # Create a game with ID
        user = User.objects.create(username="testuser")
        game = Game.objects.create(
            user=user,
            platform="chess.com",
            white="player1",
            black="player2",
            pgn='[Event "Test"]\n1. e4 e5',
            result="win",
        )

        # Get the game ID
        values = get_related_values(game, "id")

        # Should return the game ID as a list with one item
        assert values == [game.id]

        # Try with user field that's a ForeignKey
        values = get_related_values(game, "user")

        # Should return the user object
        assert values == [user]

    def test_get_related_values_foreign_key_path(self):
        """Test getting related values through a foreign key relationship."""
        # Create user, game, and player
        user = User.objects.create(username="testuser")
        game = Game.objects.create(
            user=user,
            platform="chess.com",
            white="player1",
            black="player2",
            pgn='[Event "Test"]\n1. e4 e5',
            result="win",
        )
        profile = Profile.objects.create(
            user=user, chess_com_username="testuser_chesscom", lichess_username="testuser_lichess", credits=100
        )
        player = Player.objects.create(game=game, user=user, username="testuser", color="white", rating=1500)

        # Get user ID through game relationship
        values = get_related_values(player, "game__user__id")

        # Should return the user ID
        assert values == [user.id]

        # Get user email through profile relationship
        values = get_related_values(profile, "user__email")

        # Should return the user email
        assert values == [user.email]

    def test_get_related_values_many_to_many(self):
        """Test getting related values through a many-to-many relationship."""
        # Create user, games, and connect them via profile
        user1 = User.objects.create(username="user1")
        user2 = User.objects.create(username="user2")

        profile1 = Profile.objects.create(user=user1, chess_com_username="user1_chess", credits=100)
        profile2 = Profile.objects.create(user=user2, chess_com_username="user2_chess", credits=200)

        game1 = Game.objects.create(
            user=user1,
            platform="chess.com",
            white="user1",
            black="opponent",
            pgn='[Event "Test"]\n1. e4 e5',
            result="win",
        )
        game2 = Game.objects.create(
            user=user2,
            platform="chess.com",
            white="user2",
            black="opponent",
            pgn='[Event "Test"]\n1. d4 d5',
            result="loss",
        )

        # Add games to profiles
        profile1.games.add(game1)
        profile2.games.add(game2)

        # Use a mock for a model with a many-to-many relationship
        mock_model = MagicMock()
        mock_related = MagicMock()
        mock_related.all.return_value = [game1, game2]
        mock_model.games = mock_related

        # Get game IDs through the many-to-many relationship
        values = get_related_values(mock_model, "games__id")

        # Should return both game IDs
        assert set(values) == {game1.id, game2.id}

    def test_invalidate_cache_on_save_game(self):
        """Test cache invalidation when a Game model is saved."""
        # Create a game
        user = User.objects.create(username="testuser")
        game = Game.objects.create(
            user=user,
            platform="chess.com",
            white="player1",
            black="player2",
            pgn='[Event "Test"]\n1. e4 e5',
            result="win",
        )

        # Manually trigger the signal handler
        invalidate_cache_on_save(Game, game)

        # Check that the tag invalidation was called
        self.mock_invalidate_by_tags.assert_called_with(["games"])

        # Check that the game cache was invalidated
        self.mock_invalidate_game.assert_called_with(game.id)

    def test_invalidate_cache_on_save_player(self):
        """Test cache invalidation when a Player model is saved."""
        # Create user, game, and player
        user = User.objects.create(username="testuser")
        game = Game.objects.create(
            user=user,
            platform="chess.com",
            white="player1",
            black="player2",
            pgn='[Event "Test"]\n1. e4 e5',
            result="win",
        )
        player = Player.objects.create(game=game, user=user, username="testuser", color="white", rating=1500)

        # Reset mocks
        self.mock_invalidate_by_tags.reset_mock()
        self.mock_invalidate_game.reset_mock()
        self.mock_invalidate_user_games.reset_mock()

        # Manually trigger the signal handler
        invalidate_cache_on_save(Player, player)

        # Check that the tags were invalidated
        self.mock_invalidate_by_tags.assert_called_with(["players", "games"])

        # Check that the game cache was invalidated
        self.mock_invalidate_game.assert_called_with(game.id)

        # Check that the user games cache was invalidated
        self.mock_invalidate_user_games.assert_called_with(user.id)

    def test_invalidate_cache_on_save_game_analysis(self):
        """Test cache invalidation when a GameAnalysis model is saved."""
        # Create user, game, and analysis
        user = User.objects.create(username="testuser")
        game = Game.objects.create(
            user=user,
            platform="chess.com",
            white="player1",
            black="player2",
            pgn='[Event "Test"]\n1. e4 e5',
            result="win",
        )
        analysis = GameAnalysis.objects.create(
            game=game,
            moves_analysis={"1": {"eval": 0.5}},
            summary={"accuracy": 85.5},
            feedback={"strengths": ["Good opening"], "weaknesses": ["Missed tactic"]},
            depth=20,
        )

        # Reset mocks
        self.mock_invalidate_by_tags.reset_mock()
        self.mock_invalidate_game.reset_mock()
        self.mock_invalidate_analysis.reset_mock()

        # Manually trigger the signal handler
        invalidate_cache_on_save(GameAnalysis, analysis)

        # Check that the tags were invalidated
        self.mock_invalidate_by_tags.assert_called_with(["analysis"])

        # Check that the analysis cache was invalidated
        self.mock_invalidate_analysis.assert_called_with(analysis.id)

        # Check that the game cache was invalidated
        self.mock_invalidate_game.assert_called_with(game.id)

    def test_invalidate_cache_on_save_profile(self):
        """Test cache invalidation when a Profile model is saved."""
        # Create user and profile
        user = User.objects.create(username="testuser")
        profile = Profile.objects.create(
            user=user, chess_com_username="testuser_chesscom", lichess_username="testuser_lichess", credits=100
        )

        # Reset mocks
        self.mock_invalidate_by_tags.reset_mock()
        self.mock_invalidate_prefix.reset_mock()

        # Manually trigger the signal handler
        invalidate_cache_on_save(Profile, profile)

        # Check that the tags were invalidated
        self.mock_invalidate_by_tags.assert_called_with(["profiles", "users"])

        # Check that the user cache prefix was invalidated
        self.mock_invalidate_prefix.assert_called_once()

        # Check that the call used the correct user ID
        args, kwargs = self.mock_invalidate_prefix.call_args
        assert f"user:{user.id}" in args[0]

    def test_invalidate_cache_on_delete(self):
        """Test that cache invalidation works for model deletion."""
        # Create user and game
        user = User.objects.create(username="testuser")
        game = Game.objects.create(
            user=user,
            platform="chess.com",
            white="player1",
            black="player2",
            pgn='[Event "Test"]\n1. e4 e5',
            result="win",
        )

        # Reset mocks
        self.mock_invalidate_by_tags.reset_mock()
        self.mock_invalidate_game.reset_mock()

        # Create a copy of the game to use after deletion
        game_copy = MagicMock()
        game_copy.id = game.id

        # Delete the game
        game.delete()

        # Manually trigger the signal handler
        invalidate_cache_on_delete(Game, game_copy)

        # Check that the tag invalidation was called
        self.mock_invalidate_by_tags.assert_called_with(["games"])

        # Check that the game cache was invalidated
        self.mock_invalidate_game.assert_called_with(game_copy.id)

    @patch("core.cache_middleware.apps")
    def test_setup_cache_invalidation(self, mock_apps):
        """Test setting up cache invalidation."""
        # Create mock app configs and models
        mock_app_config1 = MagicMock()
        mock_app_config2 = MagicMock()

        # Set up the Game model mock
        mock_game_model = MagicMock()
        mock_game_model.__name__ = "Game"

        # Make the first app config return our mock Game model
        mock_app_config1.get_model.side_effect = lambda name: mock_game_model if name == "Game" else None

        # Make the second app config raise LookupError
        mock_app_config2.get_model.side_effect = LookupError

        # Set up the mock apps to return our app configs
        mock_apps.get_app_configs.return_value = [mock_app_config1, mock_app_config2]

        # Call the setup function
        setup_cache_invalidation()

        # Check that the function tried to get our models
        mock_app_config1.get_model.assert_any_call("Game")
        mock_app_config1.get_model.assert_any_call("Player")
        mock_app_config1.get_model.assert_any_call("GameAnalysis")
        mock_app_config1.get_model.assert_any_call("Profile")

    def test_middleware_initialization(self):
        """Test that the middleware can be initialized."""
        # Create a mock get_response function
        get_response = MagicMock()

        # Initialize the middleware
        middleware = CacheInvalidationMiddleware(get_response)

        # Check that the middleware stored the get_response function
        assert middleware.get_response == get_response

    def test_middleware_call(self):
        """Test that the middleware can be called."""
        # Create a mock request and response
        request = MagicMock()
        response = MagicMock()

        # Create a mock get_response function that returns our mock response
        get_response = MagicMock(return_value=response)

        # Initialize the middleware and call it
        middleware = CacheInvalidationMiddleware(get_response)
        result = middleware(request)

        # Check that the get_response function was called with our request
        get_response.assert_called_with(request)

        # Check that the middleware returned our response
        assert result == response
