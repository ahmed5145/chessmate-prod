import os
import json
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import Game, Profile
from core.game_analyzer import GameAnalyzer
from django.conf import settings
from unittest.mock import patch, MagicMock
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

# Test settings
TEST_SETTINGS = {
    'TEST_MODE': True,  # Enable test mode to allow OpenAI
    'OPENAI_API_KEY': 'test-key',
    'OPENAI_MODEL': 'gpt-3.5-turbo',
    'OPENAI_MAX_TOKENS': 500,
    'OPENAI_TEMPERATURE': 0.7,
    'OPENAI_RATE_LIMIT': {
        'max_requests': 50,
        'window_seconds': 3600,
        'min_interval': 0.5,
    },
    'OPENAI_CACHE_KEY': 'test_openai_rate_limit',
    'OPENAI_CACHE_TIMEOUT': 3600,
    'STOCKFISH_PATH': 'stockfish',  # Mock path for tests
    'STOCKFISH_DEPTH': 20,
    'STOCKFISH_THREADS': 1,
    'STOCKFISH_HASH_SIZE': 128,
    'STOCKFISH_CONTEMPT': 0,
    'STOCKFISH_MIN_THINK_TIME': 20,
    'STOCKFISH_SKILL_LEVEL': 20,
    'REDIS_URL': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    'REDIS_HOST': os.getenv('REDIS_HOST', 'localhost'),
    'REDIS_PORT': int(os.getenv('REDIS_PORT', '6379')),
    'REDIS_DB': int(os.getenv('REDIS_DB', '0')),
    'CACHE_TTL': 3600,
    'CACHES': {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'test-cache',
        }
    }
}

@override_settings(**TEST_SETTINGS)
class TestOpenAIFeedback(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        
        # Create test game
        self.game = Game.objects.create(
            user=self.user,
            platform='chess.com',
            game_id='test123',
            pgn='1. e4 e5 2. Nf3 Nc6 3. Bb5 a6',
            result='1-0',
            white='testuser',
            black='opponent',
            date_played='2024-01-01T00:00:00Z'
        )
        
        # Sample analysis results
        self.analysis_results = [
            {
                'move_number': 1,
                'move': 'e4',
                'score': 0.5,
                'depth': 20,
                'time_spent': 1.0,
                'is_mistake': False,
                'is_blunder': False,
                'evaluation_drop': 0,
                'position_complexity': 0.3,
                'time_control_phase': 'opening'
            },
            {
                'move_number': 1,
                'move': 'e5',
                'score': 0.3,
                'depth': 20,
                'time_spent': 1.5,
                'is_mistake': False,
                'is_blunder': False,
                'evaluation_drop': 0.2,
                'position_complexity': 0.4,
                'time_control_phase': 'opening'
            }
        ]

    def test_valid_openai_response(self):
        """Test handling of a valid OpenAI response"""
        mock_response = {
            "summary": {
                "accuracy": 85.5,
                "evaluation": "Equal position",
                "comment": "Strong tactical play with good time management"
            },
            "phases": {
                "opening": {
                    "analysis": "Solid opening play",
                    "suggestions": ["Develop pieces faster", "Control center early"]
                },
                "middlegame": {
                    "analysis": "Good tactical awareness",
                    "suggestions": ["Look for combinations", "Improve piece coordination"]
                },
                "endgame": {
                    "analysis": "Technical conversion needed work",
                    "suggestions": ["Practice basic endgames", "Activate king earlier"]
                }
            },
            "tactics": {
                "analysis": "Good tactical awareness",
                "opportunities": 5,
                "successful": 3,
                "success_rate": 60.0,
                "suggestions": ["Practice tactical patterns", "Calculate variations deeper"]
            },
            "time_management": {
                "score": 85,
                "avg_time_per_move": 15.5,
                "time_pressure_moves": 3,
                "time_pressure_percentage": 10.0,
                "suggestion": "Good time management overall"
            }
        }

        with patch('chess.engine.SimpleEngine.popen_uci'), \
             patch('openai.OpenAI') as mock_openai:
            
            # Configure mock OpenAI response
            mock_message = ChatCompletionMessage(
                content=json.dumps(mock_response),
                role="assistant",
                function_call=None,
                tool_calls=None
            )
            mock_choice = Choice(
                finish_reason="stop",
                index=0,
                message=mock_message
            )
            mock_completion = ChatCompletion(
                id="test-id",
                choices=[mock_choice],
                created=1234567890,
                model="gpt-3.5-turbo",
                object="chat.completion",
                usage={"prompt_tokens": 100, "completion_tokens": 100, "total_tokens": 200}
            )
            
            # Set up mock client
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai.return_value = mock_client
            
            # Test the analyzer
            analyzer = GameAnalyzer()
            feedback = analyzer._generate_ai_feedback(self.analysis_results, self.game)
            
            # Verify response structure
            self.assertIsNotNone(feedback)
            self.assertIn('summary', feedback)
            self.assertIn('phases', feedback)
            self.assertIn('tactics', feedback)
            self.assertIn('time_management', feedback)
            
            # Verify content
            self.assertEqual(feedback['summary']['accuracy'], 85.5)
            self.assertEqual(feedback['phases']['opening']['analysis'], "Solid opening play")
            self.assertEqual(feedback['tactics']['success_rate'], 60.0)
            self.assertEqual(feedback['time_management']['score'], 85)

    def test_malformed_response(self):
        """Test handling of malformed OpenAI response"""
        # Create an intentionally truncated response string
        truncated_json = (
            '{"summary":{"accuracy":100.0,"evaluation":"Perfect game",'
            '"comment":"Flawless play"},"time_management":{"score":92,'
            '"avg_time_per_move":1.0,"time'
        )

        with patch('chess.engine.SimpleEngine.popen_uci'), \
             patch('openai.OpenAI') as mock_openai:
            
            # Configure mock OpenAI response with malformed JSON
            mock_message = ChatCompletionMessage(
                content=truncated_json,
                role="assistant",
                function_call=None,
                tool_calls=None
            )
            mock_choice = Choice(
                finish_reason="stop",
                index=0,
                message=mock_message
            )
            mock_completion = ChatCompletion(
                id="test-id",
                choices=[mock_choice],
                created=1234567890,
                model="gpt-3.5-turbo",
                object="chat.completion",
                usage={"prompt_tokens": 100, "completion_tokens": 100, "total_tokens": 200}
            )
            
            # Set up mock client
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai.return_value = mock_client
            
            # Test the analyzer
            analyzer = GameAnalyzer()
            feedback = analyzer._generate_ai_feedback(self.analysis_results, self.game)
            
            # Verify fallback behavior
            self.assertIsNotNone(feedback)
            self.assertIn('source', feedback)
            self.assertEqual(feedback['source'], 'statistical_analysis')

    def tearDown(self):
        # Clean up
        self.user.delete()
        self.game.delete() 