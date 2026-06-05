"""Tests for batch ACPL helpers."""

from core.analysis.batch_metrics import (
    compute_batch_acpl,
    compute_game_accuracy,
    compute_game_acpl,
    move_accuracy_percent,
    move_centipawn_loss,
)


def test_move_centipawn_loss_from_eval_swing():
    # White loses 0.5 pawns of eval after their move
    assert move_centipawn_loss({"eval_before": 0.0, "eval_after": -0.5, "is_white": True}) == 50.0


def test_compute_game_acpl_averages_moves():
    moves = [
        {"eval_before": 0.0, "eval_after": -0.1, "is_white": True},
        {"eval_before": -0.1, "eval_after": -0.4, "is_white": True},
    ]
    assert compute_game_acpl(moves) == 20.0


def test_move_accuracy_percent_best_move_is_near_100():
    assert move_accuracy_percent(0) >= 99.0


def test_move_accuracy_percent_large_blunder_is_low():
    assert move_accuracy_percent(300) < 20.0


def test_compute_game_accuracy_player_moves_only():
    moves = [
        {"eval_before": 0.0, "eval_after": 0.0, "is_white": True},
        {"eval_before": 0.0, "eval_after": -1.0, "is_white": True},
        {"eval_before": 0.0, "eval_after": 0.5, "is_white": False},
    ]
    acc = compute_game_accuracy(moves, "white")
    assert 40.0 < acc < 100.0


def test_compute_batch_acpl_weighted_by_moves():
    per_game = [
        {"acpl": 20.0, "total_moves": 40},
        {"acpl": 40.0, "total_moves": 20},
    ]
    # (20*40 + 40*20) / 60 = 26.7
    assert compute_batch_acpl(per_game) == 26.7
