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
        "description": "Import games for your first batch coach reports",
        "features": [
            "50 game imports (1 credit per game)",
            "~5 batch coach reports (10 games each)",
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
        "description": "Regular batch coach analysis across a month of play",
        "features": [
            "100 game imports",
            "~10 batch coach reports (10 games each)",
            "Compare batches over time",
            "Credits never expire",
        ],
    },
    "premium": {
        "id": "premium",
        "name": "Coach Pro",
        "credits": 250,
        "price_cents": 3999,
        "description": "Serious improvement loop — many batches and imports",
        "features": [
            "250 game imports",
            "~25 batch coach reports (10 games each)",
            "Best value per batch report",
            "Credits never expire",
        ],
    },
}


def get_package(package_id: str) -> Optional[Dict[str, Any]]:
    return CREDIT_PACKAGES.get(str(package_id or "").strip())


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
