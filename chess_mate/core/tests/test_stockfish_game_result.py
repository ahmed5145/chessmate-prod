import pytest
from core.analysis.stockfish_game_result import (
    StockfishAnalyzer,
    build_game_result,
    infer_player_color_from_headers,
)


class _FakeAnalyzer:
    """Deterministic analyzer used to keep tests engine-free and fast in CI."""

    def __init__(self):
        self._calls = 0

    def analyze_position(self, _board, depth=20):
        # Monotonic decreasing score creates at least one critical moment.
        score = float(-self._calls)
        self._calls += 1
        return {
            "score": score,
            "depth": depth,
            "pv": ["e2e4", "e7e5", "g1f3"],
            "time": 0.01,
            "nodes": 1000,
        }


@pytest.fixture(autouse=True)
def _mock_stockfish_analyzer(monkeypatch):
    """Prevent spawning real Stockfish in schema tests."""
    fake = _FakeAnalyzer()
    monkeypatch.setattr(
        StockfishAnalyzer,
        "get_instance",
        staticmethod(lambda: fake),
    )


# Two small PGN examples embedded for tests
CLEAN_GAME_PGN = """
[Event "Test"]
[Site "?"]
[Date "2020.01.01"]
[Round "1"]
[White "Tester"]
[Black "Opponent"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 1-0
"""

BLUNDER_GAME_PGN = """
[Event "BlunderTest"]
[Site "?"]
[Date "2020.01.02"]
[Round "1"]
[White "Blunderer"]
[Black "Opponent"]
[Result "0-1"]

1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 0-1
"""


def test_clean_game_schema_structure():
    res = build_game_result(CLEAN_GAME_PGN, game_id="clean-1")

    # Basic top-level keys
    assert isinstance(res, dict)
    expected_keys = {
        "game_id",
        "total_moves",
        "result",
        "player_color",
        "opening_name",
        "opening_accuracy",
        "phase_breakdown",
        "move_quality",
        "critical_moments",
        "tactical_patterns_missed",
    }
    assert expected_keys.issubset(set(res.keys()))

    # Types
    assert isinstance(res["total_moves"], int)
    assert isinstance(res["opening_name"], str)
    assert (res["opening_accuracy"] is None) or isinstance(
        res["opening_accuracy"], float
    )
    assert isinstance(res["phase_breakdown"], dict)
    assert isinstance(res["move_quality"], dict)
    assert isinstance(res["critical_moments"], list)
    assert isinstance(res["tactical_patterns_missed"], list)

    # Each critical moment has required fields
    for cm in res["critical_moments"]:
        for k in [
            "move_number",
            "phase",
            "type",
            "eval_before",
            "eval_after",
            "eval_swing",
            "fen",
            "played_move",
            "best_move",
            "tactical_theme",
            "explanation",
        ]:
            assert k in cm


def test_moves_store_pre_and_post_evals():
    """M1: each half-move has eval_before and eval_after from separate engine calls."""
    res = build_game_result(CLEAN_GAME_PGN, game_id="eval-check")
    assert res["total_moves"] > 0
    # Re-run loop indirectly: analyzed moves are not returned on result, but critical moments carry evals
    for cm in res["critical_moments"]:
        assert "eval_before" in cm
        assert "eval_after" in cm
        assert cm["eval_swing"] >= 0


def test_infer_player_color_matches_platform_username():
    assert (
        infer_player_color_from_headers("Alice", "Bob", chess_com_username="alice")
        == "white"
    )
    assert (
        infer_player_color_from_headers("Alice", "Bob", lichess_username="bob")
        == "black"
    )
    assert infer_player_color_from_headers("Alice", "Bob") == "white"


def test_build_game_result_saved_game_id_and_player_color():
    pgn = """
[Event "Color"]
[White "MyChessUser"]
[Black "Opponent"]
[Result "0-1"]

1. e4 e5 2. Nf3 Nc6 1-0
"""
    res = build_game_result(
        pgn,
        game_id="game_0",
        saved_game_id=42,
        chess_com_username="MyChessUser",
    )
    assert res["player_color"] == "white"
    assert res["saved_game_id"] == 42


def test_move_quality_and_phases_count_player_moves_only():
    res = build_game_result(
        CLEAN_GAME_PGN,
        game_id="player-only-mq",
        chess_com_username="Tester",
    )
    player_moves = res["player_moves"]
    classified_moves = sum(res["move_quality"].values())
    phase_moves = sum(
        phase.get("moves", 0) for phase in res["phase_breakdown"].values()
    )

    assert player_moves > 0
    assert classified_moves == player_moves
    assert phase_moves == player_moves
    for moment in res["critical_moments"]:
        assert moment.get("mover") == res["player_color"]


def test_blunder_game_detects_critical_moment():
    res = build_game_result(BLUNDER_GAME_PGN, game_id="blunder-1")

    # There should be at least one critical moment
    assert isinstance(res["critical_moments"], list)
    assert len(res["critical_moments"]) >= 1

    # Tactical patterns should include some theme strings
    assert isinstance(res["tactical_patterns_missed"], list)

    # Ensure game_id propagated
    assert res["game_id"] == "blunder-1"


if __name__ == "__main__":
    pytest.main([__file__])
