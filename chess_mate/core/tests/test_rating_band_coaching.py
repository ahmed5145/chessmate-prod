from core.rating_band_coaching import (
    attach_moment_benchmarks,
    rating_band_coaching,
    resolve_rating_band,
    single_game_moment_benchmark,
)


def test_rating_band_intermediate():
    result = rating_band_coaching(1550)
    assert result["band"] == "intermediate"
    assert "1400" in result["label"]
    assert result["daily_drill"]


def test_rating_band_none():
    assert rating_band_coaching(None) is None


def test_rating_band_tailors_to_opening_weakness():
    result = rating_band_coaching(
        1950,
        worst_phase="opening",
        repertoire_gaps=[{"opening_name": "Sicilian Defense"}],
    )
    assert "opening" in result["focus"].lower()
    assert (
        "endgame" not in result["daily_drill"].lower()
        or "opening" in result["daily_drill"].lower()
    )


def test_rating_band_tailors_to_endgame_when_data_exists():
    result = rating_band_coaching(
        1950,
        worst_phase="endgame",
        endgame_insights=[
            {
                "endgame_type": "rook_and_pawn",
                "label": "Rook and pawn",
                "study_focus": "Study Lucena.",
            }
        ],
    )
    assert "rook" in result["focus"].lower() or "endgame" in result["focus"].lower()


def test_resolve_rating_band_for_developing_player():
    band = resolve_rating_band(1250)
    assert band["label"] == "1200-1399"
    assert band["near_rating"] == 1300


def test_single_game_moment_benchmark_uses_range_not_point_estimate():
    benchmark = single_game_moment_benchmark(1250, "blunder")
    assert benchmark is not None
    assert "ChessMate benchmark" in benchmark["copy"]
    assert "35-45%" in benchmark["copy"]
    assert benchmark["miss_rate_low"] < benchmark["miss_rate_high"]


def test_single_game_moment_benchmark_hidden_without_rating():
    assert single_game_moment_benchmark(None, "mistake") is None


def test_attach_moment_benchmarks_enriches_moments():
    moments = attach_moment_benchmarks(
        [{"move_number": 12, "type": "mistake"}],
        1250,
    )
    assert moments[0]["rating_benchmark"]["copy"]
