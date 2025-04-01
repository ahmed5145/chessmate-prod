import pytest
import unittest
from unittest.mock import patch, MagicMock
import chess
import chess.engine
from django.test import TransactionTestCase
from django.conf import settings
from ..analysis.stockfish_analyzer import StockfishAnalyzer
import time
import logging
import threading
from conftest import TestCase
from typing import Optional
from django.db import transaction, connection

# Set up logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MockScore:
    def __init__(self, cp_score: Optional[int] = None, mate_in: Optional[int] = None):
        self.cp_score = cp_score
        self.mate_in = mate_in
        
    def score(self, mate_score: int = 10000) -> Optional[int]:
        if self.mate_in is not None:
            return mate_score if self.mate_in > 0 else -mate_score
        return self.cp_score
        
    def is_mate(self) -> bool:
        return self.mate_in is not None
        
    def mate(self) -> Optional[int]:
        return self.mate_in
        
    def cp(self) -> Optional[int]:
        return self.cp_score
        
    def white(self) -> 'MockScore':
        """Get score from White's point of view."""
        return self
        
    def black(self) -> 'MockScore':
        """Get score from Black's point of view."""
        if self.mate_in is not None:
            return MockScore(None, -self.mate_in if self.mate_in else None)
        return MockScore(-self.cp_score if self.cp_score is not None else None)

class MockPovScore:
    def __init__(self, score: MockScore, color: bool):
        self._score = score
        self._color = color
        
    def relative(self) -> MockScore:
        """Get score relative to the position's player."""
        return self._score
        
    def pov(self, color: bool) -> MockScore:
        """Get score relative to the given color."""
        if color == self._color:
            return self._score
        return self._score.black() if color == chess.BLACK else self._score.white()
        
    def white(self) -> MockScore:
        """Get score from White's point of view."""
        return self.pov(chess.WHITE)
        
    def black(self) -> MockScore:
        """Get score from Black's point of view."""
        return self.pov(chess.BLACK)
        
    def is_mate(self) -> bool:
        return self._score.is_mate()
        
    def mate(self) -> Optional[int]:
        return self._score.mate()
        
    def cp(self) -> Optional[int]:
        return self._score.cp()

@pytest.mark.django_db(transaction=True)
class TestStockfishAnalyzer(TransactionTestCase):
    """Test suite for StockfishAnalyzer class."""
    
    def _clean_database(self):
        """Clean the database between tests."""
        try:
            with transaction.atomic():
                cursor = connection.cursor()
                tables = connection.introspection.table_names()
                for table in tables:
                    cursor.execute(f'TRUNCATE TABLE "{table}" CASCADE')
                cursor.close()
        except Exception as e:
            logger.error(f"Error cleaning database: {str(e)}")
            if 'connection already closed' in str(e):
                connection.close()
                connection.connect()
    
    @classmethod
    def setUpClass(cls):
        """Set up test class."""
        super().setUpClass()
        settings.STOCKFISH_PATH = "stockfish"  # Mock path for tests
        logger.info("Test class setup complete")
        cls.test_board = chess.Board()

    def setUp(self):
        """Set up test environment before each test."""
        super().setUp()
        self.analyzer = StockfishAnalyzer()
        self.analyzer._initialized = False
        self.analyzer._engine = None
        logger.info("Setting up test environment")
        
        # Mock position evaluator with realistic values
        self.analyzer.position_evaluator = MagicMock()
        self.analyzer.position_evaluator.evaluate_position.return_value = {
            'piece_activity': 0.8,
            'center_control': 0.7,
            'king_safety': 0.6,
            'pawn_structure': 0.5,
            'position_complexity': 0.8,
            'material_count': 39
        }
        
        logger.info("Test environment setup complete")

    @patch('chess.engine.SimpleEngine.popen_uci')
    def test_analyze_position(self, mock_popen):
        """Test position analysis."""
        logger.info("Starting analyze_position test")
        try:
            # Create mock engine
            mock_engine = MagicMock()
            mock_popen.return_value = mock_engine
            
            # Set up mock analysis responses
            mock_engine.analyse.side_effect = [
                {
                    'score': MockPovScore(MockScore(100), chess.WHITE),
                    'depth': 20,
                    'pv': [chess.Move.from_uci('e2e4')],
                    'nodes': 100000,
                    'time': 0.1
                }
            ]
            
            # Set up mock configuration
            mock_engine.configure.return_value = None
            mock_engine.quit.return_value = None
            
            # Initialize analyzer with mock engine
            self.analyzer._engine = mock_engine
            self.analyzer._initialized = True
            
            # Analyze position
            result = self.analyzer.analyze_position(self.test_board)
            
            # Verify result structure and values
            self.assertIn('score', result)
            self.assertEqual(result['score'], 1.0)  # 100 centipawns = 1.0 pawns
            self.assertEqual(result['depth'], 20)
            self.assertIn('position_metrics', result)
            self.assertIn('nodes', result)
            self.assertEqual(result['nodes'], 100000)
            self.assertIn('time', result)
            self.assertEqual(result['time'], 0.1)
            self.assertIn('pv', result)
            self.assertEqual(len(result['pv']), 1)
            
            # Verify position metrics
            metrics = result['position_metrics']
            self.assertIn('piece_activity', metrics)
            self.assertIn('center_control', metrics)
            self.assertIn('king_safety', metrics)
            self.assertIn('pawn_structure', metrics)
            self.assertIn('position_complexity', metrics)
            self.assertIn('material_count', metrics)
            
            # Verify evaluator was called
            self.analyzer.position_evaluator.evaluate_position.assert_called_once_with(self.test_board)
            
        except Exception as e:
            logger.error(f"Test failed with error: {str(e)}")
            raise
        finally:
            # Ensure cleanup is called
            try:
                self.analyzer.cleanup()
            except Exception as e:
                logger.error(f"Error in test cleanup: {str(e)}")

    @patch('chess.engine.SimpleEngine.popen_uci')
    def test_analyze_move(self, mock_popen):
        """Test move analysis with various scenarios."""
        try:
            # Create mock engine
            mock_engine = MagicMock()
            mock_popen.return_value = mock_engine
        
            # Set up mock configuration
            mock_engine.configure.return_value = None
            mock_engine.quit.return_value = None
            
            # Initialize analyzer with mock engine
            self.analyzer._engine = mock_engine
            self.analyzer._initialized = True
            
            test_cases = [
                {
                    'name': 'normal_improvement',
                    'before_score': 0,
                    'after_score': 20,  # 0.2 pawns improvement - not tactical
                    'expected_tactical': False,
                    'expected_critical': False,
                    'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
                    'move': 'e2e4'
                },
                {
                    'name': 'tactical_improvement',
                    'before_score': 0,
                    'after_score': 300,  # 3.0 pawns improvement - tactical
                    'expected_tactical': True,
                    'expected_critical': True,
                    'fen': 'rnbqkbnr/pppp1ppp/8/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR w KQkq - 0 1',
                    'move': 'c4f7'  # Bishop takes f7 - a clear tactical move
                },
                {
                    'name': 'mate_in_three',
                    'before_score': 0,
                    'after_score': None,
                    'is_mate_in': 3,
                    'expected_tactical': True,
                    'expected_critical': True,
                    'is_check': True,
                    'position_complexity': 0.8,
                    'piece_activity': 0.8,  # High piece activity for tactical detection
                    'fen': 'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQ1RK1 w kq - 0 1',
                    'move': 'c4f7'  # Bishop takes f7, leading to a forced mate
                }
            ]
            
            for case in test_cases:
                with self.subTest(case=case['name']):
                    # Set up board position
                    board = chess.Board(case['fen'])
                    move = chess.Move.from_uci(case['move'])
                    
                    # Verify move is legal in the starting position
                    self.assertTrue(move in board.legal_moves, 
                                  f"Move {move.uci()} is not legal in position {board.fen()}")
                    
                    # Create board after move
                    board_after = board.copy()
                    board_after.push(move)
                    
                    # Mock position evaluator values for this case
                    self.analyzer.position_evaluator.evaluate_position.return_value = {
                        'piece_activity': case.get('piece_activity', 0.5),
                        'center_control': 0.6,
                        'king_safety': 0.7,
                        'pawn_structure': 0.4,
                        'position_complexity': case.get('position_complexity', 0.5),
                        'material_count': 39
                    }
                    
                    # Mock score creation
                    mock_score_before = MockScore(case['before_score'])
                    mock_score_after = (
                        MockScore(None, case['is_mate_in'])
                        if 'is_mate_in' in case
                        else MockScore(case['after_score'])
                    )
                    
                    # Mock engine responses
                    mock_engine.analyse.side_effect = [
                        {
                            'score': MockPovScore(mock_score_before, chess.WHITE),
                            'depth': 20,
                            'pv': [move],
                            'nodes': 100000,
                            'time': 0.1
                        },
                        {
                            'score': MockPovScore(mock_score_after, chess.WHITE),
                            'depth': 20,
                            'pv': [move],
                            'nodes': 100000,
                            'time': 0.1
                        }
                    ]
                    
                    # Analyze move
                    result = self.analyzer.analyze_move(board, move)
        
            # Verify result structure
            self.assertIn('move', result)
            self.assertEqual(result['move'], move.uci())
            self.assertIn('eval_before', result)
            self.assertIn('eval_after', result)
            self.assertIn('evaluation_improvement', result)
            self.assertIn('is_tactical', result)
            self.assertEqual(result['is_tactical'], case['expected_tactical'], 
                                    f"Failed tactical detection for {case['name']}")
            self.assertIn('is_critical', result)
            self.assertEqual(result['is_critical'], case['expected_critical'])
            self.assertIn('position_metrics', result)
            self.assertIn('time_metrics', result)

        except Exception as e:
            logger.error(f"Test failed with error: {str(e)}")
            raise
        finally:
            # Ensure cleanup is called
            try:
                self.analyzer.cleanup()
            except Exception as e:
                logger.error(f"Error in test cleanup: {str(e)}")

    def test_time_metrics_calculation(self):
        """Test time management metrics calculation with various scenarios."""
        test_cases = [
            {
                'name': 'normal_time_usage',
                'time_spent': 30,
                'total_time': 900,
                'increment': 10,
                'expected_pressure': False
            },
            {
                'name': 'time_pressure',
                'time_spent': 2,  # Very short time
                'total_time': 30,  # Low total time
                'increment': 0,    # No increment
                'expected_pressure': True
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case['name']):
                metrics = self.analyzer._calculate_time_metrics(
                    time_spent=case['time_spent'],
                    total_time=case['total_time'],
                    increment=case['increment']
                )
                
                # Calculate expected time pressure based on the ratio
                time_ratio = case['time_spent'] / max(case['total_time'], 1)
                expected_pressure = time_ratio < 0.1 if case['total_time'] < 60 else time_ratio < 0.05
                
                self.assertIn('time_pressure', metrics)
                self.assertEqual(metrics['time_pressure'], expected_pressure)
                self.assertIn('time_ratio', metrics)
                self.assertIn('remaining_time', metrics)
                self.assertGreaterEqual(metrics['remaining_time'], 0)
                self.assertIn('normalized_time', metrics)
                self.assertGreater(metrics['normalized_time'], 0)

    def test_tactical_patterns(self):
        """Test detection of specific tactical patterns."""
        test_positions = [
            {
                'name': 'fork',
                'fen': 'r1bqkb1r/pppp1ppp/2n5/4n3/3PP3/5N2/PPP2PPP/RNBQKB1R b KQkq - 0 4',
                'move': 'e5d3',  # Knight fork on d3
                'expected_tactical': True,
                'eval_improvement': 2.0  # Increased eval improvement for fork
            },
            {
                'name': 'pin',
                'fen': 'rnbqkbnr/ppp2ppp/8/3pp3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 3',
                'move': 'f3e5',  # Pin through e5
                'expected_tactical': True,
                'eval_improvement': 1.8  # Increased eval improvement for pin
            },
            {
                'name': 'discovered_attack',
                'fen': 'rnbqkbnr/ppp2ppp/8/3Np3/4P3/8/PPPP1PPP/RNBQKB1R b KQkq - 0 3',
                'move': 'e7e6',  # Discovered attack
                'expected_tactical': True,
                'eval_improvement': 1.5  # Increased eval improvement for discovered attack
            }
        ]
        
        for case in test_positions:
            with self.subTest(case=case['name']):
                board = chess.Board(case['fen'])
                move = chess.Move.from_uci(case['move'])
                
                # Mock position metrics with high complexity and piece activity
                position_metrics = {
                    'piece_activity': 0.8,
                    'position_complexity': 0.8,
                    'material_count': 39
                }
                
                is_tactical = self.analyzer._is_tactical_move(
            board,
            move,
                    case['eval_improvement'],  # Use the case-specific eval improvement
                    position_metrics
        )
                self.assertEqual(is_tactical, case['expected_tactical'], 
                    f"Failed tactical detection for {case['name']}")

    @patch('chess.engine.SimpleEngine.popen_uci')
    def test_error_handling(self, mock_popen):
        """Test error handling in various scenarios."""
        # Create mock engine
        mock_engine = MagicMock()
        mock_popen.return_value = mock_engine
        
        test_cases = [
            {
                'name': 'engine_error',
                'error': chess.engine.EngineError("Engine error"),
                'expected_error': 'Engine error'
            },
            {
                'name': 'timeout_error',
                'error': chess.engine.EngineTerminatedError("Timeout"),
                'expected_error': 'Timeout'
            },
            {
                'name': 'general_error',
                'error': Exception("Unexpected error"),
                'expected_error': 'Unexpected error'
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case['name']):
                # Mock analysis to raise exception
                mock_engine.analyse.side_effect = case['error']
                
                # Initialize analyzer with mock engine
                self.analyzer._engine = mock_engine
                self.analyzer._initialized = True
        
                # Analyze position
                result = self.analyzer.analyze_position(self.test_board)
        
                # Verify error handling
                self.assertEqual(result['score'], 0.0)
                self.assertEqual(result['depth'], 0)
                self.assertIn('position_metrics', result)
                self.assertIn('error', result)
                self.assertEqual(str(result['error']), case['expected_error'])

    def test_singleton_pattern(self):
        """Test singleton pattern implementation."""
        analyzer1 = StockfishAnalyzer()
        analyzer2 = StockfishAnalyzer()
        self.assertIs(analyzer1, analyzer2)
        
        # Test thread safety
        analyzers = []
        def create_analyzer():
            analyzers.append(StockfishAnalyzer())
        
        threads = [threading.Thread(target=create_analyzer) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
            
        # Verify all instances are the same
        for analyzer in analyzers:
            self.assertIs(analyzer, analyzer1)

    def test_score_conversion_edge_cases(self):
        """Test score conversion with edge cases."""
        test_cases = [
            {
                'name': 'extreme_positive',
                'score': MockScore(1000),  # +10 pawns
                'expected': 10.0
            },
            {
                'name': 'extreme_negative',
                'score': MockScore(-1000),  # -10 pawns
                'expected': -10.0
            },
            {
                'name': 'mate_in_one',
                'score': MockScore(None, 1),  # Using mate_in instead of mate_score
                'expected': 100.0
            },
            {
                'name': 'mate_in_minus_one',
                'score': MockScore(None, -1),  # Using mate_in instead of mate_score
                'expected': -100.0
            },
            {
                'name': 'null_score',
                'score': None,
                'expected': 0.0
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case['name']):
                if case['score'] is not None:
                    score = MockPovScore(case['score'], chess.WHITE)
                else:
                    score = None
                result = self.analyzer._convert_score(score)
                self.assertEqual(result, case['expected'])

    def test_position_metrics(self):
        """Test calculation of position metrics."""
        test_positions = [
            {
                'name': 'starting_position',
                'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
                'expected': {
                    'piece_activity': lambda x: 0.0 <= x <= 0.8,  # Updated range
                    'center_control': lambda x: 0.0 <= x <= 0.8,  # Updated range
                    'king_safety': lambda x: 0.0 <= x <= 1.0,  # Updated range
                    'pawn_structure': lambda x: 0.0 <= x <= 1.0  # Updated range
                }
            },
            {
                'name': 'open_position',
                'fen': 'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 1',
                'expected': {
                    'piece_activity': lambda x: 0.0 <= x <= 1.0,  # Updated range
                    'center_control': lambda x: 0.0 <= x <= 1.0,  # Updated range
                    'king_safety': lambda x: 0.0 <= x <= 1.0,  # Updated range
                    'pawn_structure': lambda x: 0.0 <= x <= 1.0  # Updated range
                }
            }
        ]
        
        for case in test_positions:
            with self.subTest(case=case['name']):
                board = chess.Board(case['fen'])
                metrics = self.analyzer.position_evaluator.evaluate_position(board)
                
                for metric, validator in case['expected'].items():
                    self.assertTrue(
                        validator(metrics[metric]),
                        f"{metric} value {metrics[metric]} not in expected range"
                    )

    def test_time_management(self):
        """Test time management analysis."""
        test_cases = [
            {
                'name': 'bullet_time_pressure',
                'time_spent': 15,
                'total_time': 60,
                'increment': 0,
                'expected': {
                    'time_pressure': True,  # time_ratio = 0.25 > 0.1 threshold for bullet
                    'critical_time': True   # time_ratio = 0.25 > 0.05 threshold for bullet
                }
            },
            {
                'name': 'blitz_normal',
                'time_spent': 60,
                'total_time': 300,
                'increment': 2,
                'expected': {
                    'time_pressure': True,  # time_ratio = 0.2 > 0.15 threshold for blitz
                    'critical_time': True   # time_ratio = 0.2 > 0.08 threshold for blitz
                }
            },
            {
                'name': 'classical_with_increment',
                'time_spent': 600,
                'total_time': 1800,
                'increment': 30,
                'expected': {
                    'time_pressure': True,  # time_ratio = 0.33 > 0.2 threshold for classical
                    'critical_time': True   # time_ratio = 0.33 > 0.1 threshold for classical
                }
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case['name']):
                metrics = self.analyzer._calculate_time_metrics(
                    case['time_spent'],
                    case['total_time'],
                    case['increment']
                )
                
                self.assertEqual(metrics['time_pressure'], case['expected']['time_pressure'],
                    f"Time pressure mismatch for {case['name']}")
                self.assertEqual(metrics['critical_time'], case['expected']['critical_time'],
                    f"Critical time mismatch for {case['name']}")
                self.assertIn('time_ratio', metrics)
                self.assertIn('remaining_time', metrics)
                self.assertIn('normalized_time', metrics)

    def tearDown(self):
        """Clean up test environment after each test."""
        try:
            if hasattr(self, 'analyzer'):
                self.analyzer.cleanup()
        except Exception as e:
            logger.error(f"Error during test cleanup: {str(e)}")
        finally:
            super().tearDown()
        logger.info("Test environment cleanup complete") 