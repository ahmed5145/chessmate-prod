"""Tests for batch move classification thresholds (contract M2)."""

from core.analysis.batch_move_classification import (
    classify_deterioration,
    player_eval_deterioration,
)


def test_white_deterioration_when_eval_drops():
    assert player_eval_deterioration(True, 2.0, 0.5) == 1.5


def test_black_deterioration_when_white_eval_rises():
    assert player_eval_deterioration(False, -1.0, 2.0) == 3.0


def test_classify_deterioration_thresholds():
    assert classify_deterioration(0.0) == "good"
    assert classify_deterioration(0.25) == "inaccuracy"
    assert classify_deterioration(0.6) == "mistake"
    assert classify_deterioration(2.0) == "blunder"
