import sys
import types
from types import SimpleNamespace
import json

import pytest

from core.analysis import coaching_generator as cg


def _make_dummy_openai(fixture_response=None, raise_exc=False):
    class DummyCompletions:
        def __init__(self):
            self.create_calls = []

        def create(self, **kwargs):
            self.create_calls.append(kwargs)
            if raise_exc:
                raise RuntimeError("api failure")
            return SimpleNamespace(output_parsed=fixture_response)

    class DummyChat:
        def __init__(self):
            self.completions = DummyCompletions()

    class DummyClient:
        def __init__(self):
            self.chat = DummyChat()

    client_instance = DummyClient()
    dummy = types.SimpleNamespace(OpenAI=lambda: client_instance)
    return dummy


def test_generate_coaching_report_success(monkeypatch):
    # Arrange: sample inputs
    batch_summary = {"games_analyzed": 1}
    per_game_results = [
        {
            "game_id": "g1",
            "player_color": "white",
            "result": "1-0",
            "opening_name": "Test Opening",
            "phase_breakdown": {"opening": {"avg_eval_drop": 0.1}, "middlegame": {"avg_eval_drop": 0.2}, "endgame": {"avg_eval_drop": 0.3}},
            "move_quality": {"blunder": 1, "mistake": 2},
            "critical_moments": [{"tactical_theme": "fork"}],
        }
    ]

    # Fixture matching schema
    fixture = {
        "executive_summary": "Summary",
        "coaching_narrative": {"opening": "O", "middlegame": "M", "endgame": "E"},
        "top_3_priorities": [
            {"rank": 1, "title": "T1", "why_it_matters": "W", "how_to_fix": "H", "specific_drill": "D", "estimated_study_hours": 1},
            {"rank": 2, "title": "T2", "why_it_matters": "W2", "how_to_fix": "H2", "specific_drill": "D2", "estimated_study_hours": 1},
            {"rank": 3, "title": "T3", "why_it_matters": "W3", "how_to_fix": "H3", "specific_drill": "D3", "estimated_study_hours": 1},
        ],
        "training_plan": {"week_1": "w1", "week_2": "w2", "week_3": "w3", "week_4": "w4"},
        "one_thing_to_do_today": "Do one tactic",
    }

    dummy = _make_dummy_openai(fixture_response=fixture)
    monkeypatch.setitem(sys.modules, "openai", dummy)

    # Act
    result = cg.generate_coaching_report(batch_summary, per_game_results)

    # Assert returned dict matches fixture
    assert result == fixture

    # Ensure single API call and correct args (model + strict in json_schema)
    client = dummy.OpenAI()
    assert len(client.chat.completions.create_calls) == 1
    called_kwargs = client.chat.completions.create_calls[0]
    assert called_kwargs.get("model") == "gpt-4o-mini"
    rf = called_kwargs.get("response_format")
    assert rf is not None and rf.get("type") == "json_schema"
    json_schema = rf.get("json_schema")
    assert json_schema is not None
    assert json_schema.get("strict") is True
    assert json_schema.get("name") == "batch_coaching_report"


def test_generate_coaching_report_raises_on_api_error(monkeypatch):
    batch_summary = {"games_analyzed": 0}
    per_game_results = []

    dummy = _make_dummy_openai(raise_exc=True)
    monkeypatch.setitem(sys.modules, "openai", dummy)

    with pytest.raises(cg.CoachingGeneratorError) as excinfo:
        cg.generate_coaching_report(batch_summary, per_game_results)

    assert "Coaching generation failed" in str(excinfo.value)
