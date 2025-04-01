import pytest
import chess
from django.utils import timezone
from django.db import transaction
from core.models import Game, Profile
from core.game_analyzer import GameAnalyzer
from core.task_manager import TaskManager
from core.tasks import analyze_game_task
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
pytestmark = pytest.mark.django_db

class TestGameAnalysis:
    @pytest.fixture(autouse=True)
    def setup(self, test_user, test_profile, test_game, stockfish_mock):
        """Set up test environment."""
        self.user = test_user
        self.profile = test_profile  # Use the existing profile
        self.game = test_game
        self.stockfish_mock = stockfish_mock
        self.analyzer = GameAnalyzer()
        self.task_manager = TaskManager()

    def test_full_analysis_pipeline(self, capture_queries):
        """Test the complete analysis pipeline."""
        # Set up test game with known positions
        self.game.pgn = "1. e4 e5 2. Nf3 Nc6 3. Bb5"  # Simple Spanish opening
        self.game.status = 'pending'
        self.game.analysis_status = 'pending'
        self.game.save()

        # Mock Stockfish responses for each position
        mock_responses = [
            self.stockfish_mock.create_analysis_result(cp_score=10),
            self.stockfish_mock.create_analysis_result(cp_score=-5),
            self.stockfish_mock.create_analysis_result(cp_score=15)
        ]

        # Set up the mock to return our structured responses
        self.stockfish_mock.return_value.analyse.side_effect = mock_responses

        # Create analysis task
        task_result = self.task_manager.create_analysis_job(self.game.id)
        assert task_result['status'] == 'PENDING'

        # Run analysis task directly in test mode
        result = analyze_game_task(None, self.game.id)
        assert result['status'] == 'completed'

        # Verify analysis results were saved
        self.game.refresh_from_db()
        assert self.game.status == 'analyzed'
        assert self.game.analysis_status == 'completed'
        assert self.game.analysis is not None
        assert self.game.analysis_completed_at is not None

        # Verify analysis data structure
        analysis_data = self.game.analysis
        assert isinstance(analysis_data, dict)
        assert 'moves' in analysis_data
        assert 'summary' in analysis_data
        assert 'evaluation' in analysis_data
        assert 'timestamp' in analysis_data

        # Verify moves analysis
        moves = analysis_data['moves']
        assert isinstance(moves, list)
        assert len(moves) > 0
        for move in moves:
            assert 'move' in move
            assert 'evaluation' in move
            assert 'position' in move

        # Verify summary
        summary = analysis_data['summary']
        assert isinstance(summary, dict)
        assert 'opening' in summary
        assert 'middlegame' in summary
        assert 'endgame' in summary
        assert 'strengths' in summary
        assert 'weaknesses' in summary

    def test_analysis_with_tactical_positions(self, capture_queries):
        """Test analysis pipeline with tactical positions."""
        # Set up a game with a capture
        self.game.pgn = "1. e4 e5 2. Nf3 d6 3. Nxe5"  # Knight captures pawn on e5
        self.game.save()

        # Mock Stockfish responses
        mock_responses = [
            self.stockfish_mock.create_analysis_result(cp_score=10),
            self.stockfish_mock.create_analysis_result(cp_score=100)
        ]

        # Set up the mock to return our structured responses
        self.stockfish_mock.return_value.analyse.side_effect = mock_responses

        # Create and run analysis task
        task_result = self.task_manager.create_analysis_job(self.game.id)
        result = analyze_game_task(None, self.game.id)
        
        # Verify analysis completed successfully
        assert result['status'] == 'completed'
        
        # Verify tactical detection
        self.game.refresh_from_db()
        assert self.game.status == 'analyzed'
        analysis_data = self.game.analysis
        feedback = analysis_data['feedback']
        summary = feedback['analysis_results']['summary']
        
        # Verify tactics metrics
        assert 'tactics' in summary
        tactics = summary['tactics']
        assert tactics.get('opportunities', 0) > 0
        assert tactics.get('success_rate', 0) > 0

    def test_error_handling(self):
        """Test error handling in analysis pipeline."""
        # Set up a game with invalid PGN
        self.game.pgn = "1. e4 e5 2. invalid_move"
        self.game.save()

        # Mock Stockfish to return error response
        def mock_analyze(*args, **kwargs):
            return {
                'analysis_complete': False,
                'error': 'Invalid move found: invalid_move',
                'analysis_results': None,
                'source': 'stockfish',
                'timestamp': datetime.now().isoformat()
            }
        self.stockfish_mock.return_value.analyse.side_effect = mock_analyze

        # Create and run analysis task
        task_result = self.task_manager.create_analysis_job(self.game.id)
        result = analyze_game_task(None, self.game.id)
        
        # Verify error was handled correctly
        assert result['status'] == 'failed'
        self.game.refresh_from_db()
        assert self.game.status == 'failed'
        assert 'Invalid move' in result.get('message', '')
        
        # Verify error response structure matches frontend expectations
        assert result.get('error') is not None
        assert isinstance(result.get('message'), str)
        assert result.get('game_id') == self.game.id

    def test_metrics_calculation(self):
        """Test calculation of game metrics."""
        self.game.pgn = "1. e4 e5 2. Nf3 Nc6 3. Bb5"
        self.game.save()

        # Mock Stockfish responses with detailed metrics
        mock_response = self.stockfish_mock.create_analysis_result(
            cp_score=10,
            depth=20,
            nodes=1000,
            time=0.5
        )
        self.stockfish_mock.return_value.analyse.return_value = mock_response

        # Run analysis
        analysis_results = self.analyzer.analyze_single_game(self.game)
        feedback = self.analyzer.generate_feedback(analysis_results, self.game)

        # Verify metrics structure
        assert 'analysis_results' in feedback
        metrics = feedback['analysis_results']['summary']

        # Check all required metric categories
        assert 'overall' in metrics
        assert 'phases' in metrics
        assert 'tactics' in metrics
        assert 'time_management' in metrics
        assert 'positional' in metrics
        assert 'advantage' in metrics
        assert 'resourcefulness' in metrics

        # Verify metric values are within expected ranges
        overall = metrics['overall']
        assert 0 <= overall.get('accuracy', 0) <= 100
        assert isinstance(overall.get('mistakes', 0), int)
        assert isinstance(overall.get('blunders', 0), int)

    def test_concurrent_analysis(self, test_game):
        """Test handling of concurrent analysis requests."""
        # Create a second game for concurrent analysis
        game2 = Game.objects.create(
            user=self.profile.user,
            platform='test',
            game_id='test456',
            white=self.profile.user.username,
            black=self.profile.user.username,
            pgn="1. e4 e5 2. Nf3",
            result='*',
            date_played=timezone.now()
        )

        # Mock Stockfish responses
        mock_responses = [
            {
                'analysis_complete': True,
                'analysis_results': {
                    'moves': [
                        {'move': 'e4', 'score': 10, 'depth': 20, 'nodes': 1000, 'time': 0.5},
                        {'move': 'e5', 'score': 15, 'depth': 20, 'nodes': 1000, 'time': 0.5}
                    ],
                    'summary': {
                        'overall': {'accuracy': 85, 'mistakes': 0, 'blunders': 0},
                        'phases': {'opening': 90, 'middlegame': 0, 'endgame': 0},
                        'tactics': {'opportunities': 0, 'success_rate': 0},
                        'time_management': {'average_time': 0.5},
                        'positional': {'space': 60, 'control': 70},
                        'advantage': {'max': 15, 'min': 10},
                        'resourcefulness': {'defensive': 80, 'attacking': 75}
                    }
                },
                'feedback': {
                    'analysis_results': {
                        'summary': {
                            'overall': {'accuracy': 85},
                            'phases': {'opening': 90},
                            'tactics': {'opportunities': 0},
                            'time_management': {'average_time': 0.5},
                            'positional': {'space': 60},
                            'advantage': {'max': 15},
                            'resourcefulness': {'defensive': 80}
                        },
                        'strengths': ['Solid opening play'],
                        'weaknesses': [],
                        'critical_moments': [],
                        'improvement_areas': 'Look for more dynamic opportunities'
                    },
                    'analysis_complete': True,
                    'source': 'stockfish'
                },
                'source': 'stockfish',
                'timestamp': datetime.now().isoformat()
            }
        ]

        # Set up the mock to return our structured response for both games
        self.stockfish_mock.return_value.analyse.side_effect = mock_responses * 2

        # Create and run analysis tasks
        task1 = self.task_manager.create_analysis_job(self.game.id)
        task2 = self.task_manager.create_analysis_job(game2.id)

        # Run both tasks directly in test mode
        result1 = analyze_game_task(None, self.game.id)
        result2 = analyze_game_task(None, game2.id)

        # Verify both analyses completed successfully
        self.game.refresh_from_db()
        game2.refresh_from_db()
        assert self.game.status == 'analyzed'
        assert game2.status == 'analyzed'

        # Verify both analyses have proper structure
        for game in [self.game, game2]:
            analysis = game.analysis
            assert 'feedback' in analysis
            assert 'analysis_complete' in analysis
            assert analysis['analysis_complete'] is True
            assert 'source' in analysis
            assert analysis['source'] == 'stockfish'

    def test_feedback_generation(self):
        """Test generation of game feedback."""
        self.game.pgn = "1. e4 e5 2. Nf3 Nc6 3. Bb5"
        self.game.save()

        # Mock Stockfish responses
        self.stockfish_mock.return_value.analyse.side_effect = [
            {
                'score': chess.engine.PovScore(chess.engine.Cp(10), chess.WHITE),
                'depth': 20,
                'pv': [],
                'nodes': 1000,
                'time': 0.5
            }
        ]

        # Run analysis
        analysis_results = self.analyzer.analyze_single_game(self.game)
        feedback = self.analyzer.generate_feedback(analysis_results, self.game)

        # Verify feedback structure
        assert 'analysis_results' in feedback
        assert 'analysis_complete' in feedback
        assert feedback['source'] == 'stockfish'

        # Verify feedback content
        analysis_results = feedback['analysis_results']
        assert isinstance(analysis_results['improvement_areas'], str)
        assert isinstance(analysis_results['strengths'], list)
        assert isinstance(analysis_results['weaknesses'], list)
        assert isinstance(analysis_results['critical_moments'], list)

    def tearDown(self):
        """Clean up test environment after each test."""
        try:
            with transaction.atomic():
                if hasattr(self, 'user'):
                    self.user.delete()
                if hasattr(self, 'stockfish_mock'):
                    self.stockfish_mock.return_value.cleanup()
        except Exception as e:
            logger.error(f"Error during test cleanup: {str(e)}")
        finally:
            logger.info("Test environment cleanup complete") 