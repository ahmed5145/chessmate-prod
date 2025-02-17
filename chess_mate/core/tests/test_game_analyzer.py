import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime
from core.game_analyzer import GameAnalyzer
from core.models import Game, Profile
from django.contrib.auth.models import User
import chess.pgn
import chess.engine
import io
from openai import OpenAI

# Test settings
TEST_SETTINGS = {
    'TEST_MODE': False,  # Set to False to allow OpenAI client initialization
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
    'STOCKFISH_PATH': 'stockfish'  # Mock path for tests
}

@override_settings(**TEST_SETTINGS)
class TestGameAnalyzer(TestCase):
    def setUp(self):
        # Clear cache before each test
        cache.clear()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create or get user profile
        self.profile, _ = Profile.objects.get_or_create(
            user=self.user,
            defaults={'credits': 10}
        )
        
        # Create a test game with proper PGN format
        self.game = Game.objects.create(
            user=self.user,
            platform='chess.com',
            game_id='test123',
            pgn="""[Event "Test Game"]
[Site "Chess.com"]
[Date "2024.01.15"]
[White "TestUser"]
[Black "Opponent"]
[Result "1-0"]
[WhiteElo "1500"]
[BlackElo "1450"]
[TimeControl "600"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 O-O 8. c3 d6 9. h3 Na5 10. Bc2 c5 11. d4 Qc7 12. Nbd2 cxd4 13. cxd4 Nc6 14. Nb3 a5 15. Be3 a4 16. Nbd2 Bd7 1-0""",
            white="TestUser",
            black="Opponent",
            result="1-0",
            date_played=timezone.now()
        )

    @patch('core.game_analyzer.OpenAI')
    @patch('chess.engine.SimpleEngine.popen_uci')
    def test_game_analysis_with_rate_limiting(self, mock_engine, mock_openai):
        """Test game analysis with OpenAI integration."""
        # Set up mock engine
        mock_engine_instance = MagicMock()
        mock_engine_instance.analyse.return_value = {
            "score": chess.engine.PovScore(chess.engine.Cp(100), chess.WHITE),
            "depth": 20,
            "time": 0.5
        }
        mock_engine.return_value = mock_engine_instance
        
        # Set up mock OpenAI client
        mock_openai_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="""
                    {
                        "summary": {
                            "accuracy": 85,
                            "evaluation": "Strong performance",
                            "personalized_comment": "Good understanding of the position"
                        },
                        "phase_analysis": {
                            "opening": {
                                "analysis": "Good opening play",
                                "suggestions": ["Consider e4 variations"]
                            },
                            "middlegame": {
                                "analysis": "Solid positional play",
                                "suggestions": ["Focus on piece coordination"]
                            },
                            "endgame": {
                                "analysis": "Efficient conversion",
                                "suggestions": ["Practice basic endgames"]
                            }
                        },
                        "study_plan": {
                            "focus_areas": ["Opening theory", "Tactical awareness"],
                            "rating_appropriate_exercises": ["Basic tactics", "Endgame studies"]
                        }
                    }
                    """
                )
            )
        ]
        mock_openai_instance.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_openai_instance
        
        # Initialize analyzer with mocked components
        self.analyzer = GameAnalyzer()
        self.analyzer.engine = mock_engine_instance
        self.analyzer.openai_client = mock_openai_instance
        
        # Run analysis
        analysis_results = self.analyzer.analyze_single_game(self.game)
        self.assertTrue(len(analysis_results) > 0, "No moves were analyzed")
        
        feedback = self.analyzer.generate_feedback(analysis_results, self.game)
        
        # Verify feedback structure
        self.assertIn('summary', feedback)
        self.assertIn('phase_analysis', feedback)
        self.assertIn('study_plan', feedback)
        
        # Verify source is set correctly
        self.assertIn('source', feedback)
        self.assertEqual(feedback['source'], 'openai_analysis')

    @patch('core.game_analyzer.OpenAI')
    @patch('chess.engine.SimpleEngine.popen_uci')
    def test_personalized_feedback(self, mock_engine, mock_openai):
        """Test that feedback is personalized based on player profile."""
        # Set up mock engine
        mock_engine_instance = MagicMock()
        mock_engine_instance.analyse.return_value = {
            "score": chess.engine.PovScore(chess.engine.Cp(100), chess.WHITE),
            "depth": 20,
            "time": 0.5
        }
        mock_engine.return_value = mock_engine_instance
        
        # Set up mock OpenAI client
        mock_openai_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="""
                    {
                        "summary": {
                            "accuracy": 85,
                            "evaluation": "Strong performance for your rating level (1500)",
                            "personalized_comment": "Your play shows improvement in positional understanding"
                        },
                        "phase_analysis": {
                            "opening": {
                                "analysis": "Good handling of the Ruy Lopez",
                                "suggestions": ["For your rating level, consider studying key Ruy Lopez positions"]
                            },
                            "middlegame": {
                                "analysis": "Solid positional play, appropriate for your rating",
                                "suggestions": ["Focus on piece coordination", "Study typical Ruy Lopez middlegame plans"]
                            },
                            "endgame": {
                                "analysis": "Efficient conversion showing good technique",
                                "suggestions": ["Practice basic endgames", "Study rook endgames"]
                            }
                        },
                        "study_plan": {
                            "focus_areas": ["Ruy Lopez theory", "Positional play", "Endgame technique"],
                            "rating_appropriate_exercises": ["1400-1600 tactical exercises", "Basic endgame studies"]
                        }
                    }
                    """
                )
            )
        ]
        mock_openai_instance.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_openai_instance
        
        # Initialize analyzer with mocked components
        self.analyzer = GameAnalyzer()
        self.analyzer.engine = mock_engine_instance
        self.analyzer.openai_client = mock_openai_instance
        
        # Update profile with rating history
        self.profile.rating_history = {
            'rapid': {
                '2024-01': 1500,
                '2023-12': 1450
            }
        }
        self.profile.save()
        
        # Run analysis
        analysis_results = self.analyzer.analyze_single_game(self.game)
        self.assertTrue(len(analysis_results) > 0, "No moves were analyzed")
        
        feedback = self.analyzer.generate_feedback(analysis_results, self.game)
        
        # Verify personalization
        self.assertIn('summary', feedback)
        self.assertIn('personalized_comment', feedback['summary'])
        self.assertIn('study_plan', feedback)
        self.assertIn('rating_appropriate_exercises', feedback['study_plan'])
        
        # Verify content mentions rating level
        self.assertIn('1500', str(feedback['summary']['evaluation']))
        
        # Verify source is OpenAI
        self.assertEqual(feedback['source'], 'openai_analysis')

    def tearDown(self):
        # Clean up
        cache.clear()
        if hasattr(self, 'analyzer'):
            self.analyzer.cleanup()
