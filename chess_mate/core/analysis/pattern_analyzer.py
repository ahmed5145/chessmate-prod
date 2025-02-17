"""
Pattern analyzer for chess games.
Handles recognition and analysis of chess patterns and motifs.
"""

import logging
from typing import List, Dict, Any, Optional
import chess
import chess.pgn
from django.core.cache import cache

logger = logging.getLogger(__name__)

class PatternAnalyzer:
    """Analyzes chess patterns and motifs in games."""

    def __init__(self):
        """Initialize pattern analyzer."""
        self.patterns = {
            'tactical': self._get_tactical_patterns(),
            'positional': self._get_positional_patterns(),
            'endgame': self._get_endgame_patterns()
        }
        self._initialize_methods()

    def _initialize_methods(self):
        """Ensure all required methods are available."""
        required_methods = [
            '_is_pin',
            '_has_isolated_pawn_structure',
            '_is_pawn_endgame'
        ]
        for method in required_methods:
            if not hasattr(self, method):
                logger.error(f"Missing required method: {method}")
                raise AttributeError(f"PatternAnalyzer missing required method: {method}")

    def analyze_game_patterns(self, moves: List[Dict[str, Any]], board: chess.Board) -> Dict[str, Any]:
        """Analyze patterns in a game."""
        try:
            patterns = {
                'tactical': [],
                'positional': [],
                'endgame': [],
                'errors': []  # Track any errors during analysis
            }

            current_board = chess.Board() if board is None else board.copy()

            for move_data in moves:
                try:
                    # Convert move string to chess.Move object
                    move_str = move_data.get('move')
                    if not move_str:
                        continue
                    try:
                        move = chess.Move.from_uci(move_str)
                    except ValueError:
                        patterns['errors'].append(f"Invalid move string: {move_str}")
                        continue

                    # Tactical patterns
                    if self._is_tactical_position(current_board, move):
                        patterns['tactical'].append({
                            'type': 'tactical',
                            'move': str(move),
                            'ply': move_data.get('ply'),
                            'description': 'Position contains tactical themes'
                        })

                    # Positional patterns
                    if self._is_positional_theme(current_board):
                        pos_pattern = self._identify_positional_pattern(current_board)
                        if pos_pattern:
                            patterns['positional'].append({
                                'type': 'positional',
                                'move': str(move),
                                'ply': move_data.get('ply'),
                                'pattern': pos_pattern
                            })

                    # Endgame patterns
                    if self._is_endgame_position(current_board):
                        patterns['endgame'].append({
                            'type': 'endgame',
                            'move': str(move),
                            'ply': move_data.get('ply'),
                            'description': 'Position has endgame characteristics'
                        })

                    # Make the move on the board
                    current_board.push(move)

                except Exception as e:
                    patterns['errors'].append(f"Error analyzing move {move_str}: {str(e)}")
                    continue

            return patterns

        except Exception as e:
            logger.error(f"Error analyzing game patterns: {str(e)}")
            return {
                'tactical': [],
                'positional': [],
                'endgame': [],
                'errors': [f"Fatal error in pattern analysis: {str(e)}"]
            }

    def _is_pin(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if a move involves a pin."""
        try:
            # Get the piece at the from square
            piece = board.piece_at(move.from_square)
            if not piece:
                return False
                
            # Get the king square for the side to move
            king_square = board.king(board.turn)
            if king_square is None:
                return False
                
            # Check if the piece is absolutely pinned
            return board.is_pinned(board.turn, move.from_square)
            
        except Exception as e:
            logger.error(f"Error checking pin: {str(e)}")
            return False

    def _has_isolated_pawn_structure(self, board: chess.Board) -> bool:
        """Check for isolated pawn structures."""
        if not board:
            return False
        try:
            white_pawns = board.pieces(chess.PAWN, chess.WHITE)
            black_pawns = board.pieces(chess.PAWN, chess.BLACK)
            
            for pawns in [white_pawns, black_pawns]:
                for square in pawns:
                    file = chess.square_file(square)
                    # Check adjacent files for pawns
                    has_neighbors = False
                    for adj_file in [file - 1, file + 1]:
                        if 0 <= adj_file <= 7:  # Valid file range
                            for rank in range(8):
                                adj_square = chess.square(adj_file, rank)
                                if board.piece_at(adj_square) == chess.PAWN:
                                    has_neighbors = True
                                    break
                    if not has_neighbors:
                        return True
            return False
        except Exception as e:
            logger.error(f"Error checking pawn structure: {str(e)}")
            return False

    def _is_pawn_endgame(self, board: chess.Board) -> bool:
        """Check if the position is a pawn endgame."""
        if not board:
            return False
        try:
            # Count material for both sides
            white_material = sum(len(board.pieces(piece_type, chess.WHITE)) 
                               for piece_type in [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT])
            black_material = sum(len(board.pieces(piece_type, chess.BLACK)) 
                               for piece_type in [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT])
            
            # Check if only kings and pawns remain
            return white_material == 0 and black_material == 0 and (
                len(board.pieces(chess.PAWN, chess.WHITE)) > 0 or 
                len(board.pieces(chess.PAWN, chess.BLACK)) > 0
            )
        except Exception as e:
            logger.error(f"Error checking pawn endgame: {str(e)}")
            return False

    def _is_tactical_position(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if position contains tactical themes."""
        try:
            # Check for basic tactical elements
            is_capture = board.is_capture(move)
            gives_check = board.gives_check(move)
            is_attacked = bool(board.attackers(not board.turn, move.to_square))
            
            return is_capture or gives_check or is_attacked
            
        except Exception as e:
            logger.error(f"Error checking tactical position: {str(e)}")
            return False

    def _is_positional_theme(self, board: chess.Board) -> bool:
        """Check if position contains positional themes."""
        try:
            # Check for pawn structure themes
            has_isolated_pawns = any(self._is_isolated_pawn(board, sq) for sq in chess.SQUARES 
                                   if board.piece_at(sq) and board.piece_at(sq).piece_type == chess.PAWN)
            
            # Check for piece placement themes
            has_outpost = any(self._is_outpost(board, sq) for sq in chess.SQUARES 
                            if board.piece_at(sq) and board.piece_at(sq).piece_type in [chess.KNIGHT, chess.BISHOP])
            
            return has_isolated_pawns or has_outpost
            
        except Exception as e:
            logger.error(f"Error checking positional theme: {str(e)}")
            return False

    def _is_endgame_position(self, board: chess.Board) -> bool:
        """Check if position is an endgame position."""
        try:
            # Count major pieces
            queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK))
            rooks = len(board.pieces(chess.ROOK, chess.WHITE)) + len(board.pieces(chess.ROOK, chess.BLACK))
            minors = (len(board.pieces(chess.BISHOP, chess.WHITE)) + len(board.pieces(chess.BISHOP, chess.BLACK)) +
                     len(board.pieces(chess.KNIGHT, chess.WHITE)) + len(board.pieces(chess.KNIGHT, chess.BLACK)))
            
            # Consider it endgame if:
            # 1. No queens and 2 or fewer minor pieces
            # 2. Only one queen per side and no other pieces
            # 3. Two or fewer minor pieces per side and no other major pieces
            return (queens == 0 and minors <= 2) or \
                   (queens <= 2 and rooks == 0 and minors == 0) or \
                   (queens == 0 and rooks == 0 and minors <= 4)
                   
        except Exception as e:
            logger.error(f"Error checking endgame position: {str(e)}")
            return False

    def _identify_tactical_pattern(self, board: chess.Board, move: chess.Move) -> Optional[Dict[str, Any]]:
        """Identify specific tactical pattern in position."""
        try:
            patterns = []
            
            # Check for pin
            if self._is_pin(board, move):
                patterns.append({
                    'name': 'Pin',
                    'description': 'A piece is pinned against a more valuable piece'
                })
            
            # Check for fork
            if self._is_fork(board, move):
                patterns.append({
                    'name': 'Fork',
                    'description': 'A piece attacks two or more enemy pieces simultaneously'
                })
            
            # Check for discovered attack
            if self._is_discovered_attack(board, move):
                patterns.append({
                    'name': 'Discovered Attack',
                    'description': 'Moving one piece reveals an attack from another'
                })
            
            return patterns[0] if patterns else None
            
        except Exception as e:
            logger.error(f"Error identifying tactical pattern: {str(e)}")
            return None

    def _identify_positional_pattern(self, board: chess.Board) -> Optional[Dict[str, Any]]:
        """Identify specific positional pattern in position."""
        try:
            patterns = []
            
            # Check for isolated pawn structure
            if self._has_isolated_pawn_structure(board):
                patterns.append({
                    'name': 'Isolated Pawn Structure',
                    'description': 'Position contains isolated pawns affecting strategy'
                })
            
            # Check for outpost
            if self._has_knight_outpost(board):
                patterns.append({
                    'name': 'Knight Outpost',
                    'description': 'Strong knight position supported by pawns'
                })
            
            # Check for good/bad bishop
            bishop_quality = self._evaluate_bishop_quality(board)
            if bishop_quality:
                patterns.append(bishop_quality)
            
            return patterns[0] if patterns else None
            
        except Exception as e:
            logger.error(f"Error identifying positional pattern: {str(e)}")
            return None

    def _identify_endgame_pattern(self, board: chess.Board, move: chess.Move) -> Optional[Dict[str, Any]]:
        """Identify specific endgame pattern in position."""
        try:
            patterns = []
            
            # Check for pawn endgame patterns
            if self._is_pawn_endgame(board):
                if self._has_passed_pawn(board):
                    patterns.append({
                        'name': 'Passed Pawn Endgame',
                        'description': 'Critical passed pawn in pawn endgame'
                    })
                    
            # Check for king and pawn endgame patterns
            if self._is_king_and_pawn_endgame(board):
                if self._has_opposition(board):
                    patterns.append({
                        'name': 'King Opposition',
                        'description': 'Kings in opposition in pawn endgame'
                    })
            
            # Check for rook endgame patterns
            if self._is_rook_endgame(board):
                if self._is_lucena_position(board):
                    patterns.append({
                        'name': 'Lucena Position',
                        'description': 'Classic rook endgame winning position'
                    })
                elif self._is_philidor_position(board):
                    patterns.append({
                        'name': 'Philidor Position',
                        'description': 'Classic rook endgame drawing position'
                    })
            
            return patterns[0] if patterns else None
            
        except Exception as e:
            logger.error(f"Error identifying endgame pattern: {str(e)}")
            return None

    def _summarize_patterns(self, patterns: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Summarize found patterns into analysis."""
        try:
            return {
                'tactical_patterns': self._summarize_tactical_patterns(patterns['tactical']),
                'positional_patterns': self._summarize_positional_patterns(patterns['positional']),
                'endgame_patterns': self._summarize_endgame_patterns(patterns['endgame']),
                'overall_assessment': self._generate_pattern_assessment(patterns)
            }
        except Exception as e:
            logger.error(f"Error summarizing patterns: {str(e)}")
            return self._get_default_pattern_analysis()

    def _get_default_pattern_analysis(self) -> Dict[str, Any]:
        """Return default pattern analysis when analysis fails."""
        return {
            'tactical_patterns': [],
            'positional_patterns': [],
            'endgame_patterns': [],
            'overall_assessment': 'Pattern analysis not available'
        }

    def _get_tactical_patterns(self) -> Dict[str, Any]:
        """Get dictionary of tactical patterns to look for."""
        return {
            'pin': {'name': 'Pin', 'value': 1},
            'fork': {'name': 'Fork', 'value': 1},
            'discovered_attack': {'name': 'Discovered Attack', 'value': 1},
            'skewer': {'name': 'Skewer', 'value': 1},
            'overload': {'name': 'Overload', 'value': 1}
        }

    def _get_positional_patterns(self) -> Dict[str, Any]:
        """Get dictionary of positional patterns to look for."""
        return {
            'isolated_pawn': {'name': 'Isolated Pawn', 'value': -0.5},
            'backward_pawn': {'name': 'Backward Pawn', 'value': -0.5},
            'passed_pawn': {'name': 'Passed Pawn', 'value': 1},
            'knight_outpost': {'name': 'Knight Outpost', 'value': 0.5},
            'bishop_pair': {'name': 'Bishop Pair', 'value': 0.5}
        }

    def _get_endgame_patterns(self) -> Dict[str, Any]:
        """Get dictionary of endgame patterns to look for."""
        return {
            'lucena': {'name': 'Lucena Position', 'value': 1},
            'philidor': {'name': 'Philidor Position', 'value': 0},
            'opposition': {'name': 'Opposition', 'value': 0.5},
            'triangulation': {'name': 'Triangulation', 'value': 0.5},
            'zugzwang': {'name': 'Zugzwang', 'value': 1}
        }

    def _is_isolated_pawn(self, board: chess.Board, square: chess.Square) -> bool:
        """Check if a pawn is isolated."""
        try:
            if not board.piece_at(square) or board.piece_at(square).piece_type != chess.PAWN:
                return False
                
            file = chess.square_file(square)
            color = board.piece_at(square).color
            
            # Check adjacent files for friendly pawns
            for adj_file in [file - 1, file + 1]:
                if adj_file < 0 or adj_file > 7:
                    continue
                    
                # Check entire file for friendly pawns
                for rank in range(8):
                    adj_square = chess.square(adj_file, rank)
                    piece = board.piece_at(adj_square)
                    if piece and piece.piece_type == chess.PAWN and piece.color == color:
                        return False
                        
            return True
            
        except Exception as e:
            logger.error(f"Error checking isolated pawn: {str(e)}")
            return False

    def _is_outpost(self, board: chess.Board, square: chess.Square) -> bool:
        """Check if a square is a potential outpost."""
        try:
            piece = board.piece_at(square)
            if not piece or piece.piece_type not in [chess.KNIGHT, chess.BISHOP]:
                return False
                
            color = piece.color
            file = chess.square_file(square)
            rank = chess.square_rank(square)
            
            # Check if square is protected by friendly pawn
            pawn_protectors = False
            for adj_file in [file - 1, file + 1]:
                if adj_file < 0 or adj_file > 7:
                    continue
                    
                protector_rank = rank - 1 if color == chess.WHITE else rank + 1
                if 0 <= protector_rank <= 7:
                    protector_square = chess.square(adj_file, protector_rank)
                    protector = board.piece_at(protector_square)
                    if protector and protector.piece_type == chess.PAWN and protector.color == color:
                        pawn_protectors = True
                        break
            
            # Check if square can be attacked by enemy pawns
            can_be_attacked = False
            for adj_file in [file - 1, file + 1]:
                if adj_file < 0 or adj_file > 7:
                    continue
                    
                for attack_rank in range(rank + (1 if color == chess.WHITE else -1), 
                                      8 if color == chess.WHITE else -1, 
                                      1 if color == chess.WHITE else -1):
                    if not (0 <= attack_rank <= 7):
                        continue
                        
                    attacker_square = chess.square(adj_file, attack_rank)
                    attacker = board.piece_at(attacker_square)
                    if attacker and attacker.piece_type == chess.PAWN and attacker.color != color:
                        can_be_attacked = True
                        break
                        
            return pawn_protectors and not can_be_attacked
            
        except Exception as e:
            logger.error(f"Error checking outpost: {str(e)}")
            return False

    def _summarize_tactical_patterns(self, patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize tactical patterns found in the game."""
        if not patterns:
            return {'count': 0, 'patterns': []}
            
        pattern_counts = {}
        for pattern in patterns:
            name = pattern['name']
            pattern_counts[name] = pattern_counts.get(name, 0) + 1
            
        return {
            'count': len(patterns),
            'patterns': [{'name': name, 'count': count} for name, count in pattern_counts.items()]
        }

    def _summarize_positional_patterns(self, patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize positional patterns found in the game."""
        if not patterns:
            return {'count': 0, 'patterns': []}
            
        pattern_counts = {}
        for pattern in patterns:
            name = pattern['name']
            pattern_counts[name] = pattern_counts.get(name, 0) + 1
            
        return {
            'count': len(patterns),
            'patterns': [{'name': name, 'count': count} for name, count in pattern_counts.items()]
        }

    def _summarize_endgame_patterns(self, patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize endgame patterns found in the game."""
        if not patterns:
            return {'count': 0, 'patterns': []}
            
        pattern_counts = {}
        for pattern in patterns:
            name = pattern['name']
            pattern_counts[name] = pattern_counts.get(name, 0) + 1
            
        return {
            'count': len(patterns),
            'patterns': [{'name': name, 'count': count} for name, count in pattern_counts.items()]
        }

    def _generate_pattern_assessment(self, patterns: Dict[str, List[Dict[str, Any]]]) -> str:
        """Generate overall assessment based on patterns found."""
        total_patterns = sum(len(p) for p in patterns.values())
        if total_patterns == 0:
            return "No significant patterns identified"
            
        tactical_count = len(patterns['tactical'])
        positional_count = len(patterns['positional'])
        endgame_count = len(patterns['endgame'])
        
        if tactical_count > positional_count and tactical_count > endgame_count:
            return "Predominantly tactical play with multiple combinations"
        elif positional_count > tactical_count and positional_count > endgame_count:
            return "Strong positional play with strategic themes"
        elif endgame_count > tactical_count and endgame_count > positional_count:
            return "Technical endgame play with classic patterns"
        else:
            return "Balanced play with mixed tactical and positional elements" 