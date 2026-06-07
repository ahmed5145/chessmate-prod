"""
Shared helpers for dashboard and profile statistics.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from django.db.models import Case, Count, IntegerField, Q, When

from .models import BatchAnalysisReport, Game, GameAnalysis, Profile

# Celery sets analysis_status="completed"; legacy paths used "analyzed".
ANALYZED_GAME_Q = Q(status="analyzed") | Q(analysis_status="analyzed") | Q(analysis_status="completed")


def get_game_counts(user) -> Dict[str, int]:
    """Aggregate win/loss/draw/total counts for a user."""
    stats = Game.objects.filter(user=user).aggregate(  # type: ignore[attr-defined]
        total=Count("id"),
        wins=Count(Case(When(result="win", then=1), output_field=IntegerField())),
        losses=Count(Case(When(result="loss", then=1), output_field=IntegerField())),
        draws=Count(Case(When(result="draw", then=1), output_field=IntegerField())),
        analyzed=Count("id", filter=ANALYZED_GAME_Q),
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


def _is_user_white(game, profile: Optional[Profile]) -> Optional[bool]:
    """Return True if the account owner played white, False if black, else None."""
    names: List[str] = []
    if profile:
        platform_user = profile.get_platform_username(game.platform)
        if platform_user:
            names.append(platform_user)
    username = getattr(getattr(game, "user", None), "username", None)
    if username:
        names.append(username)

    for name in names:
        if game.white and name.lower() == game.white.lower():
            return True
        if game.black and name.lower() == game.black.lower():
            return False
    return None


def _normalize_accuracy_value(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    # Legacy 0–1 stability scores stored as overall_accuracy (not percent).
    if 0 < value <= 1:
        return round(value * 100, 1)
    return round(value, 1)


def _extract_accuracy_from_analysis_data(
    analysis_data: Optional[Dict[str, Any]],
    profile: Optional[Profile],
    game,
) -> Optional[float]:
    if not isinstance(analysis_data, dict):
        return None

    metrics = analysis_data.get("metrics", {})
    if isinstance(metrics, dict):
        overall = metrics.get("overall", {})
        if isinstance(overall, dict):
            for key in ("accuracy", "user_accuracy", "player_accuracy"):
                normalized = _normalize_accuracy_value(overall.get(key))
                if normalized is not None:
                    return normalized

    summary = analysis_data.get("summary", {})
    if isinstance(summary, dict):
        overall = summary.get("overall", {})
        if isinstance(overall, dict):
            for key in ("accuracy", "user_accuracy", "player_accuracy"):
                normalized = _normalize_accuracy_value(overall.get(key))
                if normalized is not None:
                    return normalized
        for key in ("user_accuracy", "accuracy", "player_accuracy"):
            normalized = _normalize_accuracy_value(summary.get(key))
            if normalized is not None:
                return normalized

    analysis_results = analysis_data.get("analysis_results", {})
    if isinstance(analysis_results, dict):
        nested_summary = analysis_results.get("summary", {})
        if isinstance(nested_summary, dict):
            for key in ("user_accuracy", "accuracy", "player_accuracy"):
                normalized = _normalize_accuracy_value(nested_summary.get(key))
                if normalized is not None:
                    return normalized

    return None


def _extract_accuracy_from_game(game, profile: Optional[Profile] = None) -> Optional[float]:
    analysis_payload = getattr(game, "analysis", None) or {}
    if isinstance(analysis_payload, dict):
        accuracy = _extract_accuracy_from_analysis_data(analysis_payload, profile, game)
        if accuracy is not None:
            return accuracy

    game_analysis = getattr(game, "gameanalysis", None)
    if game_analysis:
        if getattr(game_analysis, "analysis_data", None):
            accuracy = _extract_accuracy_from_analysis_data(game_analysis.analysis_data, profile, game)
            if accuracy is not None:
                return accuracy

        is_white = _is_user_white(game, profile)
        if is_white is True and game_analysis.accuracy_white is not None:
            return _normalize_accuracy_value(game_analysis.accuracy_white)
        if is_white is False and game_analysis.accuracy_black is not None:
            return _normalize_accuracy_value(game_analysis.accuracy_black)

        if game_analysis.accuracy_white is not None and game_analysis.accuracy_black is not None:
            return _normalize_accuracy_value(max(game_analysis.accuracy_white, game_analysis.accuracy_black))

    return None


def _accuracy_from_per_game_result(result: Any) -> Optional[float]:
    if not isinstance(result, dict):
        return None
    for key in ("accuracy", "accuracy_pct", "player_accuracy"):
        normalized = _normalize_accuracy_value(result.get(key))
        if normalized is not None:
            return normalized
    metrics = result.get("metrics", {})
    if isinstance(metrics, dict):
        overall = metrics.get("overall", {})
        if isinstance(overall, dict):
            normalized = _normalize_accuracy_value(overall.get("accuracy"))
            if normalized is not None:
                return normalized
    return None


def _batch_accuracy_from_summary(batch_summary: Optional[Dict[str, Any]]) -> Optional[float]:
    if not isinstance(batch_summary, dict):
        return None
    pct = _normalize_accuracy_value(batch_summary.get("overall_accuracy_pct"))
    if pct is not None:
        return pct
    return _normalize_accuracy_value(batch_summary.get("overall_accuracy"))


def _batch_stats(user) -> Dict[str, Any]:
    completed = BatchAnalysisReport.objects.filter(user=user, status__in=["completed", "partial"])
    batch_count = completed.count()
    max_games = 0
    best_accuracy = 0.0

    for report in completed.only("batch_summary", "games_count").iterator():
        games_count = report.games_count or 0
        max_games = max(max_games, games_count)
        accuracy = _batch_accuracy_from_summary(
            report.batch_summary if isinstance(report.batch_summary, dict) else None
        )
        if accuracy is not None:
            best_accuracy = max(best_accuracy, accuracy)

    return {
        "batch_count": batch_count,
        "max_games_in_batch": max_games,
        "best_batch_accuracy": best_accuracy,
    }


def compute_user_average_accuracy(
    user,
    profile: Optional[Profile] = None,
    latest_batch_summary: Optional[Dict[str, Any]] = None,
) -> float:
    """Average move accuracy across analyzed games and batch reports."""
    accuracies: List[float] = []

    batch_accuracy = _batch_accuracy_from_summary(latest_batch_summary)
    if batch_accuracy is not None:
        accuracies.append(batch_accuracy)

    if not accuracies:
        for report in (
            BatchAnalysisReport.objects.filter(user=user, status__in=["completed", "partial"])
            .order_by("-created_at")
            .only("batch_summary", "per_game_results")[:5]
        ):
            accuracy = _batch_accuracy_from_summary(
                report.batch_summary if isinstance(report.batch_summary, dict) else None
            )
            if accuracy is not None:
                accuracies.append(accuracy)
                continue
            for game_result in report.per_game_results or []:
                game_accuracy = _accuracy_from_per_game_result(game_result)
                if game_accuracy is not None:
                    accuracies.append(game_accuracy)

    if profile is None:
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            profile = None

    analyzed_games = (
        Game.objects.filter(user=user)  # type: ignore[attr-defined]
        .filter(ANALYZED_GAME_Q)
        .select_related("gameanalysis")
        .order_by("-date_played")[:50]
    )
    for game in analyzed_games:
        accuracy = _extract_accuracy_from_game(game, profile)
        if accuracy is not None:
            accuracies.append(accuracy)

    recent_analyses = (
        GameAnalysis.objects.filter(game__user=user)  # type: ignore[attr-defined]
        .select_related("game")
        .order_by("-created_at")[:30]
    )
    for analysis in recent_analyses:
        accuracy = _extract_accuracy_from_analysis_data(
            analysis.analysis_data,
            profile,
            analysis.game,
        )
        if accuracy is not None:
            accuracies.append(accuracy)
        elif analysis.accuracy_white is not None or analysis.accuracy_black is not None:
            is_white = _is_user_white(analysis.game, profile)
            if is_white is True and analysis.accuracy_white is not None:
                accuracies.append(_normalize_accuracy_value(analysis.accuracy_white))
            elif is_white is False and analysis.accuracy_black is not None:
                accuracies.append(_normalize_accuracy_value(analysis.accuracy_black))
            elif analysis.accuracy_white is not None:
                accuracies.append(_normalize_accuracy_value(analysis.accuracy_white))

    if not accuracies:
        return 0.0
    return round(sum(accuracies) / len(accuracies), 1)


def format_dashboard_insights(
    analysis_insights: List[Dict[str, Any]],
    *,
    total_games: int = 0,
    latest_batch_coach: Optional[Dict[str, Any]] = None,
    latest_batch_summary: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
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

    if not formatted and (total_games > 0 or latest_batch_coach):
        batch_insights = _batch_dashboard_insights(latest_batch_coach, latest_batch_summary)
        formatted.extend(batch_insights)

    if not formatted:
        formatted.append(
            {
                "type": "success",
                "text": "Import and analyze games to unlock personalized performance insights.",
            }
        )
    return formatted


def _batch_dashboard_insights(
    latest_batch_coach: Optional[Dict[str, Any]],
    latest_batch_summary: Optional[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """Build performance insights from batch coach when per-game analysis is unavailable."""
    insights: List[Dict[str, str]] = []
    summary = latest_batch_summary if isinstance(latest_batch_summary, dict) else {}
    coach = latest_batch_coach if isinstance(latest_batch_coach, dict) else {}

    accuracy = summary.get("overall_accuracy_pct") or coach.get("overall_accuracy_pct")
    if accuracy is not None:
        try:
            accuracy_val = float(accuracy)
            insight_type = "success" if accuracy_val >= 80 else "warning" if accuracy_val >= 65 else "error"
            insights.append(
                {
                    "type": insight_type,
                    "text": f"Latest batch coach: {accuracy_val:.1f}% overall accuracy across your games.",
                }
            )
        except (TypeError, ValueError):
            pass

    priorities = summary.get("top_priorities") or summary.get("priorities") or []
    if isinstance(priorities, list) and priorities:
        first = priorities[0]
        if isinstance(first, dict):
            priority_text = (first.get("title") or first.get("priority") or first.get("text") or "").strip()
        else:
            priority_text = str(first).strip()
        if priority_text:
            insights.append({"type": "warning", "text": f"Top focus area: {priority_text[:200]}"})

    opening_weakness = summary.get("opening_weakness") or summary.get("weakest_opening")
    if opening_weakness:
        if isinstance(opening_weakness, dict):
            opening_name = opening_weakness.get("name") or opening_weakness.get("opening") or "an opening"
        else:
            opening_name = str(opening_weakness)
        insights.append({"type": "warning", "text": f"Opening to review: {opening_name[:120]}"})

    coach_summary = (coach.get("summary") or "").strip()
    if coach_summary and len(insights) < 3:
        insights.append({"type": "success", "text": coach_summary[:240]})

    return insights[:3]


def compute_user_achievements(profile: Profile, game_counts: Optional[Dict[str, int]] = None) -> List[Dict[str, Any]]:
    """Derive achievement progress from profile and game data."""
    counts = game_counts or get_game_counts(profile.user)
    total_games = counts["total"]
    analyzed_games = counts["analyzed"]
    batch_stats = _batch_stats(profile.user)
    batch_count = batch_stats["batch_count"]
    max_games_in_batch = batch_stats["max_games_in_batch"]
    best_batch_accuracy = batch_stats["best_batch_accuracy"]

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
            "name": "Batch Starter",
            "description": "Complete your first batch coach report",
            "target": 1,
            "progress": min(batch_count, 1),
        },
        {
            "name": "Batch Regular",
            "description": "Complete 5 batch coach reports",
            "target": 5,
            "progress": min(batch_count, 5),
        },
        {
            "name": "Batch Veteran",
            "description": "Complete 10 batch coach reports",
            "target": 10,
            "progress": min(batch_count, 10),
        },
        {
            "name": "Deep Batch",
            "description": "Run a batch coach report on 20+ games",
            "target": 20,
            "progress": min(max_games_in_batch, 20),
        },
        {
            "name": "Full Roster Batch",
            "description": "Run a 30-game batch coach report",
            "target": 30,
            "progress": min(max_games_in_batch, 30),
        },
        {
            "name": "Sharp Batch",
            "description": "Reach 80% accuracy in a batch report",
            "target": 80,
            "progress": min(int(best_batch_accuracy), 80),
        },
        {
            "name": "Elite Batch",
            "description": "Reach 90% accuracy in a batch report",
            "target": 90,
            "progress": min(int(best_batch_accuracy), 90),
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

    latest_batch_summary = (
        BatchAnalysisReport.objects.filter(user=user, status__in=["completed", "partial"])
        .order_by("-created_at")
        .values_list("batch_summary", flat=True)
        .first()
    )
    batch_summary = latest_batch_summary if isinstance(latest_batch_summary, dict) else None

    return {
        "total_games": counts["total"],
        "win_rate": get_win_rate(counts["total"], counts["wins"]),
        "performance_stats": performance_stats,
        "time_control_distribution": get_time_control_distribution(user),
        "achievements": compute_user_achievements(profile, counts),
        "analyzed_games": counts["analyzed"],
        "average_accuracy": compute_user_average_accuracy(user, profile, batch_summary),
        "wins": counts["wins"],
        "losses": counts["losses"],
        "draws": counts["draws"],
    }
