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
                            'description': self._get_tactical_description(current_board, move)
                        })

                    # Positional patterns
                    if self._is_positional_theme(current_board):
                        pos_pattern = self._identify_positional_pattern(current_board)
                        if pos_pattern:
                            patterns['positional'].append({
                                'type': 'positional',
                                'move': str(move),
                                'ply': move_data.get('ply'),
                                'pattern': pos_pattern,
                                'description': self._get_positional_description(pos_pattern)
                            })

                    # Endgame patterns
                    if self._is_endgame_position(current_board):
                        end_pattern = self._identify_endgame_pattern(current_board)
                        if end_pattern:
                        patterns['endgame'].append({
                            'type': 'endgame',
                            'move': str(move),
                            'ply': move_data.get('ply'),
                                'pattern': end_pattern,
                                'description': self._get_endgame_description(end_pattern)
                        })

                    # Make the move on the board
                    current_board.push(move)

                except Exception as e:
                    patterns['errors'].append(f"Error analyzing move: {str(e)}")
                    continue

            return patterns

        except Exception as e:
            logger.error(f"Error analyzing game patterns: {str(e)}")
            return {
                'tactical': [],
                'positional': [],
                'endgame': [],
                'errors': [str(e)]
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
        """Check if a position contains tactical themes."""
        try:
            # Check for captures
            is_capture = board.is_capture(move)
            
            # Check for checks
            gives_check = board.gives_check(move)
            
            # Check for piece hanging
            is_hanging = self._is_piece_hanging(board, move)
            
            # Check for pins and forks
            has_pin_or_fork = self._has_pin_or_fork(board)
            
            return any([is_capture, gives_check, is_hanging, has_pin_or_fork])
            
        except Exception:
            return False

    def _is_positional_theme(self, board: chess.Board) -> bool:
        """Check if a position contains positional themes."""
        try:
            # Check pawn structure
            has_pawn_theme = self._has_pawn_structure_theme(board)
            
            # Check piece placement
            has_piece_theme = self._has_piece_placement_theme(board)
            
            # Check control of key squares
            has_control_theme = self._has_control_theme(board)
            
            return any([has_pawn_theme, has_piece_theme, has_control_theme])
            
        except Exception:
            return False

    def _is_endgame_position(self, board: chess.Board) -> bool:
        """Check if position is an endgame position."""
        try:
            # Count material
            total_pieces = len(board.piece_map())
            
            # Check for specific endgame characteristics
            queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK))
            rooks = len(board.pieces(chess.ROOK, chess.WHITE)) + len(board.pieces(chess.ROOK, chess.BLACK))
            
            return total_pieces <= 12 or (queens == 0 and rooks <= 2)
            
        except Exception:
            return False

    def _identify_positional_pattern(self, board: chess.Board) -> Optional[str]:
        """Identify specific positional patterns."""
        try:
            # Check isolated pawns
            if self._has_isolated_pawns(board):
                return 'isolated_pawns'
                
            # Check backward pawns
            if self._has_backward_pawns(board):
                return 'backward_pawns'
                
            # Check doubled pawns
            if self._has_doubled_pawns(board):
                return 'doubled_pawns'
                
            # Check outposts
            if self._has_outpost(board):
                return 'outpost'
                
            # Check fianchetto
            if self._has_fianchetto(board):
                return 'fianchetto'
                
            return None
            
        except Exception:
            return None

    def _identify_endgame_pattern(self, board: chess.Board) -> Optional[str]:
        """Identify specific endgame patterns."""
        try:
            # Check king and pawn endgames
            if self._is_king_and_pawn_endgame(board):
                return 'king_and_pawn'
                
            # Check rook endgames
            if self._is_rook_endgame(board):
                return 'rook_endgame'
                
            # Check minor piece endgames
            if self._is_minor_piece_endgame(board):
                return 'minor_piece_endgame'
                
            # Check opposite colored bishops
            if self._is_opposite_colored_bishops(board):
                return 'opposite_colored_bishops'
                
            return None
            
        except Exception:
            return None

    def _get_tactical_description(self, board: chess.Board, move: chess.Move) -> str:
        """Generate description for tactical patterns."""
        try:
            if board.is_capture(move):
                return "Material gain through capture"
            elif board.gives_check(move):
                return "Attack on enemy king"
            elif self._is_piece_hanging(board, move):
                return "Tactical opportunity with hanging piece"
            elif self._has_pin_or_fork(board):
                return "Multiple pieces under attack"
            return "Complex tactical position"
        except Exception:
            return "Tactical opportunity"

    def _get_positional_description(self, pattern: str) -> str:
        """Generate description for positional patterns."""
        descriptions = {
            'isolated_pawns': "Position features isolated pawns, creating potential weaknesses",
            'backward_pawns': "Presence of backward pawns affecting pawn structure",
            'doubled_pawns': "Doubled pawns creating structural considerations",
            'outpost': "Strong outpost position for pieces",
            'fianchetto': "Fianchetto formation providing bishop activity"
        }
        return descriptions.get(pattern, "Positional imbalance")

    def _get_endgame_description(self, pattern: str) -> str:
        """Generate description for endgame patterns."""
        descriptions = {
            'king_and_pawn': "King and pawn endgame requiring precise calculation",
            'rook_endgame': "Rook endgame with technical winning chances",
            'minor_piece_endgame': "Minor piece endgame with strategic possibilities",
            'opposite_colored_bishops': "Opposite colored bishops affecting drawing chances"
        }
        return descriptions.get(pattern, "Technical endgame position")

    def _is_piece_hanging(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if a piece is hanging after a move."""
        try:
            # Make the move on a copy of the board
            board_copy = board.copy()
            board_copy.push(move)
            
            # Check each square
            for square in chess.SQUARES:
                piece = board_copy.piece_at(square)
                if piece is None:
                    continue
                    
                # Count attackers and defenders
                attackers = board_copy.attackers(not piece.color, square)
                defenders = board_copy.attackers(piece.color, square)
                
                if len(attackers) > len(defenders):
                    return True
                    
            return False
            
        except Exception:
            return False

    def _has_pin_or_fork(self, board: chess.Board) -> bool:
        """Check for pins or forks in the position."""
        try:
            # Check each square for potential fork points
            for square in chess.SQUARES:
                attackers = []
                for attacked_square in chess.SQUARES:
                    piece = board.piece_at(attacked_square)
                    if piece and board.is_attacked_by(not piece.color, attacked_square):
                        attackers.append(attacked_square)
                if len(attackers) >= 2:
                    return True
                    
            return False
            
        except Exception:
            return False

    def _has_pawn_structure_theme(self, board: chess.Board) -> bool:
        """Check for pawn structure themes."""
        try:
            # Count pawns on each file
            files = [0] * 8
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece and piece.piece_type == chess.PAWN:
                    files[chess.square_file(square)] += 1
                    
            # Check for structural features
            has_doubled = any(f > 1 for f in files)
            has_isolated = any(f == 1 and (i == 0 or files[i-1] == 0) and (i == 7 or files[i+1] == 0) 
                             for i, f in enumerate(files))
                             
            return has_doubled or has_isolated
            
        except Exception:
            return False

    def _has_piece_placement_theme(self, board: chess.Board) -> bool:
        """Check for piece placement themes."""
        try:
            # Check central squares
            central_squares = [chess.E4, chess.D4, chess.E5, chess.D5]
            center_control = sum(1 for sq in central_squares if board.piece_at(sq) is not None)
            
            # Check piece development
            developed_pieces = sum(1 for sq in chess.SQUARES if board.piece_at(sq) and 
                                 board.piece_at(sq).piece_type in [chess.KNIGHT, chess.BISHOP] and
                                 chess.square_rank(sq) not in [0, 1, 6, 7])
                                 
            return center_control >= 2 or developed_pieces >= 3
            
        except Exception:
            return False

    def _has_control_theme(self, board: chess.Board) -> bool:
        """Check for control of key squares."""
        try:
            # Define key squares
            key_squares = [chess.E4, chess.D4, chess.E5, chess.D5,  # Center
                          chess.C4, chess.F4, chess.C5, chess.F5]  # Extended center
                          
            # Count control of key squares
            white_control = sum(1 for sq in key_squares if board.is_attacked_by(chess.WHITE, sq))
            black_control = sum(1 for sq in key_squares if board.is_attacked_by(chess.BLACK, sq))
            
            return white_control >= 4 or black_control >= 4
            
        except Exception:
            return False

    def _has_isolated_pawns(self, board: chess.Board) -> bool:
        """Check for isolated pawns."""
        try:
            files = [0] * 8
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece and piece.piece_type == chess.PAWN:
                    files[chess.square_file(square)] = 1
                    
            return any(files[i] == 1 and (i == 0 or files[i-1] == 0) and (i == 7 or files[i+1] == 0)
                      for i in range(8))
                      
        except Exception:
            return False

    def _has_backward_pawns(self, board: chess.Board) -> bool:
        """Check for backward pawns."""
        try:
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece and piece.piece_type == chess.PAWN:
                    file = chess.square_file(square)
                    rank = chess.square_rank(square)
                    
                    # Check adjacent files for pawns
                    adjacent_files = []
                    if file > 0:
                        adjacent_files.append(file - 1)
                    if file < 7:
                        adjacent_files.append(file + 1)
                        
                    # Check if pawn is behind adjacent pawns
                    for adj_file in adjacent_files:
                        adj_rank = None
                        for r in range(8):
                            adj_square = chess.square(adj_file, r)
                            adj_piece = board.piece_at(adj_square)
                            if adj_piece and adj_piece.piece_type == chess.PAWN and adj_piece.color == piece.color:
                                adj_rank = r
                                break
                                
                        if adj_rank is not None:
                            if (piece.color == chess.WHITE and rank < adj_rank) or \
                               (piece.color == chess.BLACK and rank > adj_rank):
                                return True
                                
            return False
            
        except Exception:
            return False

    def _has_doubled_pawns(self, board: chess.Board) -> bool:
        """Check for doubled pawns."""
        try:
            files = [0] * 8
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece and piece.piece_type == chess.PAWN:
                    files[chess.square_file(square)] += 1
                    
            return any(f > 1 for f in files)
            
        except Exception:
            return False

    def _has_outpost(self, board: chess.Board) -> bool:
        """Check for outposts."""
        try:
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece and piece.piece_type in [chess.KNIGHT, chess.BISHOP]:
                    file = chess.square_file(square)
                    rank = chess.square_rank(square)
                    
                    # Check if piece is in enemy territory
                    if (piece.color == chess.WHITE and rank >= 4) or \
                       (piece.color == chess.BLACK and rank <= 3):
                        # Check if protected by pawn
                        if self._is_protected_by_pawn(board, square, piece.color):
                            return True
                            
            return False
            
        except Exception:
            return False

    def _has_fianchetto(self, board: chess.Board) -> bool:
        """Check for fianchetto formation."""
        try:
            fianchetto_squares = [
                (chess.G2, chess.F3, chess.G3),  # White kingside
                (chess.B2, chess.C3, chess.B3),  # White queenside
                (chess.G7, chess.F6, chess.G6),  # Black kingside
                (chess.B7, chess.C6, chess.B6)   # Black queenside
            ]
            
            for squares in fianchetto_squares:
                bishop_square, knight_square, pawn_square = squares
                bishop = board.piece_at(bishop_square)
                if bishop and bishop.piece_type == chess.BISHOP:
                    pawn = board.piece_at(pawn_square)
                    if pawn and pawn.piece_type == chess.PAWN and pawn.color == bishop.color:
                        return True
                        
            return False
            
        except Exception:
            return False

    def _is_king_and_pawn_endgame(self, board: chess.Board) -> bool:
        """Check if position is a king and pawn endgame."""
        try:
            pieces = board.piece_map()
            only_kings_and_pawns = all(p.piece_type in [chess.KING, chess.PAWN] for p in pieces.values())
            return only_kings_and_pawns and len(pieces) <= 7
        except Exception:
            return False

    def _is_rook_endgame(self, board: chess.Board) -> bool:
        """Check if position is a rook endgame."""
        try:
            pieces = board.piece_map()
            has_rooks = any(p.piece_type == chess.ROOK for p in pieces.values())
            no_queens = all(p.piece_type != chess.QUEEN for p in pieces.values())
            few_pieces = len(pieces) <= 8
            return has_rooks and no_queens and few_pieces
        except Exception:
            return False

    def _is_minor_piece_endgame(self, board: chess.Board) -> bool:
        """Check if position is a minor piece endgame."""
        try:
            pieces = board.piece_map()
            only_minor = all(p.piece_type in [chess.KING, chess.BISHOP, chess.KNIGHT] for p in pieces.values())
            return only_minor and len(pieces) <= 6
        except Exception:
            return False

    def _is_opposite_colored_bishops(self, board: chess.Board) -> bool:
        """Check if position has opposite colored bishops."""
        try:
            white_bishops = board.pieces(chess.BISHOP, chess.WHITE)
            black_bishops = board.pieces(chess.BISHOP, chess.BLACK)
            
            if len(white_bishops) == 1 and len(black_bishops) == 1:
                white_bishop_square = white_bishops.pop()
                black_bishop_square = black_bishops.pop()
                
                white_bishop_color = (chess.square_rank(white_bishop_square) + 
                                    chess.square_file(white_bishop_square)) % 2
                black_bishop_color = (chess.square_rank(black_bishop_square) + 
                                    chess.square_file(black_bishop_square)) % 2
                                    
                return white_bishop_color != black_bishop_color
                
            return False
            
        except Exception:
            return False

    def _is_protected_by_pawn(self, board: chess.Board, square: chess.Square, color: bool) -> bool:
        """Check if a square is protected by a pawn of the given color."""
        try:
            file = chess.square_file(square)
            rank = chess.square_rank(square)
            
            # Check pawn protection squares
            protection_squares = []
            if color == chess.WHITE:
                if rank > 0:
                    if file > 0:
                        protection_squares.append(chess.square(file - 1, rank - 1))
                    if file < 7:
                        protection_squares.append(chess.square(file + 1, rank - 1))
            else:
                if rank < 7:
                    if file > 0:
                        protection_squares.append(chess.square(file - 1, rank + 1))
                    if file < 7:
                        protection_squares.append(chess.square(file + 1, rank + 1))
                        
            for prot_square in protection_squares:
                piece = board.piece_at(prot_square)
                if piece and piece.piece_type == chess.PAWN and piece.color == color:
                    return True
                    
            return False
            
        except Exception:
            return False

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