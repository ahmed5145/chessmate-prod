import json
import logging

from core.batch_observability import log_batch_completed, log_batch_event, log_batch_started


def test_log_batch_event_emits_json(caplog):
    caplog.set_level(logging.INFO, logger="chessmate.batch")
    log_batch_event("test_event", "batch-42", user_id=7, games_count=10)
    assert any("batch_event" in record.message for record in caplog.records)
    payload_line = next(r.message for r in caplog.records if "batch_event" in r.message)
    json_str = payload_line.split("batch_event ", 1)[1]
    payload = json.loads(json_str)
    assert payload["event"] == "test_event"
    assert payload["batch_id"] == "batch-42"
    assert payload["user_id"] == 7
    assert payload["games_count"] == 10


def test_log_batch_started_wrapper(caplog):
    caplog.set_level(logging.INFO, logger="chessmate.batch")
    log_batch_started("abc", 1, 5)
    payload_line = next(r.message for r in caplog.records if "batch_event" in r.message)
    payload = json.loads(payload_line.split("batch_event ", 1)[1])
    assert payload["event"] == "batch_started"
    assert payload["games_count"] == 5


def test_log_batch_completed_includes_coaching_flags(caplog):
    caplog.set_level(logging.INFO, logger="chessmate.batch")
    log_batch_completed(
        "xyz",
        final_status="partial",
        games_analyzed=5,
        games_failed=0,
        duration_seconds=120.5,
        coaching_ok=False,
        coaching_error="rate limit",
    )
    payload_line = next(r.message for r in caplog.records if "batch_event" in r.message)
    payload = json.loads(payload_line.split("batch_event ", 1)[1])
    assert payload["event"] == "batch_completed"
    assert payload["status"] == "partial"
    assert payload["coaching_ok"] is False
    assert payload["coaching_error"] == "rate limit"
    assert payload["duration_seconds"] == 120.5
