"""Public share links for single-game critical moments (stored in analysis_data JSON)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from django.conf import settings

from core.models import Game, GameAnalysis
from core.stats_helpers import build_single_game_context

SHARE_META_KEY = "moment_share"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _frontend_origin() -> str:
    return (getattr(settings, "FRONTEND_URL", "") or "").rstrip("/")


def build_moment_share_url(share_token: str) -> str:
    origin = _frontend_origin()
    path = f"/share/game-moment/{share_token}"
    return f"{origin}{path}" if origin else path


def get_moment_share_meta(analysis: GameAnalysis) -> Optional[Dict[str, Any]]:
    payload = analysis.analysis_data if isinstance(analysis.analysis_data, dict) else {}
    share_meta = payload.get(SHARE_META_KEY)
    return share_meta if isinstance(share_meta, dict) else None


def get_or_create_moment_share(
    analysis: GameAnalysis,
    move_number: Optional[int] = None,
) -> Dict[str, Any]:
    """Persist share token in analysis_data without a DB migration."""
    payload = dict(analysis.analysis_data) if isinstance(analysis.analysis_data, dict) else {}
    share_meta = payload.get(SHARE_META_KEY)
    if isinstance(share_meta, dict) and share_meta.get("token"):
        if move_number is not None:
            share_meta["move_number"] = move_number
            payload[SHARE_META_KEY] = share_meta
            analysis.analysis_data = payload
            analysis.save(update_fields=["analysis_data", "updated_at"])
        return share_meta

    token = str(uuid.uuid4())
    share_meta = {
        "token": token,
        "move_number": move_number,
        "created_at": _utc_now_iso(),
    }
    payload[SHARE_META_KEY] = share_meta
    analysis.analysis_data = payload
    analysis.save(update_fields=["analysis_data", "updated_at"])
    return share_meta


def find_analysis_by_share_token(share_token: str) -> Optional[GameAnalysis]:
    if not share_token:
        return None
    return (
        GameAnalysis.objects.select_related("game")
        .filter(analysis_data__moment_share__token=str(share_token))
        .first()
    )


def _pick_moment(critical_moments: list, move_number: Optional[int]) -> Optional[Dict[str, Any]]:
    if not isinstance(critical_moments, list) or not critical_moments:
        return None
    if move_number is not None:
        for moment in critical_moments:
            if isinstance(moment, dict) and moment.get("move_number") == move_number:
                return moment
    first = critical_moments[0]
    return first if isinstance(first, dict) else None


def sanitize_public_game_context(game_context: Dict[str, Any]) -> Dict[str, Any]:
    """Strip identifiers; keep coaching-safe metadata only."""
    return {
        "opening_name": game_context.get("opening_name"),
        "eco": game_context.get("eco"),
        "result": game_context.get("result"),
        "player_color": game_context.get("player_color"),
        "platform": game_context.get("platform"),
        "date_played": game_context.get("date_played"),
    }


def build_public_moment_payload(analysis: GameAnalysis, move_number: Optional[int] = None) -> Dict[str, Any]:
    game: Game = analysis.game
    payload = analysis.analysis_data if isinstance(analysis.analysis_data, dict) else {}
    feedback_payload = analysis.feedback if isinstance(analysis.feedback, dict) else {}

    coaching_payload = payload.get("coaching")
    if not isinstance(coaching_payload, dict):
        coaching_payload = (
            feedback_payload.get("coaching")
            if isinstance(feedback_payload.get("coaching"), dict)
            else {}
        )

    critical_moments = payload.get("critical_moments")
    if not isinstance(critical_moments, list):
        critical_moments = coaching_payload.get("critical_moments") or []

    share_meta = get_moment_share_meta(analysis) or {}
    resolved_move = move_number if move_number is not None else share_meta.get("move_number")
    try:
        resolved_move = int(resolved_move) if resolved_move not in (None, "") else None
    except (TypeError, ValueError):
        resolved_move = None

    moment = _pick_moment(critical_moments, resolved_move)
    game_context = sanitize_public_game_context(build_single_game_context(game, profile=None))

    return {
        "share_token": share_meta.get("token"),
        "move_number": resolved_move,
        "game_context": game_context,
        "coaching": {
            "takeaway": coaching_payload.get("takeaway"),
            "do_today": coaching_payload.get("do_today"),
        },
        "moment": moment,
        "engine_meta": {
            "depth": getattr(analysis, "depth", 20) or 20,
            "classification_note": (
                "Single-game uses depth-20 coach model; batch report uses depth-14."
            ),
        },
    }
