"""
Classify critical moments and positions for specific coaching insights.
"""

from __future__ import annotations

from typing import Dict, Optional

import chess

from .batch_move_classification import HANGING_PIECE_MIN_PAWNS


def _material_counts(board: chess.Board) -> tuple[Dict[int, int], Dict[int, int]]:
    white = {pt: 0 for pt in chess.PIECE_TYPES}
    black = {pt: 0 for pt in chess.PIECE_TYPES}
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if not piece:
            continue
        bucket = white if piece.color == chess.WHITE else black
        bucket[piece.piece_type] += 1
    return white, black


def classify_endgame_material(fen: str) -> str:
    """Classify endgame type from FEN material (for study recommendations)."""
    try:
        board = chess.Board(fen)
    except Exception:
        return "unknown_endgame"

    white, black = _material_counts(board)

    def total(side: Dict[int, int]) -> int:
        return sum(side.values())

    w, b = total(white), total(black)
    max_side = max(w, b)
    if max_side > 12:
        return "general_endgame"

    wr, br = white[chess.ROOK], black[chess.ROOK]
    wp, bp = white[chess.PAWN], black[chess.PAWN]
    wq, bq = white[chess.QUEEN], black[chess.QUEEN]
    wb, bb = white[chess.BISHOP], black[chess.BISHOP]
    wn, bn = white[chess.KNIGHT], black[chess.KNIGHT]
    minors = wb + wn + bb + bn

    if wq + bq >= 1 and wr + br == 0 and minors <= 2:
        return "queen_endgame"
    if wr + br >= 1 and wq + bq == 0:
        if wp + bp >= 1:
            return "rook_and_pawn"
        return "rook_endgame"
    if wr + br == 0 and wq + bq == 0:
        if wp + bp >= 2:
            return "king_and_pawn"
        if minors >= 2 and wp + bp >= 1:
            return "minor_piece_endgame"
    if wq + bq == 0 and wr + br <= 2 and wp + bp >= 4:
        return "pawn_structure_endgame"
    if wq + bq == 0 and wr + br <= 1 and minors >= 2:
        return "minor_piece_endgame"
    return "general_endgame"


ENDGAME_LICHESS_URLS = {
    "rook_and_pawn": "https://lichess.org/learn#/1",
    "rook_endgame": "https://lichess.org/learn#/1",
    "king_and_pawn": "https://lichess.org/learn#/6",
    "queen_endgame": "https://lichess.org/learn#/3",
    "minor_piece_endgame": "https://lichess.org/learn",
    "pawn_structure_endgame": "https://lichess.org/learn/6",
    "general_endgame": "https://lichess.org/learn",
    "unknown_endgame": "https://lichess.org/learn",
}


ENDGAME_STUDY_HINTS = {
    "rook_and_pawn": (
        "Study rook-and-pawn endgames: Lucena (building a bridge), Philidor (rook on 3rd rank), "
        "and keeping the rook behind the passed pawn."
    ),
    "king_and_pawn": ("Study king-and-pawn endgames: opposition, key squares, and pawn breakthroughs."),
    "queen_endgame": ("Study queen endgames: centralization, checks, and converting extra material without stalemate."),
    "rook_endgame": (
        "Study rook endgames: active rook placement, cutting the enemy king off, and seventh-rank activity."
    ),
    "minor_piece_endgame": (
        "Study minor-piece endgames: bishop vs knight imbalances, wrong-colored bishop pawn endings, "
        "and keeping pieces coordinated around passed pawns."
    ),
    "pawn_structure_endgame": (
        "Study pawn-structure endgames: creating passed pawns, fixing weaknesses, and king activity "
        "before pushing pawns."
    ),
    "general_endgame": (
        "Review fundamental endgame technique: activate your king, reduce counterplay, and calculate forcing lines first."
    ),
    "unknown_endgame": "Review practical endgame technique for the positions where you lost evaluation.",
}


def _is_square_hanging(board: chess.Board, sq: int, color: chess.Color) -> bool:
    """True when a piece on sq is attacked by the opponent and has no defenders."""
    piece = board.piece_at(sq)
    if not piece or piece.color != color or piece.piece_type == chess.KING:
        return False
    if piece.piece_type < chess.KNIGHT:
        return False
    opponent = not color
    if not board.attackers(opponent, sq):
        return False
    return not board.attackers(color, sq)


def _is_fork_by_square(board: chess.Board, from_sq: int, to_sq: int) -> bool:
    """True if the piece on to_sq attacks two+ valuable enemy pieces."""
    piece = board.piece_at(to_sq)
    if not piece:
        return False
    color = piece.color
    valuable_targets = 0
    for sq in chess.SQUARES:
        target = board.piece_at(sq)
        if not target or target.color == color:
            continue
        if target.piece_type < chess.KNIGHT and target.piece_type != chess.KING:
            continue
        attackers = board.attackers(color, sq)
        if to_sq in attackers:
            valuable_targets += 1
    return valuable_targets >= 2


def classify_tactical_theme(
    fen: str,
    played_move_uci: Optional[str],
    best_move_uci: Optional[str],
    eval_swing: Optional[float] = None,
) -> str:
    """
    Classify why the moment hurt. Hanging-piece labels require meaningful eval loss
    and a piece left undefended by the played move — not unrelated board noise.
    """
    try:
        board_before = chess.Board(fen) if fen else None
    except Exception:
        return "missed_tactic"

    if board_before is None:
        return "missed_tactic"

    swing = float(eval_swing or 0.0)
    allow_hanging_piece = swing >= HANGING_PIECE_MIN_PAWNS

    try:
        if allow_hanging_piece and played_move_uci:
            played = chess.Move.from_uci(played_move_uci)
            if played in board_before.legal_moves:
                after_played = board_before.copy()
                after_played.push(played)
                mover_color = not after_played.turn
                to_sq = played.to_square
                if _is_square_hanging(after_played, to_sq, mover_color):
                    return "hanging_piece"

        if best_move_uci:
            best = chess.Move.from_uci(best_move_uci)
            if best in board_before.legal_moves:
                after_best = board_before.copy()
                after_best.push(best)
                if _is_fork_by_square(after_best, best.from_square, best.to_square):
                    return "fork"
    except Exception:
        return "missed_tactic"

    return "missed_tactic"
