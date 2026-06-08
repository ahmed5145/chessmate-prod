"""Tests for public single-game moment share links."""

from django.urls import reverse

from core.models import GameAnalysis
from core.single_game_moment_share import get_or_create_moment_share


def test_create_and_fetch_public_moment_share(authenticated_client, test_user, test_game):
    analysis = GameAnalysis.objects.create(
        game=test_game,
        analysis_data={
            "coaching": {
                "takeaway": "The swing on move 12 decided the game.",
                "do_today": "Replay that tactic for five minutes.",
            },
            "critical_moments": [
                {
                    "move_number": 12,
                    "type": "mistake",
                    "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
                    "played_move": "Nf3",
                    "best_move": "d4",
                    "eval_swing": 1.4,
                }
            ],
        },
        feedback={},
        depth=20,
    )

    share_url = reverse("create_game_moment_share", kwargs={"game_id": test_game.id})
    create_response = authenticated_client.post(share_url, {"move": 12}, format="json")
    assert create_response.status_code == 200
    assert create_response.data["share_token"]
    assert create_response.data["share_url"]

    analysis.refresh_from_db()
    share_meta = get_or_create_moment_share(analysis, move_number=12)
    assert share_meta["token"] == create_response.data["share_token"]

    public_url = reverse(
        "public_game_moment",
        kwargs={"share_token": create_response.data["share_token"]},
    )
    public_response = authenticated_client.get(public_url)
    assert public_response.status_code == 200
    assert public_response.data["moment"]["move_number"] == 12
    assert "opponent" not in (public_response.data.get("game_context") or {})
    assert public_response.data["coaching"]["takeaway"] == "The swing on move 12 decided the game."


def test_public_moment_share_requires_completed_analysis(authenticated_client, test_game):
    share_url = reverse("create_game_moment_share", kwargs={"game_id": test_game.id})
    response = authenticated_client.post(share_url, {}, format="json")
    assert response.status_code == 400
