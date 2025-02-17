"""
Position evaluator for chess games.
Handles evaluation of chess positions and calculation of positional features.
"""

import logging
import chess
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class PositionEvaluator:
    """Evaluates chess positions for various metrics."""

    def evaluate_position(self, board: chess.Board) -> Dict[str, Any]:
        """
        Evaluate a chess position for various metrics.
        
        Args:
            board: A chess.Board object representing the current position
            
        Returns:
            Dictionary containing position metrics
        """
        try:
            return {
                "piece_activity": self._calculate_piece_activity(board),
                "center_control": self._calculate_center_control(board),
                "king_safety": self._calculate_king_safety(board),
                "pawn_structure": self._calculate_pawn_structure(board),
                "position_complexity": self._calculate_position_complexity(board),
                "material_count": self._calculate_material_count(board)
            }
        except Exception as e:
            logger.error(f"Error evaluating position: {str(e)}")
            return self._get_default_metrics()

    def _calculate_piece_activity(self, board: chess.Board) -> float:
        """Calculate piece activity score."""
        try:
            activity_score = 0.0
            total_pieces = 0
            
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece and piece.piece_type != chess.KING:
                    total_pieces += 1
                    # Calculate mobility
                    mobility = len(list(board.attacks(square)))
                    # Normalize mobility score
                    activity_score += mobility / 8.0  # Max mobility per piece
            
            return activity_score / max(1, total_pieces)  # Normalize by piece count
        except Exception as e:
            logger.error(f"Error calculating piece activity: {str(e)}")
            return 0.0

    def _calculate_center_control(self, board: chess.Board) -> float:
        """Calculate center control score."""
        try:
            center_squares = [chess.E4, chess.E5, chess.D4, chess.D5]
            center_score = 0.0
            
            for square in center_squares:
                # Count attackers and defenders
                white_control = len(board.attackers(chess.WHITE, square))
                black_control = len(board.attackers(chess.BLACK, square))
                
                # Add to score based on control difference
                if board.turn == chess.WHITE:
                    center_score += (white_control - black_control) / 4.0
                else:
                    center_score += (black_control - white_control) / 4.0
            
            return max(0.0, min(1.0, (center_score + 4.0) / 8.0))
        except Exception as e:
            logger.error(f"Error calculating center control: {str(e)}")
            return 0.0

    def _calculate_king_safety(self, board: chess.Board) -> float:
        """Calculate king safety score."""
        try:
            safety_score = 0.0
            
            # Get king positions
            white_king_square = board.king(chess.WHITE)
            black_king_square = board.king(chess.BLACK)
            
            if not white_king_square or not black_king_square:
                return 0.0
            
            # Calculate safety for the side to move
            king_square = white_king_square if board.turn == chess.WHITE else black_king_square
            
            # Check pawn shield
            pawn_shield = 0
            for square in board.attacks(king_square):
                if board.piece_at(square) and board.piece_at(square).piece_type == chess.PAWN:
                    pawn_shield += 1
            
            # Check attacking pieces
            attackers = len(board.attackers(not board.turn, king_square))
            
            # Calculate final safety score
            safety_score = (pawn_shield * 0.2) - (attackers * 0.15)
            
            return max(0.0, min(1.0, safety_score + 0.5))
        except Exception as e:
            logger.error(f"Error calculating king safety: {str(e)}")
            return 0.0

    def _calculate_pawn_structure(self, board: chess.Board) -> float:
        """Calculate pawn structure score."""
        try:
            structure_score = 0.0
            
            # Count pawns by file
            files = [0] * 8
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece and piece.piece_type == chess.PAWN:
                    files[chess.square_file(square)] += 1
            
            # Penalize doubled pawns
            doubled_pawns = sum(1 for count in files if count > 1)
            structure_score -= doubled_pawns * 0.1
            
            # Reward connected pawns
            connected_pawns = 0
            for i in range(7):
                if files[i] > 0 and files[i+1] > 0:
                    connected_pawns += 1
            structure_score += connected_pawns * 0.15
            
            return max(0.0, min(1.0, structure_score + 0.5))
        except Exception as e:
            logger.error(f"Error calculating pawn structure: {str(e)}")
            return 0.0

    def _calculate_position_complexity(self, board: chess.Board) -> float:
        """Calculate position complexity score."""
        try:
            complexity = 0.0
            
            # Factor 1: Number of pieces
            piece_count = len(board.piece_map())
            complexity += piece_count / 32.0  # Normalize by max pieces
            
            # Factor 2: Number of legal moves
            legal_moves = len(list(board.legal_moves))
            complexity += legal_moves / 40.0  # Normalize by average moves
            
            # Factor 3: Piece distribution
            files_used = len(set(chess.square_file(square) for square in board.piece_map()))
            ranks_used = len(set(chess.square_rank(square) for square in board.piece_map()))
            complexity += (files_used + ranks_used) / 16.0
            
            return max(0.0, min(1.0, complexity / 3.0))
        except Exception as e:
            logger.error(f"Error calculating position complexity: {str(e)}")
            return 0.0

    def _calculate_material_count(self, board: chess.Board) -> float:
        """Calculate material count."""
        try:
            piece_values = {
                chess.PAWN: 1,
                chess.KNIGHT: 3,
                chess.BISHOP: 3,
                chess.ROOK: 5,
                chess.QUEEN: 9
            }
            
            total_material = 0
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece and piece.piece_type != chess.KING:
                    total_material += piece_values.get(piece.piece_type, 0)
            
            return total_material
        except Exception as e:
            logger.error(f"Error calculating material count: {str(e)}")
            return 0.0

    def _get_default_metrics(self) -> Dict[str, Any]:
        """Return default position metrics."""
        return {
            "piece_activity": 0.0,
            "center_control": 0.0,
            "king_safety": 0.0,
            "pawn_structure": 0.0,
            "position_complexity": 0.0,
            "material_count": 0.0
        }

    PIECE_VALUES = {
        chess.PAWN: 100,
        chess.KNIGHT: 300,
        chess.BISHOP: 300,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 0
    }

    @staticmethod
    def calculate_position_complexity(board: chess.Board) -> float:
        """Calculate the complexity of a position based on various factors."""
        try:
            complexity = 0.0
            
            # Count pieces in the center
            center_squares = [chess.D4, chess.D5, chess.E4, chess.E5]
            center_control = sum(1 for sq in center_squares if board.piece_at(sq) is not None)
            complexity += center_control * 0.25
            
            # Count attacked squares
            white_attacks = sum(1 for sq in chess.SQUARES if board.is_attacked_by(chess.WHITE, sq))
            black_attacks = sum(1 for sq in chess.SQUARES if board.is_attacked_by(chess.BLACK, sq))
            complexity += (white_attacks + black_attacks) * 0.01
            
            # Count piece mobility
            mobility = len(list(board.legal_moves))
            complexity += mobility * 0.05
            
            # Count tactical pieces
            tactical_pieces = 0
            for sq in chess.SQUARES:
                piece = board.piece_at(sq)
                if piece is not None and piece.color is not None:
                    if board.is_pinned(piece.color, sq) or board.attackers(not piece.color, sq):
                        tactical_pieces += 1
            complexity += tactical_pieces * 0.2
            
            # Normalize to 0-100 range
            return min(100.0, max(0.0, complexity * 10))
            
        except Exception as e:
            logger.error(f"Error calculating position complexity: {str(e)}")
            return 0.0

    @staticmethod
    def calculate_piece_activity(board: chess.Board) -> float:
        """Calculate piece activity based on mobility and center control."""
        try:
            activity_score = 0.0
            
            # Evaluate piece mobility
            for sq in chess.SQUARES:
                piece = board.piece_at(sq)
                if piece is None or piece.piece_type == chess.KING:
                    continue
                    
                # Count attacked squares
                if piece.color == chess.WHITE:
                    attacks = sum(1 for s in chess.SQUARES if board.is_attacked_by(chess.WHITE, s))
                else:
                    attacks = sum(1 for s in chess.SQUARES if board.is_attacked_by(chess.BLACK, s))
                activity_score += attacks * 0.1
                
                # Bonus for center control
                if sq in [chess.D4, chess.D5, chess.E4, chess.E5]:
                    activity_score += 2
                elif sq in [chess.C3, chess.C4, chess.C5, chess.C6, chess.F3, chess.F4, chess.F5, chess.F6]:
                    activity_score += 1
                    
            # Normalize score
            return min(100.0, max(0.0, activity_score))
            
        except Exception as e:
            logger.error(f"Error calculating piece activity: {str(e)}")
            return 0.0

    @staticmethod
    def calculate_king_safety(board: chess.Board) -> float:
        """Calculate king safety based on position and pawn shield."""
        try:
            safety_score = 70.0  # Base safety score
            
            for color in [chess.WHITE, chess.BLACK]:
                king_square = board.king(color)
                if king_square is None:
                    continue
                    
                # Check if castled
                if color == chess.WHITE:
                    if king_square in [chess.G1, chess.C1]:
                        safety_score += 10
                else:
                    if king_square in [chess.G8, chess.C8]:
                        safety_score += 10
                        
                # Check pawn shield
                pawn_shield = 0
                rank_mod = 0 if color == chess.WHITE else 7
                file_start = max(0, chess.square_file(king_square) - 1)
                file_end = min(7, chess.square_file(king_square) + 1)
                
                for f in range(file_start, file_end + 1):
                    if board.piece_at(chess.square(f, rank_mod + (1 if color == chess.WHITE else -1))) == chess.Piece(chess.PAWN, color):
                        pawn_shield += 1
                        
                safety_score += pawn_shield * 5
                
                # Penalize for enemy attacks near king
                enemy_attacks = sum(1 for sq in chess.SQUARES 
                                  if abs(chess.square_file(sq) - chess.square_file(king_square)) <= 1
                                  and abs(chess.square_rank(sq) - chess.square_rank(king_square)) <= 1
                                  and board.is_attacked_by(not color, sq))
                safety_score -= enemy_attacks * 3
                
            return min(100.0, max(0.0, safety_score))
            
        except Exception as e:
            logger.error(f"Error calculating king safety: {str(e)}")
            return 50.0

    @staticmethod
    def calculate_pawn_structure(board: chess.Board) -> float:
        """Calculate pawn structure quality."""
        try:
            structure_score = 50.0  # Base score
            
            # Count doubled, isolated, and passed pawns
            doubled_pawns = 0
            isolated_pawns = 0
            passed_pawns = 0
            
            for color in [chess.WHITE, chess.BLACK]:
                pawns = board.pieces(chess.PAWN, color)
                for pawn_square in pawns:
                    file = chess.square_file(pawn_square)
                    rank = chess.square_rank(pawn_square)
                    
                    # Check for doubled pawns
                    if any(sq for sq in pawns 
                          if chess.square_file(sq) == file 
                          and chess.square_rank(sq) != rank):
                        doubled_pawns += 1
                        
                    # Check for isolated pawns
                    adjacent_files = []
                    if file > 0:
                        adjacent_files.append(file - 1)
                    if file < 7:
                        adjacent_files.append(file + 1)
                        
                    if not any(sq for sq in pawns if chess.square_file(sq) in adjacent_files):
                        isolated_pawns += 1
                        
                    # Check for passed pawns
                    is_passed = True
                    enemy_pawns = board.pieces(chess.PAWN, not color)
                    for enemy_square in enemy_pawns:
                        enemy_file = chess.square_file(enemy_square)
                        if abs(enemy_file - file) <= 1:
                            if color == chess.WHITE and chess.square_rank(enemy_square) > rank:
                                is_passed = False
                                break
                            elif color == chess.BLACK and chess.square_rank(enemy_square) < rank:
                                is_passed = False
                                break
                    if is_passed:
                        passed_pawns += 1
            
            # Adjust score based on findings
            structure_score -= doubled_pawns * 5  # Penalty for doubled pawns
            structure_score -= isolated_pawns * 3  # Penalty for isolated pawns
            structure_score += passed_pawns * 7   # Bonus for passed pawns
            
            return min(100.0, max(0.0, structure_score))
            
        except Exception as e:
            logger.error(f"Error calculating pawn structure: {str(e)}")
            return 50.0

    @staticmethod
    def calculate_material_balance(board: chess.Board) -> int:
        """Calculate material balance in centipawns."""
        try:
            material_balance = 0
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece is None:
                    continue
                value = PositionEvaluator.PIECE_VALUES[piece.piece_type]
                if piece.color == chess.WHITE:
                    material_balance += value
                else:
                    material_balance -= value
            return material_balance
        except Exception as e:
            logger.error(f"Error calculating material balance: {str(e)}")
            return 0 

    @staticmethod
    def _calculate_development(board: chess.Board) -> float:
        """Calculate piece development score (0-1)."""
        development_score = 0.0
        total_pieces = 0
        
        # Development weights for different pieces
        weights = {
            chess.KNIGHT: 1.0,  # Knights should be developed early
            chess.BISHOP: 1.0,  # Bishops should be developed early
            chess.QUEEN: 0.5,   # Early queen development might be premature
            chess.ROOK: 0.7     # Rooks become more important after development
        }
        
        for color in [chess.WHITE, chess.BLACK]:
            # Base ranks for development assessment
            home_rank = 0 if color == chess.WHITE else 7
            ideal_ranks = [2, 3] if color == chess.WHITE else [4, 5]
            
            for piece_type, weight in weights.items():
                pieces = board.pieces(piece_type, color)
                for square in pieces:
                    total_pieces += 1
                    rank = chess.square_rank(square)
                    
                    # Reward pieces that have moved from their home rank
                    if rank != home_rank:
                        development_score += weight
                        
                        # Extra reward for pieces in ideal positions
                        if rank in ideal_ranks:
                            development_score += 0.5 * weight
        
        # Normalize score
        return development_score / max(1, total_pieces)

    @staticmethod
    def _calculate_space_advantage(board: chess.Board) -> float:
        """Calculate space advantage score (0-1)."""
        white_space = 0
        black_space = 0
        
        # Define central and extended central squares
        central_squares = [chess.D4, chess.D5, chess.E4, chess.E5]
        extended_squares = [
            chess.C3, chess.C4, chess.C5, chess.C6,
            chess.D3, chess.D4, chess.D5, chess.D6,
            chess.E3, chess.E4, chess.E5, chess.E6,
            chess.F3, chess.F4, chess.F5, chess.F6
        ]
        
        # Calculate control of central squares
        for square in central_squares:
            white_attackers = len(board.attackers(chess.WHITE, square))
            black_attackers = len(board.attackers(chess.BLACK, square))
            
            if white_attackers > black_attackers:
                white_space += 2
            elif black_attackers > white_attackers:
                black_space += 2
                
        # Calculate control of extended squares
        for square in extended_squares:
            white_attackers = len(board.attackers(chess.WHITE, square))
            black_attackers = len(board.attackers(chess.BLACK, square))
            
            if white_attackers > black_attackers:
                white_space += 1
            elif black_attackers > white_attackers:
                black_space += 1
        
        # Calculate advanced pawns
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.piece_type == chess.PAWN:
                rank = chess.square_rank(square)
                if piece.color == chess.WHITE and rank >= 4:
                    white_space += (rank - 3)
                elif piece.color == chess.BLACK and rank <= 3:
                    black_space += (4 - rank)
        
        # Normalize scores
        max_space = len(central_squares) * 2 + len(extended_squares) + 16  # 16 for max pawn advancement
        white_space_score = white_space / max_space
        black_space_score = black_space / max_space
        
        return white_space_score - black_space_score

    @staticmethod
    def _calculate_king_safety(board: chess.Board) -> float:
        """Enhanced calculation of king safety score (0-1)."""
        safety_score = 0.0
        
        for color in [chess.WHITE, chess.BLACK]:
            king_square = board.king(color)
            if king_square is None:
                continue
                
            # Base safety factors
            attackers = len(board.attackers(not color, king_square))
            defenders = len(board.attackers(color, king_square))
            
            # Pawn shield analysis
            pawn_shield_score = 0
            king_file = chess.square_file(king_square)
            king_rank = chess.square_rank(king_square)
            
            # Check pawns in front of king
            shield_squares = []
            if color == chess.WHITE:
                base_rank = king_rank + 1
                shield_ranks = [base_rank, base_rank + 1] if base_rank <= 6 else [base_rank]
            else:
                base_rank = king_rank - 1
                shield_ranks = [base_rank, base_rank - 1] if base_rank >= 1 else [base_rank]
            
            for rank in shield_ranks:
                for file_offset in [-1, 0, 1]:
                    file = king_file + file_offset
                    if 0 <= file <= 7:
                        shield_squares.append(chess.square(file, rank))
            
            for square in shield_squares:
                piece = board.piece_at(square)
                if piece and piece.piece_type == chess.PAWN and piece.color == color:
                    pawn_shield_score += 1
            
            # Castling status
            castling_bonus = 0
            if color == chess.WHITE:
                if board.has_kingside_castling_rights(chess.WHITE):
                    castling_bonus += 0.5
                if board.has_queenside_castling_rights(chess.WHITE):
                    castling_bonus += 0.5
            else:
                if board.has_kingside_castling_rights(chess.BLACK):
                    castling_bonus += 0.5
                if board.has_queenside_castling_rights(chess.BLACK):
                    castling_bonus += 0.5
            
            # Calculate final safety score for this color
            color_safety = (
                (defenders - attackers) * 0.3 +  # Protection vs threats
                pawn_shield_score * 0.4 +        # Pawn shield importance
                castling_bonus * 0.3             # Castling possibilities
            )
            
            # Normalize and add to total
            safety_score += max(0, min(1, color_safety))
        
        return safety_score / 2  # Average of both colors 