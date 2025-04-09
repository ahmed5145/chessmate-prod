import json
import os
from unittest.mock import MagicMock, patch

from core.game_analyzer import GameAnalyzer
from core.models import Game, Profile
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

# Test settings
TEST_SETTINGS = {
    "TEST_MODE": True,  # Enable test mode to allow OpenAI
    "OPENAI_API_KEY": "test-key",
    "OPENAI_MODEL": "gpt-3.5-turbo",
    "OPENAI_MAX_TOKENS": 500,
    "OPENAI_TEMPERATURE": 0.7,
    "OPENAI_RATE_LIMIT": {
        "max_requests": 50,
        "window_seconds": 3600,
        "min_interval": 0.5,
    },
    "OPENAI_CACHE_KEY": "test_openai_rate_limit",
    "OPENAI_CACHE_TIMEOUT": 3600,
    "STOCKFISH_PATH": "stockfish",  # Mock path for tests
    "STOCKFISH_DEPTH": 20,
    "STOCKFISH_THREADS": 1,
    "STOCKFISH_HASH_SIZE": 128,
    "STOCKFISH_CONTEMPT": 0,
    "STOCKFISH_MIN_THINK_TIME": 20,
    "STOCKFISH_SKILL_LEVEL": 20,
    "REDIS_URL": None,  # Disable Redis for tests
    "USE_REDIS": False,
    "CACHES": {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-cache",
        }
    },
}


@override_settings(**TEST_SETTINGS)
class TestOpenAIFeedback(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(username="testuser", password="testpass123")

        # Create test game
        self.game = Game.objects.create(
            user=self.user,
            pgn="1. e4 e5 2. Nf3 Nc6",
            platform="lichess",
            game_id="test123",
            result="1-0",
            date_played=timezone.now(),
            white="testuser",
            black="opponent",
        )

        # Mock Stockfish engine
        self.patcher = patch("chess.engine.SimpleEngine.popen_uci")
        self.mock_engine = self.patcher.start()

        # Configure mock engine
        mock_engine_instance = MagicMock()
        mock_engine_instance.analyse.return_value = {
            "score": MagicMock(relative=MagicMock(return_value=MagicMock(cp=lambda: 100))),
            "depth": 20,
            "time": 0.5,
        }
        self.mock_engine.return_value = mock_engine_instance

        # Mock OpenAI client
        self.openai_patcher = patch("core.game_analyzer.OpenAI")
        self.mock_openai = self.openai_patcher.start()
        self.mock_openai_instance = MagicMock()
        self.mock_openai.return_value = self.mock_openai_instance

    def test_valid_openai_response(self):
        """Test handling of a valid OpenAI response"""
        # Create a valid response with all required sections
        valid_response = {
            "feedback": {
                "overall_performance": {
                    "accuracy": 85.5,
                    "evaluation": "Equal position",
                    "personalized_comment": "Strong tactical play",
                },
                "opening": {"analysis": "Solid opening play", "suggestions": ["Develop pieces faster"]},
                "middlegame": {"analysis": "Good tactical awareness", "suggestions": ["Look for combinations"]},
                "endgame": {"analysis": "Technical conversion", "suggestions": ["Practice endgames"]},
                "tactics": {"analysis": "Good tactical vision", "suggestions": ["Practice tactics"]},
                "time_management": {"analysis": "Good time usage", "suggestions": ["Be more consistent"]},
            }
        }

        # Configure mock OpenAI response
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(valid_response)))]
        self.mock_openai_instance.chat.completions.create.return_value = mock_completion

        # Create analyzer instance
        analyzer = GameAnalyzer()

        # Test with sample game data
        game_analysis = [
            {
                "move": "e4",
                "evaluation": 0.3,
                "best_move": "d4",
                "position": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
            }
        ]

        # Generate feedback
        feedback = analyzer._generate_ai_feedback(game_analysis, self.game)

        # Verify feedback structure
        self.assertIsNotNone(feedback)
        self.assertIn("overall_performance", feedback)
        self.assertIn("opening", feedback)
        self.assertIn("middlegame", feedback)
        self.assertIn("endgame", feedback)
        self.assertIn("tactics", feedback)
        self.assertIn("time_management", feedback)

    def test_malformed_response(self):
        """Test handling of a malformed OpenAI response"""
        # Create a malformed response missing required sections
        malformed_response = {
            "feedback": {
                "overall_performance": {"accuracy": 85.5}
                # Missing required sections
            }
        }

        # Configure mock OpenAI response
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(malformed_response)))]
        self.mock_openai_instance.chat.completions.create.return_value = mock_completion

        # Create analyzer instance
        analyzer = GameAnalyzer()

        # Test with sample game data
        game_analysis = [{"move": "e4", "evaluation": 0.3, "best_move": "d4"}]

        # Generate feedback
        feedback = analyzer._generate_ai_feedback(game_analysis, self.game)

        # Verify fallback to statistical feedback
        self.assertIsNone(feedback)

    def tearDown(self):
        # Stop the patchers
        self.patcher.stop()
        self.openai_patcher.stop()
        # Clean up
        self.game.delete()
        self.user.delete()
