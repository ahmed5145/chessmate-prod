"""
Credit packages — single source of truth for Stripe checkout and the Credits UI.

Credits are consumed when importing games (1 credit per game). Batch coach analysis
is included once games are on the account (BATCH_CREDITS_PER_GAME defaults to 0).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

BATCH_GAMES_RECOMMENDED = 10


def _batch_reports_from_credits(credits: int) -> int:
    return max(1, credits // BATCH_GAMES_RECOMMENDED)


CREDIT_PACKAGES: Dict[str, Dict[str, Any]] = {
    "basic": {
        "id": "basic",
        "name": "Coach Starter",
        "credits": 50,
        "price_cents": 999,
        "description": "Buy credits once — import your first batch of games",
        "features": [
            "One-time purchase (not a subscription)",
            "50 game imports (1 credit per game)",
            "~5 Batch Coach reports (10 games each)",
            "Full Stockfish + AI coaching per batch",
            "Credits never expire",
        ],
    },
    "pro": {
        "id": "pro",
        "name": "Coach Plus",
        "credits": 100,
        "price_cents": 1799,
        "popular": True,
        "description": "Buy credits once for regular Batch Coach",
        "features": [
            "One-time purchase (not a subscription)",
            "100 game imports",
            "~10 Batch Coach reports (10 games each)",
            "Compare batches over time",
            "Credits never expire",
        ],
    },
    "premium": {
        "id": "premium",
        "name": "Coach Pro",
        "credits": 250,
        "price_cents": 3999,
        "description": "Buy credits once for a serious improvement loop",
        "features": [
            "One-time purchase (not a subscription)",
            "250 game imports",
            "~25 Batch Coach reports (10 games each)",
            "Best value per batch report",
            "Credits never expire",
        ],
    },
}


def get_package(package_id: str) -> Optional[Dict[str, Any]]:
    return CREDIT_PACKAGES.get(str(package_id or "").strip())


def credit_model_for_api() -> Dict[str, Any]:
    """
    User-facing credit economics (aligned with docs/PRICING_UNIT_ECONOMICS.md).
    """
    from django.conf import settings

    batch_per_game = int(getattr(settings, "BATCH_CREDITS_PER_GAME", 0))
    signup_bonus = int(getattr(settings, "SIGNUP_BONUS_CREDITS", 15))
    single_game = int(getattr(settings, "SINGLE_GAME_ANALYSIS_CREDITS", 1))

    return {
        "credits_per_imported_game": 1,
        "batch_credits_per_game": batch_per_game,
        "signup_bonus_credits": signup_bonus,
        "single_game_analysis_credits": single_game,
        "batch_games_recommended": BATCH_GAMES_RECOMMENDED,
        "batch_included": batch_per_game == 0,
        "summary_points": [
            "1 credit per game import from Chess.com or Lichess",
            (
                "Batch Coach is included once games are on your account"
                if batch_per_game == 0
                else f"Batch Coach costs {batch_per_game} credit(s) per game in the batch"
            ),
            f"New accounts receive {signup_bonus} free credits",
            f"Optional single-game deep analysis costs {single_game} credit per game",
            "Credits are sold as one-time packs — not a subscription",
            "Purchased credits do not expire while your account stays active",
        ],
    }


def list_packages_for_api() -> List[Dict[str, Any]]:
    """Public package list for GET /api/v1/credits/packages/."""
    out: List[Dict[str, Any]] = []
    for pkg in CREDIT_PACKAGES.values():
        credits = int(pkg["credits"])
        out.append(
            {
                "id": pkg["id"],
                "name": pkg["name"],
                "credits": credits,
                "price_cents": pkg["price_cents"],
                "price_display": f"${pkg['price_cents'] / 100:.2f}",
                "description": pkg["description"],
                "popular": bool(pkg.get("popular")),
                "features": list(pkg.get("features") or []),
                "batch_reports_approx": _batch_reports_from_credits(credits),
                "batch_games_per_report": BATCH_GAMES_RECOMMENDED,
            }
        )
    return out
