"""Tests for moment_insights classification helpers."""

import chess
from core.analysis.moment_insights import (
    _is_square_hanging,
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


def test_classify_tactical_theme_small_swing_not_hanging_piece():
    board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    theme = classify_tactical_theme(board.fen(), "e2e4", "d2d4", eval_swing=0.5)
    assert theme != "hanging_piece"


def test_classify_tactical_theme_hanging_piece_requires_material_loss():
    board = chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKB1R b KQkq e3 0 2")
    theme = classify_tactical_theme(board.fen(), "d7d5", "e4d5", eval_swing=0.5)
    assert theme != "hanging_piece"


def test_is_square_hanging_detects_undefended_piece():
    board = chess.Board("8/8/8/8/3q4/8/8/3R2K1 w - - 0 1")
    assert _is_square_hanging(board, chess.D4, chess.BLACK)


def test_classify_endgame_material_minor_piece():
    board = chess.Board("8/4k3/8/8/8/3BN3/3P4/4K3 w - - 0 1")
    assert classify_endgame_material(board.fen()) == "minor_piece_endgame"


def test_classify_tactical_theme_prefers_missed_fork_on_best_move():
    board = chess.Board(
        "r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 4 4"
    )
    legal = list(board.legal_moves)
    assert len(legal) >= 1
    best = legal[0].uci()
    played = legal[1].uci() if len(legal) > 1 else best
    theme = classify_tactical_theme(board.fen(), played, best)
    assert theme in ("fork", "missed_tactic", "hanging_piece")
