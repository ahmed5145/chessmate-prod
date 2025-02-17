from django.test import TestCase
from django.contrib.auth.models import User
from .models import Game, Profile
from datetime import datetime
import uuid
import chess
from .game_analyzer import GameAnalyzer
from django.utils import timezone
from unittest.mock import patch
from chess_mate.core.chess_services import ChessComService

class FeedbackTestCase(TestCase):
    def setUp(self):
        # Create a user first
        self.user = User.objects.create_user(
            username=f"test_user_{uuid.uuid4().hex[:8]}",
            password="test_pass",
            email="test@example.com"
        )
        # Delete any existing profile for this user
        Profile.objects.filter(user=self.user).delete()
        # Create a profile for the user
        Profile.objects.create(user=self.user, credits=10)
        # Create a game using the user
        self.game = Game.objects.create(
            user=self.user,
            platform='chess.com',
            game_id=uuid.uuid4().hex,
            white='testuser',
            black='test_opponent',
            result='win',
            pgn='1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7',
            date_played=timezone.now(),
            opening_name='Ruy Lopez',
            opponent='test_opponent'
        )

    def test_feedback_generation(self):
        try:
            analyzer = GameAnalyzer()
            analysis_results = analyzer.analyze_games([self.game])
            feedback = analyzer.generate_feedback(analysis_results[self.game.id])
            
            self.assertIsInstance(feedback, dict)
            self.assertIn('opening', feedback)
            self.assertIn('accuracy', feedback['opening'])
            self.assertIn('mistakes', feedback)
            self.assertIn('blunders', feedback)
            self.assertIn('time_management', feedback)
            self.assertIn('tactical_opportunities', feedback)
            self.assertIsInstance(feedback['tactical_opportunities'], list)
        except chess.engine.EngineTerminatedError:
            self.skipTest("Stockfish engine not available")
        finally:
            if analyzer:
                analyzer.close_engine()

class ChessComServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=f"test_user_{uuid.uuid4().hex[:8]}",
            password="test_pass",
            email="test@example.com"
        )
        self.profile = Profile.objects.create(user=self.user, credits=10)
        self.service = ChessComService()

    def test_fetch_games_respects_limit(self):
        """Test that fetch_games respects the limit parameter and credit deduction."""
        username = "test_player"
        limit = 5
        initial_credits = self.profile.credits

        # Create some test game data
        test_games = []
        for i in range(10):  # Create more games than the limit
            test_games.append({
                'url': f'https://chess.com/game/{i}',
                'pgn': f'[Event "Test Game {i}"]\n1. e4 e5',
                'time_class': 'rapid',
                'white': {'username': username if i % 2 == 0 else 'opponent', 'rating': 1500},
                'black': {'username': 'opponent' if i % 2 == 0 else username, 'rating': 1500},
                'time_control': '10+0'
            })

        # Mock the API response
        with patch('chess_mate.core.chess_services.requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {'games': test_games}
            
            # Mock the archives endpoint
            with patch('chess_mate.core.chess_services.ChessComService.fetch_archives') as mock_archives:
                mock_archives.return_value = ['https://api.chess.com/pub/player/test_player/games/2024/01']
                
                # Fetch games
                result = self.service.fetch_games(username, self.user, limit=limit)
                
                # Verify results
                self.assertEqual(result['saved'], limit)  # Should only save up to the limit
                self.assertTrue(result['skipped'] >= 0)  # Should track skipped games
                self.assertEqual(len(result['games']), limit)  # Should return only up to limit games
                
                # Verify credit deduction
                self.profile.refresh_from_db()
                self.assertEqual(self.profile.credits, initial_credits - limit)
                
                # Verify saved games in database
                saved_games = Game.objects.filter(user=self.user).count()
                self.assertEqual(saved_games, limit)

