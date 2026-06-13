"""Tests for server-rendered share moment OG pages."""

from __future__ import annotations

import os
import tempfile

import pytest
from core.models import GameAnalysis
from core.share_preview import build_share_moment_meta, render_share_moment_html
from core.single_game_moment_share import get_or_create_moment_share
from django.test import override_settings


@pytest.mark.django_db
def test_build_share_moment_meta_from_payload():
    title, description = build_share_moment_meta(
        {
            "moment": {"move_number": 12, "eval_swing": 1.8},
            "game_context": {"opening_name": "Sicilian", "result": "loss"},
            "coaching": {
                "takeaway": "You lost the center on move 12",
                "do_today": "Practice c5 breaks before committing the queen.",
            },
        }
    )
    assert "You lost the center on move 12" in title
    assert "Move 12" in description
    assert "Sicilian" in description


def test_build_share_moment_meta_truncates_long_social_copy():
    title, description = build_share_moment_meta(
        {
            "moment": {"move_number": 19, "eval_swing": 8.42},
            "game_context": {
                "opening_name": "Queen's Pawn Game: Accelerated London System",
                "result": "loss",
            },
            "coaching": {
                "takeaway": "Focus on recognizing hanging pieces to avoid blunders.",
                "do_today": "Spend 5 minutes solving hanging-piece puzzles on Lichess.",
            },
        }
    )
    assert len(title) <= 60
    assert len(description) <= 125


@pytest.mark.django_db
def test_share_game_moment_page_injects_og_tags(rf, test_user, test_game):
    analysis = GameAnalysis.objects.create(
        game=test_game,
        analysis_data={
            "critical_moments": [
                {
                    "move_number": 12,
                    "eval_swing": 1.8,
                    "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                }
            ],
            "coaching": {
                "takeaway": "You lost the center on move 12",
                "do_today": "Practice c5 breaks before committing the queen.",
            },
        },
        feedback={},
        depth=20,
    )
    share_meta = get_or_create_moment_share(analysis, move_number=12)
    token = share_meta["token"]

    index_html = (
        "<!DOCTYPE html><html><head><title>Chess Mate</title>"
        '<meta name="description" content="fallback" />'
        '</head><body><div id="root"></div></body></html>'
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        build_dir = os.path.join(tmpdir, "frontend", "build")
        os.makedirs(build_dir)
        with open(os.path.join(build_dir, "index.html"), "w", encoding="utf-8") as handle:
            handle.write(index_html)

        with override_settings(BASE_DIR=tmpdir):
            request = rf.get(f"/share/game-moment/{token}/")
            html_doc = render_share_moment_html(request, token)

    assert 'property="og:title"' in html_doc
    assert "You lost the center on move 12" in html_doc
    assert 'property="og:site_name"' in html_doc
    assert "ChessMate" in html_doc
    assert 'property="og:image"' in html_doc
    assert 'name="twitter:card"' in html_doc
    assert 'content="summary_large_image"' in html_doc


@pytest.mark.django_db
def test_share_game_moment_url_with_and_without_trailing_slash(client, test_game):
    analysis = GameAnalysis.objects.create(
        game=test_game,
        analysis_data={
            "critical_moments": [{"move_number": 12, "eval_swing": 1.8}],
            "coaching": {"takeaway": "You lost the center on move 12"},
        },
        feedback={},
        depth=20,
    )
    token = get_or_create_moment_share(analysis, move_number=12)["token"]

    for path in (f"/share/game-moment/{token}", f"/share/game-moment/{token}/"):
        response = client.get(path)
        assert response.status_code == 200
        assert 'property="og:title"' in response.content.decode()
        assert "You lost the center on move 12" in response.content.decode()
