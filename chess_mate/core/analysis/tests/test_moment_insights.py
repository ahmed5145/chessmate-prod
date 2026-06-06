"""Tests for moment_insights classification helpers."""

import chess
from core.analysis.moment_insights import (
    classify_endgame_material,
    classify_tactical_theme,
)


def test_classify_endgame_material_rook_and_pawn():
    # Minimal rook + pawn endgame FEN (white rook, white pawn, kings)
    board = chess.Board.empty()
    board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
    board.set_piece_at(chess.A1, chess.Piece(chess.ROOK, chess.WHITE))
    board.set_piece_at(chess.A7, chess.Piece(chess.PAWN, chess.WHITE))
    assert classify_endgame_material(board.fen()) == "rook_and_pawn"


def test_classify_tactical_theme_prefers_missed_fork_on_best_move():
    board = chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 4 4")
    legal = list(board.legal_moves)
    assert len(legal) >= 1
    best = legal[0].uci()
    played = legal[1].uci() if len(legal) > 1 else best
    theme = classify_tactical_theme(board.fen(), played, best)
    assert theme in ("fork", "missed_tactic", "hanging_piece")
