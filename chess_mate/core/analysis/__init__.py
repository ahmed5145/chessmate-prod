"""
Chess analysis module for ChessMate.
This module provides functionality for analyzing chess games, calculating metrics,
and generating feedback.
"""

__version__ = '1.0.0'

from .stockfish_analyzer import StockfishAnalyzer
from .metrics_calculator import MetricsCalculator
from .feedback_generator import FeedbackGenerator
from .position_evaluator import PositionEvaluator
from .pattern_analyzer import PatternAnalyzer

__all__ = [
    'StockfishAnalyzer',
    'MetricsCalculator',
    'FeedbackGenerator',
    'PositionEvaluator',
    'PatternAnalyzer',
] 