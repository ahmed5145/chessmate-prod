import pytest
from core.analysis.stockfish_game_result import StockfishAnalyzer, build_game_result


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
    assert (res["opening_accuracy"] is None) or isinstance(res["opening_accuracy"], float)
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
