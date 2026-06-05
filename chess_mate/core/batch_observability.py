"""
Structured batch analysis events for logs / monitoring (grep-friendly JSON).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("chessmate.batch")


def log_batch_event(event: str, batch_id: Any, **fields: Any) -> None:
    """Emit one JSON line for batch lifecycle events."""
    payload: Dict[str, Any] = {
        "event": event,
        "batch_id": str(batch_id),
    }
    for key, value in fields.items():
        if value is not None:
            payload[key] = value
    logger.info("batch_event %s", json.dumps(payload, default=str, sort_keys=True))


def log_batch_started(batch_id: Any, user_id: int, games_count: int) -> None:
    log_batch_event(
        "batch_started",
        batch_id,
        user_id=user_id,
        games_count=games_count,
    )


def log_batch_completed(
    batch_id: Any,
    *,
    final_status: str,
    games_analyzed: int,
    games_failed: int,
    duration_seconds: Optional[float] = None,
    coaching_ok: Optional[bool] = None,
    coaching_error: Optional[str] = None,
    aggregation_failed: bool = False,
) -> None:
    log_batch_event(
        "batch_completed",
        batch_id,
        status=final_status,
        games_analyzed=games_analyzed,
        games_failed=games_failed,
        duration_seconds=round(duration_seconds, 2) if duration_seconds is not None else None,
        coaching_ok=coaching_ok,
        coaching_error=coaching_error,
        aggregation_failed=aggregation_failed,
    )
