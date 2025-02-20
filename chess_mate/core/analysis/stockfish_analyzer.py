"""
Stockfish engine analyzer for chess games.
Handles all interactions with the Stockfish chess engine.
"""

import logging
import chess
import chess.engine
from typing import Dict, Any, Optional, Union, cast
from django.conf import settings
import threading
import time
import atexit
from .position_evaluator import PositionEvaluator

logger = logging.getLogger(__name__)

class StockfishAnalyzer:
    """Handles analysis of chess positions using Stockfish engine."""

    _instance = None
    _engine = None
    _lock = threading.Lock()
    _last_used: float = 0.0  # Changed to float for time.time()
    _TIMEOUT: int = 30  # Seconds before engine is considered idle
    _initialized = False

    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(StockfishAnalyzer, cls).__new__(cls)
                    cls._instance._initialized = False
                    atexit.register(cls._instance.cleanup)
        return cls._instance

    def __init__(self):
        """Initialize the analyzer."""
        self.position_evaluator = PositionEvaluator()
        self._init_engine()

    def _init_engine(self):
        """Initialize the Stockfish engine."""
        try:
            # Try multiple common paths for Stockfish
            stockfish_paths = [
                "C:/Users/PCAdmin/Downloads/stockfish-windows-x86-64-avx2/stockfish/stockfish-windows-x86-64-avx2.exe",
                "stockfish",  # If in PATH
                settings.STOCKFISH_PATH,  # From Django settings
                "stockfish.exe",  # Windows specific
                r"C:\Program Files\Stockfish\stockfish.exe",  # Common Windows install location
                "/usr/local/bin/stockfish",  # Common Unix location
                "/usr/games/stockfish"  # Another common Unix location
            ]
            
            for path in stockfish_paths:
                try:
                    self._engine = chess.engine.SimpleEngine.popen_uci(path)
                    if self._engine:
                        self._engine.configure({"Threads": 4, "Hash": 128})
                        self._initialized = True
                        logger.info(f"Successfully initialized Stockfish engine from path: {path}")
                        return
                except Exception as e:
                    logger.debug(f"Failed to initialize Stockfish at path {path}: {str(e)}")
                    continue
                    
            raise ValueError("Could not find Stockfish engine in any standard location")
            
        except Exception as e:
            logger.error(f"Failed to initialize Stockfish engine: {str(e)}")
            self._engine = None
            self._initialized = False

    def _initialize_engine(self) -> None:
        """Initialize the Stockfish engine with configured settings."""
        if self._initialized and self._engine:
            return

        try:
            with self._lock:
                if self._initialized and self._engine:
                    return

                # Clean up any existing engine first
                self._cleanup_engine()

                stockfish_path = settings.STOCKFISH_PATH
                if not stockfish_path:
                    raise ValueError("STOCKFISH_PATH not configured")

                try:
                    # Create engine instance
                    self._engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
                    if not self._engine:
                        raise ValueError("Failed to create engine instance")
                    
                    # Configure engine with settings from Django settings
                    config = {
                        'Threads': getattr(settings, 'STOCKFISH_THREADS', 1),
                        'Hash': getattr(settings, 'STOCKFISH_HASH_SIZE', 128),
                        'Skill Level': getattr(settings, 'STOCKFISH_SKILL_LEVEL', 20),
                        'Move Overhead': getattr(settings, 'STOCKFISH_MOVE_OVERHEAD', 30),
                        'Clear Hash': True
                    }
                    
                    # Apply configuration
                    self._engine.configure(config)
                    
                    # Test engine
                    self._test_engine()
                    
                except Exception as e:
                    self._cleanup_engine()
                    raise ValueError(f"Failed to initialize engine: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to initialize Stockfish engine: {str(e)}")
            self._cleanup_engine()
            raise

    def _test_engine(self) -> None:
        """Test engine with a simple position."""
        if not self._engine:
            raise ValueError("Engine not initialized")
            
        try:
            # Create test position
            test_board = chess.Board()
            engine = cast(chess.engine.SimpleEngine, self._engine)
            
            # Use a very short time limit for the test
            limit = chess.engine.Limit(time=0.1)
            
            # Get analysis
            info = engine.analyse(test_board, limit)
            
            # Verify the analysis result has required fields
            if not info:
                raise ValueError("Engine test failed - no analysis result")
            if 'score' not in info:
                raise ValueError("Engine test failed - no score in analysis")
            if 'pv' not in info:
                raise ValueError("Engine test failed - no principal variation")
                
            # Test successful
            self._initialized = True
            logger.info("Engine test successful")
            
        except chess.engine.EngineTerminatedError:
            logger.error("Engine terminated unexpectedly during test")
            self._cleanup_engine()
            raise ValueError("Engine terminated unexpectedly during test")
        except chess.engine.EngineError as e:
            logger.error(f"Engine error during test: {str(e)}")
            self._cleanup_engine()
            raise ValueError(f"Engine error during test: {str(e)}")
        except Exception as e:
            logger.error(f"Engine test failed: {str(e)}")
            self._cleanup_engine()
            raise ValueError(f"Engine test failed: {str(e)}")

    def analyze_position(self, board: chess.Board, depth: int = 20) -> Dict[str, Any]:
        """Analyze a chess position using Stockfish engine."""
        try:
            if not self._engine or not self._initialized:
                # Try to initialize engine if not already initialized
                self._init_engine()
                if not self._engine or not self._initialized:
                    return self._create_neutral_evaluation("Engine not initialized")

            # Use analyse instead of evaluate_position
            result = self._engine.analyse(board, chess.engine.Limit(depth=depth))
            
            # Extract score
            score = result.get('score')
            if not score:
                return self._create_neutral_evaluation("No score in analysis result")
                
            # Convert score to float value
            score_value = self._convert_score(score)
            
            # Calculate position metrics
            position_metrics = self.position_evaluator.evaluate_position(board)
            
            # Create complete analysis result
            analysis_result = {
                'score': score_value,
                'depth': result.get('depth', 0),
                'nodes': result.get('nodes', 0),
                'time': result.get('time', 0.0),
                'pv': [move.uci() for move in result.get('pv', [])],
                'position_metrics': position_metrics,
                'timestamp': time.time()
            }
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing position: {str(e)}")
            return self._create_neutral_evaluation(str(e))

    def _convert_score(self, score: Union[chess.engine.Score, int, float]) -> float:
        """Convert chess.engine.Score to float value."""
        try:
            if hasattr(score, 'white'):
                # Handle both PovScore and MockPovScore
                score = score.white()
                
            if hasattr(score, 'is_mate') and hasattr(score, 'cp'):
                # Handle both Score and MockScore
                if score.is_mate():
                mate_score = score.mate()
                if mate_score is None:
                        return 0.0
                    # Return a high value for mate, scaled by number of moves
                    return 100.0 if mate_score > 0 else -100.0
                
                cp_score = score.cp()
                if cp_score is None:
                    return 0.0
                
                # Convert centipawns to pawns (divide by 100)
                return float(cp_score) / 100.0
            
            elif isinstance(score, (int, float)):
                # Assume the score is in centipawns
                return float(score) / 100.0
                
            logger.warning(f"Unknown score type: {type(score)}")
            return 0.0
            
        except Exception as e:
            logger.error(f"Error converting score: {str(e)}")
            return 0.0

    def _create_neutral_evaluation(self, error_msg: str = None) -> Dict[str, Any]:
        """Create a neutral evaluation when analysis fails."""
        result = {
            "score": 0.0,
            "depth": 0,
            "nodes": 0,
            "time": 0.0,
            "pv": [],
            "position_metrics": {
                "piece_activity": 0.0,
                "center_control": 0.0,
                "king_safety": 0.0,
                "pawn_structure": 0.0,
                "position_complexity": 0.0,
                "material_count": 0.0
            },
            "timestamp": time.time()
        }
        if error_msg:
            result["error"] = error_msg
        return result

    def _cleanup_engine(self) -> None:
        """Internal method to clean up engine resources."""
        with self._lock:
            if self._engine:
                try:
                    self._engine.quit()
                except Exception as e:
                    logger.error(f"Error closing engine: {str(e)}")
                finally:
                    self._engine = None
                    self._initialized = False
                    logger.info("Engine cleaned up")

    def cleanup(self) -> None:
        """Public method to clean up engine resources."""
        try:
        self._cleanup_engine()
        except Exception as e:
            logger.error(f"Error in cleanup: {str(e)}")
        finally:
            self._initialized = False
            self._engine = None

    def cleanup_if_idle(self) -> None:
        """Close engine if it has been idle for too long."""
        try:
        if self._initialized and time.time() - self._last_used > self._TIMEOUT:
            self.cleanup()
        except Exception as e:
            logger.error(f"Error in cleanup_if_idle: {str(e)}")
            self.cleanup()  # Force cleanup on error

    def __del__(self):
        """Ensure engine is closed on deletion."""
        try:
        self.cleanup()
        except Exception as e:
            logger.error(f"Error in __del__: {str(e)}")

    def analyze_move(self, board: chess.Board, move: chess.Move, time_spent: float = 0, total_time: float = 900, increment: float = 0) -> Dict[str, Any]:
        """Analyze a chess move using Stockfish engine."""
        try:
            # Get evaluation before move
            eval_before = self.analyze_position(board)
            
            # Make the move on a copy of the board
            board_after = board.copy()
            board_after.push(move)
            
            # Get evaluation after move
            eval_after = self.analyze_position(board_after)
            
            # Calculate evaluation improvement
            eval_improvement = eval_after['score'] - eval_before['score']
            
            # Get position metrics
            position_metrics = eval_after.get('position_metrics', {})
            
            # Determine if move is tactical or critical
            is_tactical = self._is_tactical_move(board, move, eval_improvement, position_metrics)
            is_critical = self._is_critical_move(board, move, eval_before['score'], eval_after['score'])
            
            return {
                'move': move.uci(),
                'eval_before': eval_before['score'],
                'eval_after': eval_after['score'],
                'evaluation_improvement': eval_improvement,
                'depth': eval_after.get('depth', 0),
                'is_tactical': is_tactical,
                'is_critical': is_critical,
                'position_metrics': position_metrics,
                'time_metrics': self._calculate_time_metrics(time_spent, total_time, increment),
                'time_spent': time_spent,
                'material_change': self._calculate_material_change(board_after, move),
                'is_check': board_after.is_check(),
                'is_capture': board_after.is_capture(move)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing move: {str(e)}")
            return {
                'move': move.uci(),
                'eval_before': 0,
                'eval_after': 0,
                'evaluation_improvement': 0,
                'depth': 0,
                'is_tactical': False,
                'is_critical': False,
                'position_metrics': {},
                'time_metrics': self._calculate_time_metrics(time_spent, total_time, increment),
                'time_spent': time_spent,
                'material_change': 0,
                'is_check': False,
                'is_capture': False
            }
            
    def _is_tactical_move(self, board: chess.Board, move: chess.Move, eval_improvement: float, position_metrics: Dict[str, Any]) -> bool:
        """Determine if a move is tactical."""
        try:
            # Validate move first
            if move not in board.legal_moves:
                logger.error(f"Move {move.uci()} is not legal in position {board.fen()}")
                return False

            # Create a copy of the board for analysis
            board_copy = board.copy()
            
            # Store the piece at the destination square before the move
            captured_piece = board_copy.piece_at(move.to_square)
            is_capture = board_copy.is_capture(move)
            
            # Make the move
            board_copy.push(move)
            
            # Base conditions that always make a move tactical
            if is_capture:
                if captured_piece:
                    piece_type = captured_piece.piece_type
                    if piece_type in [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]:
                        return True  # Capturing major or minor piece is always tactical
                    
            # Mate threats are always tactical
            if board_copy.is_checkmate():
                return True
                
            # Very significant evaluation change alone can make a move tactical
            if abs(eval_improvement) >= 1.0:  # Reduced from 1.5 to 1.0 pawns
                return True
            
            # Get piece activity and position complexity
            piece_activity = position_metrics.get('piece_activity', 0)
            position_complexity = position_metrics.get('position_complexity', 0)
            
            # Complex position with significant evaluation change
            if position_complexity > 0.6 and abs(eval_improvement) >= 0.8:  # Reduced from 1.0 to 0.8
                return True
            
            # High piece activity in a complex position with moderate eval change
            if piece_activity > 0.6 and position_complexity > 0.5 and abs(eval_improvement) >= 0.6:  # Reduced from 0.8 to 0.6
                return True
            
            # Check positions with significant eval change
            if board.is_check() or board_copy.is_check():
                if abs(eval_improvement) >= 0.4:  # Reduced from 0.5 to 0.4
                    return True
            
            # Capture with significant eval improvement
            if is_capture and abs(eval_improvement) >= 0.6:  # Reduced from 0.8 to 0.6
                return True
                
            # Additional tactical patterns
            if self._is_fork(board_copy, move) or self._is_pin(board_copy, move):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in _is_tactical_move: {str(e)}")
            return False

    def _is_fork(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if a move creates a fork."""
        try:
            moving_piece = board.piece_at(move.from_square)
            if not moving_piece:
                return False
                
            # Count attacked pieces after the move
            attacked_pieces = 0
            attacked_values = 0
            
            for square in chess.SQUARES:
                attacked_piece = board.piece_at(square)
                if attacked_piece and board.is_attacked_by(not board.turn, square):
                    attacked_pieces += 1
                    piece_values = {
                        chess.PAWN: 1,
                        chess.KNIGHT: 3,
                        chess.BISHOP: 3,
                        chess.ROOK: 5,
                        chess.QUEEN: 9
                    }
                    attacked_values += piece_values.get(attacked_piece.piece_type, 0)
            
            # Consider it a fork if attacking multiple pieces with significant value
            return attacked_pieces >= 2 and attacked_values >= 6
            
        except Exception as e:
            logger.error(f"Error in _is_fork: {str(e)}")
            return False

    def _is_pin(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if a move creates a pin."""
        try:
            # Get the piece that moved
            moving_piece = board.piece_at(move.from_square)
            if not moving_piece:
                return False
                
            # Check if the moving piece is a sliding piece
            if moving_piece.piece_type not in [chess.BISHOP, chess.ROOK, chess.QUEEN]:
                return False
                
            # Look for pieces along the attack lines
            rays = chess.Board.attacks_mask(move.to_square, moving_piece.piece_type, board.occupied)
            
            pinned_pieces = 0
            for square in chess.scan_reversed(rays):
                piece = board.piece_at(square)
                if piece:
                    if piece.color != board.turn:  # Enemy piece
                        pinned_pieces += 1
                        if pinned_pieces >= 2:  # Found a pin
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in _is_pin: {str(e)}")
            return False
        
    def _is_critical_move(self, board: chess.Board, move: chess.Move, eval_before: float, eval_after: float) -> bool:
        """Determine if a move is critical."""
        try:
            # Large evaluation change
            if abs(eval_after - eval_before) > 2.0:
                return True
                
            # Position is already critical
            if abs(eval_before) > 2.0 or abs(eval_after) > 2.0:
                return True
                
            # Check or mate
            board_after = board.copy()
            board_after.push(move)
            if board.is_check() or board_after.is_check() or board_after.is_checkmate():
                return True
                
            # Capture of major piece
            if board.is_capture(move):
                captured_piece = board.piece_at(move.to_square)
                if captured_piece and captured_piece.piece_type in [chess.QUEEN, chess.ROOK]:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in _is_critical_move: {str(e)}")
            return False
        
    def _calculate_time_metrics(self, time_spent: float, total_time: float, increment: float) -> Dict[str, Any]:
        """Calculate time management metrics."""
        try:
            # Calculate time pressure thresholds based on game phase
            if total_time < 60:  # Bullet/Ultra-bullet
                pressure_threshold = 0.1
                critical_threshold = 0.05
            elif total_time < 300:  # Blitz
                pressure_threshold = 0.15
                critical_threshold = 0.08
            else:  # Rapid/Classical
                pressure_threshold = 0.2
                critical_threshold = 0.1
                
            # Calculate time ratio considering increment
            effective_total = max(total_time + increment, 1)
            time_ratio = time_spent / effective_total
            
            # Determine time pressure
            time_pressure = time_ratio < pressure_threshold
            critical_time = time_ratio < critical_threshold
            
            # Calculate normalized time (0-1 scale)
            normalized_time = min(1.0, time_ratio / pressure_threshold)
            
            return {
                'time_pressure': time_pressure,
                'critical_time': critical_time,
                'time_ratio': time_ratio,
                'remaining_time': total_time - time_spent + increment,
                'normalized_time': normalized_time
            }
        except Exception as e:
            logger.error(f"Error calculating time metrics: {str(e)}")
            return {
                'time_pressure': False,
                'critical_time': False,
                'time_ratio': 0.0,
                'remaining_time': total_time,
                'normalized_time': 0.0
            }
            
    def _calculate_material_change(self, board: chess.Board, move: chess.Move) -> int:
        """Calculate material change after a move."""
        try:
            # Get captured piece value if any
            captured_piece = board.piece_at(move.to_square)
            if captured_piece:
                piece_values = {
                    chess.PAWN: 1,
                    chess.KNIGHT: 3,
                    chess.BISHOP: 3,
                    chess.ROOK: 5,
                    chess.QUEEN: 9
                }
                return piece_values.get(captured_piece.piece_type, 0)
            return 0
        except Exception as e:
            logger.error(f"Error calculating material change: {str(e)}")
            return 0 

    def _calculate_piece_activity(self, board: chess.Board) -> float:
        """Calculate piece activity score (0.0 to 1.0)."""
        try:
            total_squares = 64
            controlled_squares = 0
            
            for square in chess.SQUARES:
                # Count squares attacked by either side
                if board.attackers(chess.WHITE, square) or board.attackers(chess.BLACK, square):
                    controlled_squares += 1
                    
            # Normalize to 0-1 range
            return min(1.0, controlled_squares / total_squares)
            
        except Exception as e:
            logger.error(f"Error calculating piece activity: {str(e)}")
            return 0.5

    def _calculate_position_complexity(self, board: chess.Board) -> float:
        """Calculate position complexity score (0.0 to 1.0)."""
        try:
            complexity_score = 0.0
            total_pieces = len(board.piece_map())
            
            # Factor 1: Number of legal moves (more moves = more complex)
            num_legal_moves = len(list(board.legal_moves))
            moves_score = min(1.0, num_legal_moves / 40)  # Normalize to 0-1
            complexity_score += moves_score * 0.4
            
            # Factor 2: Piece density in center
            center_squares = [chess.D4, chess.D5, chess.E4, chess.E5]
            center_pieces = sum(1 for sq in center_squares if board.piece_at(sq))
            center_score = center_pieces / 4
            complexity_score += center_score * 0.3
            
            # Factor 3: Piece interaction
            interaction_score = self._calculate_piece_activity(board)
            complexity_score += interaction_score * 0.3
            
            return min(1.0, complexity_score)
            
        except Exception as e:
            logger.error(f"Error calculating position complexity: {str(e)}")
            return 0.5

    def _calculate_material_count(self, board: chess.Board) -> int:
        """Calculate total material count on the board."""
        try:
            piece_values = {
                chess.PAWN: 1,
                chess.KNIGHT: 3,
                chess.BISHOP: 3,
                chess.ROOK: 5,
                chess.QUEEN: 9
            }
            
            total_material = 0
            
            for piece_type in piece_values:
                # Count white pieces
                white_pieces = len(board.pieces(piece_type, chess.WHITE))
                total_material += white_pieces * piece_values[piece_type]
                
                # Count black pieces
                black_pieces = len(board.pieces(piece_type, chess.BLACK))
                total_material += black_pieces * piece_values[piece_type]
            
            return total_material
            
        except Exception as e:
            logger.error(f"Error calculating material count: {str(e)}")
            return 32  # Default starting material count 