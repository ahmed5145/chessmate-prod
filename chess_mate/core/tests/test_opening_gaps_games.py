"""Tests for repertoire gap lost-game enrichment (SRG-21)."""

from core.opening_gaps_games import (
    collect_lost_games_for_gap,
    enrich_batch_summary_opening_gaps,
    enrich_repertoire_gap,
)
from django.test import SimpleTestCase


class OpeningGapsGamesTests(SimpleTestCase):
    def setUp(self):
        self.gap = {
            "opening_name": "Queen's Pawn Game",
            "eco_code": "D00",
            "player_color": "white",
            "record": "0W-1L-0D",
            "summary": "This line needs review.",
        }
        self.per_game = [
            {
                "game_id": "game_0",
                "saved_game_id": 42,
                "result": "0-1",
                "player_color": "white",
                "opening_name": "Queen's Pawn Game",
                "eco_code": "D00",
                "opponent": "Rival",
                "platform": "lichess",
                "platform_game_url": "https://lichess.org/abc",
                "critical_moments": [
                    {"phase": "opening", "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1", "move_number": 2}
                ],
            },
            {
                "game_id": "game_1",
                "saved_game_id": 43,
                "result": "1-0",
                "player_color": "white",
                "opening_name": "Queen's Pawn Game",
                "eco_code": "D00",
            },
        ]

    def test_collects_losses_matching_gap(self):
        lost = collect_lost_games_for_gap(self.gap, self.per_game, batch_id=7)
        self.assertEqual(len(lost), 1)
        self.assertEqual(lost[0]["saved_game_id"], 42)
        self.assertEqual(lost[0]["href"], "/game/42/analysis?mode=review&batch=7&move=2")
        self.assertIn("opening_fen", lost[0])

    def test_enrich_gap_sets_loss_copy(self):
        enriched = enrich_repertoire_gap(self.gap, self.per_game, batch_id=3)
        self.assertEqual(enriched["loss_count"], 1)
        self.assertEqual(enriched["loss_copy"], "You lost 1 game in this line")
        self.assertEqual(len(enriched["lost_games"]), 1)

    def test_enrich_batch_summary_repertoire_gaps(self):
        summary = {"repertoire_gaps": [self.gap]}
        enriched = enrich_batch_summary_opening_gaps(summary, self.per_game, batch_id=9)
        gap = enriched["repertoire_gaps"][0]
        self.assertEqual(gap["loss_count"], 1)
        self.assertTrue(gap["lost_games"][0]["href"].startswith("/game/42/analysis"))

    def test_skips_games_without_saved_game_id(self):
        games = [{**self.per_game[0], "saved_game_id": None}]
        lost = collect_lost_games_for_gap(self.gap, games)
        self.assertEqual(lost, [])
