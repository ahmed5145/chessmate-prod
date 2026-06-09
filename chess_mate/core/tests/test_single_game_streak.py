"""Tests for single-game blunder-free streak tracking."""

import pytest
from core.single_game_streak import (
    game_breaks_streak,
    get_single_game_streak,
    move_breaks_streak,
    update_single_game_streak,
)
from core.tests.profile_helpers import ensure_profile


@pytest.mark.django_db
class TestSingleGameStreak:
    def test_move_breaks_streak_on_blunder_swing(self):
        move = {
            "is_white": True,
            "eval_change": -1.8,
            "classification": "blunder",
        }
        assert move_breaks_streak(move, "white") is True

    def test_mistake_under_one_pawn_does_not_break(self):
        move = {
            "is_white": True,
            "eval_change": -0.6,
            "classification": "mistake",
        }
        assert move_breaks_streak(move, "white") is False

    def test_opponent_move_ignored(self):
        move = {
            "is_white": False,
            "eval_change": -3.0,
            "classification": "blunder",
        }
        assert move_breaks_streak(move, "white") is False

    def test_update_increments_on_clean_game(self, test_user):
        profile = ensure_profile(test_user)
        profile.preferences = {"single_game_streak": {"count": 2, "last_game_id": 10}}
        profile.save(update_fields=["preferences"])

        analysis_data = {
            "moves": [
                {"is_white": True, "eval_change": 0.1, "classification": "good"},
                {"is_white": False, "eval_change": -2.0, "classification": "blunder"},
            ]
        }
        state = update_single_game_streak(
            profile,
            game_id=11,
            analysis_data=analysis_data,
            player_color="white",
        )
        assert state["count"] == 3
        assert state["last_game_id"] == 11

    def test_update_resets_on_breaking_game(self, test_user):
        profile = ensure_profile(test_user)
        profile.preferences = {"single_game_streak": {"count": 4, "last_game_id": 20}}
        profile.save(update_fields=["preferences"])

        analysis_data = {
            "moves": [
                {"is_white": True, "eval_change": -1.2, "classification": "blunder"},
            ]
        }
        state = update_single_game_streak(
            profile,
            game_id=21,
            analysis_data=analysis_data,
            player_color="white",
        )
        assert state["count"] == 0

    def test_reanalyze_same_game_does_not_double_increment(self, test_user):
        profile = ensure_profile(test_user)
        profile.preferences = {"single_game_streak": {"count": 2, "last_game_id": 30}}
        profile.save(update_fields=["preferences"])

        analysis_data = {"moves": [{"is_white": True, "eval_change": 0.05, "classification": "good"}]}
        state = update_single_game_streak(
            profile,
            game_id=30,
            analysis_data=analysis_data,
            player_color="white",
        )
        assert state["count"] == 2

    def test_get_single_game_streak_defaults(self):
        assert get_single_game_streak(None) == {"count": 0, "last_game_id": None, "updated_at": None}
