import json
import sys
import types

import pytest
from core.analysis import coaching_generator


def make_fake_openai_module(response_dict):
    """Create a fake `openai` module that provides OpenAI().chat.completions.create(...)"""
    fake_module = types.SimpleNamespace()

    class FakeCompletions:
        def create(self, *args, **kwargs):
            # Return an object that coaching_generator will accept.
            fake_resp = types.SimpleNamespace()
            # Prefer output_parsed shortcut so generator returns quickly
            fake_resp.output_parsed = response_dict
            return fake_resp

    class FakeChat:
        def __init__(self):
            self.completions = FakeCompletions()

    class OpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = FakeChat()

    fake_module.OpenAI = OpenAI
    return fake_module


def build_minimal_valid_report():
    return {
        "executive_summary": "Top issue: tactical oversight across middlegame.",
        "coaching_narrative": {
            "opening": "Solid opening play.",
            "middlegame": "Tend to miss tactics; focus on vision.",
            "endgame": "Endgame technique needs work.",
        },
        "top_3_priorities": [
            {
                "rank": 1,
                "title": "Tactics: pattern recognition",
                "why_it_matters": "Tactical misses change evaluations drastically.",
                "how_to_fix": "Train common tactical motifs with puzzles.",
                "specific_drill": "50 tactics/day focusing on forks and pins.",
                "estimated_study_hours": 6,
            },
            {
                "rank": 2,
                "title": "Time management",
                "why_it_matters": "Time trouble leads to blunders.",
                "how_to_fix": "Practice with a clock and targets.",
                "specific_drill": "10 rapid games focusing on decision time.",
                "estimated_study_hours": 4,
            },
            {
                "rank": 3,
                "title": "Endgame basics",
                "why_it_matters": "Convert advantages more reliably.",
                "how_to_fix": "Study king and pawn, rook endgames.",
                "specific_drill": "Set up common endgames and play them out.",
                "estimated_study_hours": 5,
            },
        ],
        "training_plan": {
            "week_1": "Tactics drills + 2 rapid games",
            "week_2": "Tactics + time control exercises",
            "week_3": "Endgame basics + tactics",
            "week_4": "Integrated practice and review",
        },
        "one_thing_to_do_today": "Solve 20 tactical puzzles focusing on forks",
    }


def test_generate_coaching_report_matches_schema(monkeypatch):
    # Build fake response that matches the coaching schema
    fake_report = build_minimal_valid_report()

    fake_openai = make_fake_openai_module(fake_report)
    # Inject fake module into sys.modules so coaching_generator imports it
    sys.modules["openai"] = fake_openai

    # Prepare deterministic input batch summary and per-game results
    batch_summary = {"overall_accuracy": 0.72}
    per_game_results = [
        {
            "game_id": "g1",
            "player_color": "white",
            "result": "1-0",
            "phase_breakdown": {
                "opening": {"avg_eval_drop": 0.1},
                "middlegame": {"avg_eval_drop": 0.3},
                "endgame": {"avg_eval_drop": 0.2},
            },
            "move_quality": {"blunder": 0, "mistake": 2, "inaccuracy": 1},
            "critical_moments": [],
        }
    ]

    # Call generator — it will use our fake OpenAI client and return fake_report
    result = coaching_generator.generate_coaching_report(batch_summary, per_game_results, player_rating=1200)

    # Basic structural assertions to validate schema conformance
    assert isinstance(result, dict)
    assert "executive_summary" in result and isinstance(result["executive_summary"], str)

    cn = result.get("coaching_narrative")
    assert isinstance(cn, dict)
    for phase in ("opening", "middlegame", "endgame"):
        assert phase in cn and isinstance(cn[phase], str)

    priorities = result.get("top_3_priorities")
    assert isinstance(priorities, list) and len(priorities) == 3
    for idx, p in enumerate(priorities, start=1):
        assert p.get("rank") == idx
        assert isinstance(p.get("title"), str)
        assert isinstance(p.get("why_it_matters"), str)
        assert isinstance(p.get("how_to_fix"), str)
        assert isinstance(p.get("specific_drill"), str)
        assert isinstance(p.get("estimated_study_hours"), (int, float))

    tp = result.get("training_plan")
    assert isinstance(tp, dict)
    for k in ("week_1", "week_2", "week_3", "week_4"):
        assert k in tp and isinstance(tp[k], str)

    assert "one_thing_to_do_today" in result and isinstance(result["one_thing_to_do_today"], str)

    # Cleanup fake module
    del sys.modules["openai"]
