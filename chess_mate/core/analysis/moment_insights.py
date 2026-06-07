"""
Classify critical moments and positions for specific coaching insights.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import chess


def classify_endgame_material(fen: str) -> str:
    """Classify endgame type from FEN material (for study recommendations)."""
    try:
        board = chess.Board(fen)
    except Exception:
        return "unknown_endgame"

    white = {pt: 0 for pt in chess.PIECE_TYPES}
    black = {pt: 0 for pt in chess.PIECE_TYPES}
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if not piece:
            continue
        bucket = white if piece.color == chess.WHITE else black
        bucket[piece.piece_type] += 1

    def total(side: Dict[int, int]) -> int:
        return sum(side.values())

    w, b = total(white), total(black)
    if w <= 6 and b <= 6:
        wr, br = white[chess.ROOK], black[chess.ROOK]
        wp, bp = white[chess.PAWN], black[chess.PAWN]
        wq, bq = white[chess.QUEEN], black[chess.QUEEN]
        if wr + br >= 1 and wq + bq == 0 and wp + bp >= 1:
            return "rook_and_pawn"
        if wr + br == 0 and wq + bq == 0 and wp + bp >= 2:
            return "king_and_pawn"
        if wq + bq >= 1 and wr + br == 0:
            return "queen_endgame"
        if wr + br >= 2:
            return "rook_endgame"
    return "general_endgame"


ENDGAME_LICHESS_URLS = {
    "rook_and_pawn": "https://lichess.org/practice/endgames/rook",
    "rook_endgame": "https://lichess.org/practice/endgames/rook",
    "king_and_pawn": "https://lichess.org/practice/endgames/pawn",
    "queen_endgame": "https://lichess.org/practice/endgames/queen",
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
    "general_endgame": (
        "Review fundamental endgame technique: activate your king, reduce counterplay, and calculate forcing lines first."
    ),
    "unknown_endgame": "Review practical endgame technique for the positions where you lost evaluation.",
}


def _left_piece_en_prise(board: chess.Board, victim_color: chess.Color) -> bool:
    """True if victim has a valuable piece attacked and undefended after the played move."""
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if not piece or piece.color != victim_color:
            continue
        if piece.piece_type < chess.KNIGHT and piece.piece_type != chess.KING:
            continue
        attackers = board.attackers(not victim_color, sq)
        if not attackers:
            continue
        defenders = board.attackers(victim_color, sq)
        if not defenders:
            return True
    return False


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
) -> str:
    """
    Classify why the moment hurt: prefer themes from the missed best move, not noisy post-blunder board.
    """
    try:
        board_before = chess.Board(fen) if fen else None
    except Exception:
        return "missed_tactic"

    if board_before is None:
        return "missed_tactic"

    try:
        if played_move_uci:
            played = chess.Move.from_uci(played_move_uci)
            if played in board_before.legal_moves:
                after_played = board_before.copy()
                after_played.push(played)
                to_sq = played.to_square
                if not after_played.is_attacked_by(after_played.turn, to_sq) and after_played.is_attacked_by(
                    not after_played.turn, to_sq
                ):
                    return "hanging_piece"
                if _left_piece_en_prise(after_played, not after_played.turn):
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
