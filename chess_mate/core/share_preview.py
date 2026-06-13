"""Server-rendered HTML for public share links (OG crawlers cannot run React)."""

from __future__ import annotations

import html
import os
import re
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse

from .single_game_moment_share import (
    build_public_moment_payload,
    find_analysis_by_share_token,
)

DEFAULT_SITE_NAME = "ChessMate"
DEFAULT_OG_IMAGE_PATH = "/chessmate-og.png"
OG_TITLE_MAX = 60
OG_DESCRIPTION_MAX = 125


def _truncate(text: str, limit: int) -> str:
    normalized = str(text or "").strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1].rstrip()}…"


def build_share_moment_meta(payload: Optional[Dict[str, Any]]) -> Tuple[str, str]:
    """Return (page_title, description) for OG tags."""
    if not payload:
        return (
            "Shared chess moment · ChessMate",
            "See a turning point from a ChessMate depth-20 review — get your own batch coach report.",
        )

    moment = payload.get("moment") if isinstance(payload.get("moment"), dict) else {}
    context = (
        payload.get("game_context")
        if isinstance(payload.get("game_context"), dict)
        else {}
    )
    coaching = (
        payload.get("coaching") if isinstance(payload.get("coaching"), dict) else {}
    )

    takeaway = str(
        coaching.get("takeaway") or "Critical moment from a ChessMate deep review"
    ).strip()
    parts = [
        f"Move {moment.get('move_number')}" if moment.get("move_number") else None,
        (
            f"Eval swing {moment.get('eval_swing')}"
            if moment.get("eval_swing") is not None
            else None
        ),
        str(context.get("opening_name") or "").strip() or None,
        str(context.get("result") or "").strip() or None,
        f"Practice: {coaching.get('do_today')}" if coaching.get("do_today") else None,
    ]
    description = " · ".join(part for part in parts if part)
    if not description:
        description = "See a turning point from a ChessMate depth-20 review — get your own batch coach report."

    suffix = f" · {DEFAULT_SITE_NAME}"
    page_title = f"{_truncate(takeaway, OG_TITLE_MAX - len(suffix))}{suffix}"
    return page_title, _truncate(description, OG_DESCRIPTION_MAX)


def _frontend_build_index_path() -> str:
    return os.path.join(settings.BASE_DIR, "frontend", "build", "index.html")


def _absolute_url(request: HttpRequest, path: str) -> str:
    normalized = path if path.startswith("/") else f"/{path}"
    return request.build_absolute_uri(normalized)


def _inject_meta_block(html_doc: str, meta_block: str) -> str:
    if "</head>" not in html_doc:
        return html_doc
    return html_doc.replace("</head>", f"{meta_block}\n  </head>", 1)


def render_share_moment_html(
    request: HttpRequest,
    share_token: str,
) -> str:
    analysis = find_analysis_by_share_token(str(share_token))
    payload = build_public_moment_payload(analysis) if analysis else None
    if payload is None or not payload.get("moment"):
        raise Http404("Shared moment not found.")

    page_title, description = build_share_moment_meta(payload)
    canonical_path = f"/share/game-moment/{share_token}"
    canonical_url = _absolute_url(request, canonical_path)
    og_image_url = _absolute_url(request, DEFAULT_OG_IMAGE_PATH)

    meta_block = "\n".join(
        [
            f"    <title>{html.escape(page_title)}</title>",
            f'    <meta name="description" content="{html.escape(description)}" />',
            f'    <meta property="og:site_name" content="{DEFAULT_SITE_NAME}" />',
            f'    <meta property="og:title" content="{html.escape(page_title)}" />',
            f'    <meta property="og:description" content="{html.escape(description)}" />',
            f'    <meta property="og:type" content="article" />',
            f'    <meta property="og:url" content="{html.escape(canonical_url)}" />',
            f'    <meta property="og:image" content="{html.escape(og_image_url)}" />',
            '    <meta name="twitter:card" content="summary_large_image" />',
            f'    <meta name="twitter:title" content="{html.escape(page_title)}" />',
            f'    <meta name="twitter:description" content="{html.escape(description)}" />',
            f'    <meta name="twitter:image" content="{html.escape(og_image_url)}" />',
            f'    <link rel="canonical" href="{html.escape(canonical_url)}" />',
        ]
    )

    index_path = _frontend_build_index_path()
    if not os.path.isfile(index_path):
        return (
            "<!DOCTYPE html><html><head>"
            f"{meta_block}"
            '</head><body><div id="root"></div></body></html>'
        )

    with open(index_path, encoding="utf-8") as handle:
        html_doc = handle.read()

    html_doc = re.sub(r"<title>[^<]*</title>", "", html_doc, count=1)
    html_doc = re.sub(
        r'<meta\s+name="description"[^>]*>',
        "",
        html_doc,
        count=1,
        flags=re.IGNORECASE,
    )
    return _inject_meta_block(html_doc, meta_block)


def share_game_moment_page(request: HttpRequest, share_token: str) -> HttpResponse:
    html_doc = render_share_moment_html(request, share_token)
    return HttpResponse(html_doc, content_type="text/html; charset=utf-8")
