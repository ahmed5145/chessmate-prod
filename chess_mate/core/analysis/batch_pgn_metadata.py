"""
Extract platform URLs and opponent/date metadata from batch PGN headers.
"""

from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Any, Dict, Optional

import chess.pgn

_LICHESS_GAME_RE = re.compile(r"lichess\.org/([a-zA-Z0-9]{8,12})", re.IGNORECASE)
_CHESSCOM_GAME_RE = re.compile(r"chess\.com/(?:game/)?([a-zA-Z0-9/_-]+)", re.IGNORECASE)
_LICHESS_RESERVED = frozenset(
    {"study", "training", "practice", "api", "learn", "forum", "broadcast"}
)


def _normalize_platform_url(url: str) -> Optional[str]:
    cleaned = (url or "").strip().strip('"')
    if not cleaned.startswith("http"):
        return None
    if "lichess.org" not in cleaned and "chess.com" not in cleaned:
        return None
    return cleaned.split("?")[0].rstrip("/")


def _platform_from_url(url: str) -> Optional[str]:
    lower = url.lower()
    if "lichess.org" in lower:
        return "lichess"
    if "chess.com" in lower:
        return "chess.com"
    return None


def _lichess_url_from_site(site: str) -> Optional[str]:
    match = _LICHESS_GAME_RE.search(site)
    if not match:
        return None
    game_id = match.group(1)
    if game_id.lower() in _LICHESS_RESERVED:
        return None
    return f"https://lichess.org/{game_id}"


def _parse_date_header(raw: str) -> Optional[str]:
    value = (raw or "").strip()
    if not value or value.startswith("?"):
        return None
    for fmt in ("%Y.%m.%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def extract_platform_metadata_from_pgn(pgn: str) -> Dict[str, Any]:
    """
    Best-effort metadata from PGN tags (Chess.com / Lichess exports).
    """
    metadata: Dict[str, Any] = {}
    if not pgn or not str(pgn).strip():
        return metadata

    try:
        game = chess.pgn.read_game(io.StringIO(pgn))
    except Exception:
        return metadata

    if not game:
        return metadata

    headers = game.headers
    platform_url = None

    for key in ("Link", "RoundUrl", "Site"):
        header_value = headers.get(key, "")
        if not header_value:
            continue

        if key == "Site" and header_value.lower() in ("chess.com", "lichess.org", "?"):
            continue

        candidate = _normalize_platform_url(header_value)
        if candidate:
            platform_url = candidate
            break

        if key == "Site":
            lichess_url = _lichess_url_from_site(header_value)
            if lichess_url:
                platform_url = lichess_url
                break

    if not platform_url:
        for header_value in headers.values():
            if not header_value:
                continue
            match = _CHESSCOM_GAME_RE.search(header_value)
            if match:
                platform_url = _normalize_platform_url(match.group(0))
                if platform_url and not platform_url.startswith("http"):
                    platform_url = f"https://www.{platform_url}"
                break

    if platform_url:
        metadata["platform_game_url"] = platform_url
        platform = _platform_from_url(platform_url)
        if platform:
            metadata["platform"] = platform

    date_played = _parse_date_header(headers.get("Date", ""))
    if date_played:
        metadata["date_played"] = date_played

    white = headers.get("White", "")
    black = headers.get("Black", "")
    if white and black:
        metadata["white"] = white
        metadata["black"] = black

    return metadata
