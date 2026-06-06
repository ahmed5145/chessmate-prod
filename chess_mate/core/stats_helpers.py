"""
Shared helpers for dashboard and profile statistics.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from django.db.models import Case, Count, IntegerField, Q, When

from .models import BatchAnalysisReport, Game, GameAnalysis, Profile


def get_game_counts(user) -> Dict[str, int]:
    """Aggregate win/loss/draw/total counts for a user."""
    stats = Game.objects.filter(user=user).aggregate(  # type: ignore[attr-defined]
        total=Count("id"),
        wins=Count(Case(When(result="win", then=1), output_field=IntegerField())),
        losses=Count(Case(When(result="loss", then=1), output_field=IntegerField())),
        draws=Count(Case(When(result="draw", then=1), output_field=IntegerField())),
        analyzed=Count(
            Case(
                When(Q(status="analyzed") | Q(analysis_status="analyzed"), then=1),
                output_field=IntegerField(),
            )
        ),
    )
    return {
        "total": stats["total"] or 0,
        "wins": stats["wins"] or 0,
        "losses": stats["losses"] or 0,
        "draws": stats["draws"] or 0,
        "analyzed": stats["analyzed"] or 0,
    }


def get_win_rate(total: int, wins: int) -> float:
    if total <= 0:
        return 0.0
    return round((wins / total) * 100, 1)


def get_time_control_distribution(user) -> Dict[str, float]:
    """Return percentage of games per time control category."""
    counts = {tc: 0 for tc in ("bullet", "blitz", "rapid", "classical")}
    games = Game.objects.filter(user=user).only("time_control_category", "time_control")  # type: ignore[attr-defined]
    total = 0
    for game in games.iterator():
        category = game.time_control_category or game.get_time_control_category()
        if category in counts:
            counts[category] += 1
            total += 1

    if total == 0:
        return {key: 0.0 for key in counts}

    return {key: round((value / total) * 100, 1) for key, value in counts.items()}


def _extract_accuracy_from_game(game) -> Optional[float]:
    analysis_payload = getattr(game, "analysis", None) or {}
    if isinstance(analysis_payload, dict):
        analysis_results = analysis_payload.get("analysis_results", analysis_payload)
        if isinstance(analysis_results, dict):
            summary = analysis_results.get("summary", {})
            if isinstance(summary, dict):
                raw = summary.get("user_accuracy", summary.get("accuracy"))
                if raw is not None:
                    return float(raw)

    game_analysis = getattr(game, "gameanalysis", None)
    if game_analysis and getattr(game_analysis, "analysis_data", None):
        summary = game_analysis.analysis_data.get("summary", {})
        if isinstance(summary, dict):
            raw = summary.get("user_accuracy", summary.get("accuracy"))
            if raw is not None:
                return float(raw)
    return None


def compute_user_average_accuracy(user, latest_batch_coach: Optional[Dict[str, Any]] = None) -> float:
    """Average move accuracy across analyzed games, with batch coach fallback."""
    if latest_batch_coach and latest_batch_coach.get("overall_accuracy_pct") is not None:
        return round(float(latest_batch_coach["overall_accuracy_pct"]), 1)

    accuracies: List[float] = []
    analyzed_games = (
        Game.objects.filter(user=user)  # type: ignore[attr-defined]
        .filter(Q(status="analyzed") | Q(analysis_status="analyzed"))
        .order_by("-date_played")[:50]
    )
    for game in analyzed_games:
        accuracy = _extract_accuracy_from_game(game)
        if accuracy is not None:
            accuracies.append(accuracy)

    if not accuracies:
        latest_batch = (
            BatchAnalysisReport.objects.filter(user=user, status__in=["completed", "partial"])
            .order_by("-created_at")
            .first()
        )
        if latest_batch and isinstance(latest_batch.batch_summary, dict):
            batch_accuracy = latest_batch.batch_summary.get("overall_accuracy_pct")
            if batch_accuracy is not None:
                return round(float(batch_accuracy), 1)

    if not accuracies:
        recent_analyses = GameAnalysis.objects.filter(game__user=user).order_by("-created_at")[:20]  # type: ignore[attr-defined]
        for analysis in recent_analyses:
            if not analysis.analysis_data:
                continue
            summary = analysis.analysis_data.get("summary", {})
            if isinstance(summary, dict):
                raw = summary.get("user_accuracy", summary.get("accuracy"))
                if raw is not None:
                    accuracies.append(float(raw))

    if not accuracies:
        return 0.0
    return round(sum(accuracies) / len(accuracies), 1)


def format_dashboard_insights(analysis_insights: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Map raw analysis insights to UI-friendly {type, text} entries."""
    formatted: List[Dict[str, str]] = []
    for item in analysis_insights or []:
        mistake_count = int(item.get("mistake_count") or 0)
        opponent = item.get("opponent") or "opponent"
        summary = (item.get("summary") or "").strip()
        if mistake_count >= 5:
            insight_type = "error"
        elif mistake_count >= 2:
            insight_type = "warning"
        else:
            insight_type = "success"

        if summary:
            text = f"vs {opponent}: {summary}"
        else:
            text = f"vs {opponent}: {mistake_count} mistake{'s' if mistake_count != 1 else ''} in recent analysis"

        formatted.append({"type": insight_type, "text": text[:240]})

    if not formatted:
        formatted.append(
            {
                "type": "success",
                "text": "Import and analyze games to unlock personalized performance insights.",
            }
        )
    return formatted


def compute_user_achievements(profile: Profile, game_counts: Optional[Dict[str, int]] = None) -> List[Dict[str, Any]]:
    """Derive achievement progress from profile and game data."""
    counts = game_counts or get_game_counts(profile.user)
    total_games = counts["total"]
    analyzed_games = counts["analyzed"]

    max_rating = max(
        profile.bullet_rating,
        profile.blitz_rating,
        profile.rapid_rating,
        profile.classical_rating,
        getattr(profile, "elo_rating", 1200) or 1200,
    )

    win_streak = _current_win_streak(profile.user)

    definitions = [
        {
            "name": "Novice Player",
            "description": "Import your first 10 games",
            "target": 10,
            "progress": min(total_games, 10),
        },
        {
            "name": "Dedicated Player",
            "description": "Build a library of 50 games",
            "target": 50,
            "progress": min(total_games, 50),
        },
        {
            "name": "Century Player",
            "description": "Track 100 games in ChessMate",
            "target": 100,
            "progress": min(total_games, 100),
        },
        {
            "name": "Rising Star",
            "description": "Reach a peak rating of 1500",
            "target": 1500,
            "progress": min(max_rating, 1500),
        },
        {
            "name": "Rating Star",
            "description": "Reach a peak rating of 1800",
            "target": 1800,
            "progress": min(max_rating, 1800),
        },
        {
            "name": "Win Streak",
            "description": "Win 3 games in a row",
            "target": 3,
            "progress": min(win_streak, 3),
        },
        {
            "name": "Unstoppable",
            "description": "Win 5 games in a row",
            "target": 5,
            "progress": min(win_streak, 5),
        },
        {
            "name": "Chess Student",
            "description": "Analyze 5 games",
            "target": 5,
            "progress": min(analyzed_games, 5),
        },
        {
            "name": "Deep Thinker",
            "description": "Analyze 20 games",
            "target": 20,
            "progress": min(analyzed_games, 20),
        },
        {
            "name": "Master Analyst",
            "description": "Analyze 50 games",
            "target": 50,
            "progress": min(analyzed_games, 50),
        },
        {
            "name": "Chess.com Connected",
            "description": "Link your Chess.com account",
            "target": 1,
            "progress": 1 if profile.chess_com_username else 0,
        },
        {
            "name": "Lichess Connected",
            "description": "Link your Lichess account",
            "target": 1,
            "progress": 1 if profile.lichess_username else 0,
        },
    ]

    achievements: List[Dict[str, Any]] = []
    for item in definitions:
        target = max(item["target"], 1)
        progress = item["progress"]
        achievements.append(
            {
                "name": item["name"],
                "description": item["description"],
                "target": target,
                "progress": progress,
                "completed": progress >= target,
            }
        )
    return achievements


def _current_win_streak(user) -> int:
    streak = 0
    recent_results = (
        Game.objects.filter(user=user, result__in=["win", "loss", "draw"])  # type: ignore[attr-defined]
        .order_by("-date_played")
        .values_list("result", flat=True)[:20]
    )
    for result in recent_results:
        if result == "win":
            streak += 1
        else:
            break
    return streak


def enrich_profile_payload(user, profile: Profile) -> Dict[str, Any]:
    """Build flat profile fields expected by the frontend."""
    counts = get_game_counts(user)
    performance_stats = profile.get_performance_stats() or {}
    if not performance_stats:
        performance_stats = {
            tc: {"games": 0, "winRate": 0, "drawRate": 0, "lossRate": 0}
            for tc in ("bullet", "blitz", "rapid", "classical")
        }

    return {
        "total_games": counts["total"],
        "win_rate": get_win_rate(counts["total"], counts["wins"]),
        "performance_stats": performance_stats,
        "time_control_distribution": get_time_control_distribution(user),
        "achievements": compute_user_achievements(profile, counts),
        "analyzed_games": counts["analyzed"],
        "wins": counts["wins"],
        "losses": counts["losses"],
        "draws": counts["draws"],
    }
