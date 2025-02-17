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
        self.game.save()

        # Mock Stockfish responses for each position
        self.stockfish_mock.return_value.analyse.side_effect = [
            {
                'score': chess.engine.PovScore(chess.engine.Cp(10), chess.WHITE),
                'depth': 20,
                'pv': [],
                'nodes': 1000,
                'time': 0.5
            },
            {
                'score': chess.engine.PovScore(chess.engine.Cp(-5), chess.BLACK),
                'depth': 20,
                'pv': [],
                'nodes': 1200,
                'time': 0.6
            },
            {
                'score': chess.engine.PovScore(chess.engine.Cp(15), chess.WHITE),
                'depth': 20,
                'pv': [],
                'nodes': 1500,
                'time': 0.7
            }
        ]

        # Create analysis task
        task_result = self.task_manager.create_analysis_job(self.game.id)
        assert task_result['status'] == 'PENDING'

        # Run analysis task
        result = analyze_game_task(task_result['task_id'], self.game.id)
        assert result['status'] == 'completed'

        # Verify analysis results were saved
        self.game.refresh_from_db()
        assert self.game.status == 'analyzed'
        assert self.game.analysis is not None
        assert self.game.analysis_completed_at is not None

        # Verify analysis data structure
        analysis_data = self.game.analysis
        assert 'analysis_results' in analysis_data
        assert 'feedback' in analysis_data
        assert 'analysis_complete' in analysis_data
        assert 'timestamp' in analysis_data
        assert 'source' in analysis_data

        # Verify feedback structure
        feedback = analysis_data['feedback']
        assert 'analysis_results' in feedback
        assert 'analysis_complete' in feedback
        assert feedback['source'] == 'stockfish'

        # Verify analysis results structure
        analysis_results = feedback['analysis_results']
        assert 'summary' in analysis_results
        assert 'strengths' in analysis_results
        assert 'weaknesses' in analysis_results
        assert 'critical_moments' in analysis_results
        assert 'improvement_areas' in analysis_results

        # Verify summary metrics
        summary = analysis_results['summary']
        assert 'overall' in summary
        assert 'phases' in summary
        assert 'tactics' in summary
        assert 'time_management' in summary
        assert 'positional' in summary
        assert 'advantage' in summary
        assert 'resourcefulness' in summary

    def test_analysis_with_tactical_positions(self, capture_queries):
        """Test analysis pipeline with tactical positions."""
        # Set up a game with a capture
        self.game.pgn = "1. e4 e5 2. Nxe5"  # Knight captures pawn
        self.game.save()

        # Mock Stockfish responses
        self.stockfish_mock.return_value.analyse.side_effect = [
            {
                'score': chess.engine.PovScore(chess.engine.Cp(10), chess.WHITE),
                'depth': 20,
                'pv': [],
                'nodes': 1000,
                'time': 0.5
            },
            {
                'score': chess.engine.PovScore(chess.engine.Cp(100), chess.WHITE),
                'depth': 20,
                'pv': [],
                'nodes': 1200,
                'time': 0.6
            }
        ]

        # Create and run analysis task
        task_result = self.task_manager.create_analysis_job(self.game.id)
        result = analyze_game_task(task_result['task_id'], self.game.id)
        assert result['status'] == 'completed'

        # Verify tactical detection
        self.game.refresh_from_db()
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

        # Create and run analysis task
        task_result = self.task_manager.create_analysis_job(self.game.id)
        result = analyze_game_task(task_result['task_id'], self.game.id)
        assert result['status'] == 'failed'

        # Verify error was recorded
        self.game.refresh_from_db()
        assert self.game.status == 'failed'

    def test_metrics_calculation(self):
        """Test calculation of game metrics."""
        self.game.pgn = "1. e4 e5 2. Nf3 Nc6 3. Bb5"
        self.game.save()

        # Mock Stockfish responses with detailed metrics
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
            white_player=self.profile,
            black_player=self.profile,
            pgn="1. e4 e5 2. Nf3",
            created_at=timezone.now()
        )

        # Mock Stockfish responses
        self.stockfish_mock.return_value.analyse.side_effect = [
            {
                'score': chess.engine.PovScore(chess.engine.Cp(10), chess.WHITE),
                'depth': 20,
                'pv': [],
                'nodes': 1000,
                'time': 0.5
            }
        ] * 4  # Enough responses for both games

        # Create and run analysis tasks
        task1 = self.task_manager.create_analysis_job(self.game.id)
        task2 = self.task_manager.create_analysis_job(game2.id)

        # Run both tasks
        result1 = analyze_game_task(task1['task_id'], self.game.id)
        result2 = analyze_game_task(task2['task_id'], game2.id)

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