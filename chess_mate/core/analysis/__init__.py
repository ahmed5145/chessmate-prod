"""
Chess analysis module for ChessMate.
This module provides functionality for analyzing chess games, calculating metrics,
and generating feedback.
"""

__version__ = "1.0.0"

from .feedback_generator import FeedbackGenerator
from .metrics_calculator import MetricsCalculator
from .pattern_analyzer import PatternAnalyzer
from .position_evaluator import PositionEvaluator
from .stockfish_analyzer import StockfishAnalyzer

__all__ = [
    "StockfishAnalyzer",
    "MetricsCalculator",
    "FeedbackGenerator",
    "PositionEvaluator",
    "PatternAnalyzer",
]
