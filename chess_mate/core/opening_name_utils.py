"""
Normalize verbose PGN/Chess.com opening headers for display and external study search.
"""

from __future__ import annotations

import re

_MOVE_SEGMENT_RE = re.compile(r"^\d+\.")
_MOVE_TAIL_RE = re.compile(r"\s+\d+\.\s*.*$")
_INLINE_MOVE_TAIL_RE = re.compile(r"\d+\.[NBRQKO].*$", re.IGNORECASE)


def compact_opening_name(name: str | None) -> str:
    """
    Strip move-tree suffixes from opening names.

    Example:
        Sicilian Defense Open Dragon Classical Attack...8.O O O O 9.f4 Qb6
        -> Sicilian Defense Open Dragon Classical Attack
    """
    if not name:
        return ""

    text = str(name).strip()
    if not text:
        return ""

    if "..." in text:
        text = text.split("...", 1)[0].strip()

    segments = [part.strip() for part in text.split(",")]
    kept: list[str] = []
    for segment in segments:
        if _MOVE_SEGMENT_RE.match(segment) or _INLINE_MOVE_TAIL_RE.search(segment):
            break
        kept.append(segment)
    text = ", ".join(kept) if kept else text

    text = _MOVE_TAIL_RE.sub("", text).strip()
    text = _INLINE_MOVE_TAIL_RE.sub("", text).strip()
    text = re.sub(r"\s+", " ", text)
    return text
