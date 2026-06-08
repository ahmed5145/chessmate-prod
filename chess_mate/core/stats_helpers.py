"""
Shared helpers for dashboard and profile statistics.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from django.db.models import Case, Count, IntegerField, Q, When
from django.utils import timezone

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


def resolve_game_opponent_display(game: Any, profile: Optional[Profile]) -> str:
    """Opponent name for UI — prefers stored `opponent`, else infers from PGN headers + linked accounts."""
    stored = ""
    if isinstance(game, dict):
        stored = str(game.get("opponent") or "").strip()
        white = game.get("white") or ""
        black = game.get("black") or ""
        platform = game.get("platform") or ""
    else:
        stored = str(getattr(game, "opponent", None) or "").strip()
        white = getattr(game, "white", "") or ""
        black = getattr(game, "black", "") or ""
        platform = getattr(game, "platform", "") or ""

    if stored and stored.lower() != "unknown":
        return stored

    class _GameRow:
        def __init__(self, white_name: str, black_name: str, platform_name: str):
            self.white = white_name
            self.black = black_name
            self.platform = platform_name

    is_white = _is_user_white(_GameRow(white, black, platform), profile)
    if is_white is True:
        return black or "Unknown"
    if is_white is False:
        return white or "Unknown"
    return black or white or "Unknown"


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


def build_single_game_context(game: Game, profile: Optional[Profile] = None) -> Dict[str, Any]:
    """Rich header context for single-game analysis UI."""
    is_white = _is_user_white(game, profile)
    player_color: Optional[str]
    if is_white is True:
        player_color = "white"
    elif is_white is False:
        player_color = "black"
    else:
        player_color = None

    date_played = None
    if getattr(game, "date_played", None):
        date_played = game.date_played.isoformat()

    opening_name = (getattr(game, "opening_name", None) or "").strip()
    if not opening_name or opening_name.lower() == "unknown opening":
        opening_name = (getattr(game, "opening_played", None) or "").strip() or opening_name

    return {
        "id": game.id,
        "white": game.white,
        "black": game.black,
        "opponent": resolve_game_opponent_display(game, profile),
        "player_color": player_color,
        "result": game.result,
        "opening_name": opening_name,
        "eco": getattr(game, "eco_code", None),
        "platform": game.platform,
        "platform_game_url": game.game_url,
        "date_played": date_played,
    }


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

        entry: Dict[str, Any] = {"type": insight_type, "text": text[:240]}
        if item.get("game_id"):
            entry["game_id"] = item["game_id"]
        formatted.append(entry)

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


GENERIC_DASHBOARD_INSIGHT_PATTERNS = (
    "import and analyze games",
    "run batch coach or analyze",
    "unlock personalized",
    "unlock more personalized",
)


def _is_generic_dashboard_insight(text: str) -> bool:
    lowered = (text or "").lower()
    return any(pattern in lowered for pattern in GENERIC_DASHBOARD_INSIGHT_PATTERNS)


def _is_recent_game_analyzed(game: Dict[str, Any]) -> bool:
    status_value = str(game.get("analysis_status") or game.get("status") or "").lower()
    return status_value in ("analyzed", "completed") or bool(game.get("analysis"))


def build_dashboard_next_action(
    *,
    total_games: int,
    analyzed_games: int,
    recent_games: Optional[List[Dict[str, Any]]] = None,
    latest_batch_coach: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Single primary CTA for the dashboard hero."""
    recent = recent_games or []
    first_unanalyzed = next((game for game in recent if not _is_recent_game_analyzed(game)), None)
    coach = latest_batch_coach if isinstance(latest_batch_coach, dict) else {}

    if total_games <= 0:
        return {
            "type": "import_games",
            "title": "Import games to get started",
            "description": "Pull games from Chess.com or Lichess to unlock analysis and coaching.",
            "cta_label": "Import games",
            "cta_to": "/fetch-games",
            "secondary_links": [{"label": "Credits & pricing", "to": "/credits"}],
        }

    coach_summary = (coach.get("summary") or "").strip()
    batch_id = coach.get("batch_id")
    if coach_summary and batch_id:
        summary_preview = coach_summary
        if len(summary_preview) > 180:
            summary_preview = f"{summary_preview[:180]}…"
        return {
            "type": "open_batch_report",
            "title": "Pick up your latest coach report",
            "description": summary_preview,
            "cta_label": "Open report",
            "cta_to": f"/batch-report/{batch_id}",
            "secondary_links": [
                {"label": "Run new batch", "to": "/batch-analysis"},
                {"label": "View games", "to": "/games"},
            ],
        }

    if total_games >= 5:
        secondary_links = [{"label": "View games", "to": "/games"}]
        if first_unanalyzed and first_unanalyzed.get("id"):
            secondary_links.append(
                {
                    "label": "Optional: deep review one game",
                    "to": f"/game/{first_unanalyzed['id']}/analysis",
                }
            )
        return {
            "type": "start_batch_coach",
            "title": "Run Batch Coach on your games",
            "description": (
                "Batch Coach analyzes 5–30 imported games and finds cross-game patterns — "
                "no need to run single-game review first."
            ),
            "cta_label": "Start Batch Coach",
            "cta_to": "/batch-analysis",
            "secondary_links": secondary_links,
        }

    remaining = 5 - total_games
    plural = "" if remaining == 1 else "s"
    secondary_links = [{"label": "View games", "to": "/games"}]
    if first_unanalyzed and first_unanalyzed.get("id"):
        secondary_links.append(
            {
                "label": "Optional: try deep review",
                "to": f"/game/{first_unanalyzed['id']}/analysis",
            }
        )
    return {
        "type": "import_for_batch",
        "title": f"Import {remaining} more game{plural} for Batch Coach",
        "description": ("Batch Coach needs at least 5 games. Optional: run a depth-20 review on one game (+1 credit)."),
        "cta_label": "Import games",
        "cta_to": "/fetch-games",
        "secondary_links": secondary_links,
    }


def _is_batch_accuracy_insight(text: str) -> bool:
    lowered = (text or "").lower()
    return "latest batch coach" in lowered and "accuracy" in lowered


def build_dashboard_focus_insight(
    *,
    insights: Optional[List[Dict[str, Any]]] = None,
    analysis_insights: Optional[List[Dict[str, Any]]] = None,
    latest_batch_coach: Optional[Dict[str, Any]] = None,
    total_games: int = 0,
    hero_action_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Primary coaching insight for the dashboard focus card."""
    formatted = insights or []
    raw_items = analysis_insights or []
    coach = latest_batch_coach if isinstance(latest_batch_coach, dict) else {}
    batch_id = coach.get("batch_id")

    meaningful = [
        item
        for item in formatted
        if (item.get("text") or "").strip() and not _is_generic_dashboard_insight(item["text"])
    ]

    priority = next(
        (
            item
            for item in meaningful
            if any(token in item["text"].lower() for token in ("top focus", "opening to review", "weakest", "priority"))
        ),
        None,
    )
    if priority and batch_id:
        return {
            "type": priority.get("type") or "warning",
            "text": priority["text"],
            "href": f"/batch-report/{batch_id}",
            "action_label": "Open report",
        }

    if meaningful:
        first = next((item for item in meaningful if not _is_batch_accuracy_insight(item.get("text", ""))), None)
        if first:
            linked = next((item for item in raw_items if item.get("game_id")), None)
            game_id = first.get("game_id") or (linked or {}).get("game_id")
            href = f"/game/{game_id}/analysis" if game_id else None
            if not href and batch_id and hero_action_type == "open_batch_report":
                href = f"/batch-report/{batch_id}"
            return {
                "type": first.get("type") or "success",
                "text": first["text"],
                "href": href,
                "action_label": "View game" if game_id else ("Open report" if href else None),
            }

    coach_summary = (coach.get("summary") or "").strip()
    if coach_summary and batch_id and hero_action_type != "open_batch_report":
        meta_parts = []
        if coach.get("games_count"):
            meta_parts.append(f"{coach['games_count']} games")
        accuracy = coach.get("overall_accuracy_pct")
        if accuracy is not None:
            try:
                meta_parts.append(f"{float(accuracy):.1f}% accuracy")
            except (TypeError, ValueError):
                pass
        return {
            "type": "success",
            "text": coach_summary,
            "href": f"/batch-report/{batch_id}",
            "action_label": "Open full report",
            "meta": " · ".join(meta_parts),
        }

    if hero_action_type == "open_batch_report" and batch_id:
        return {
            "type": "success",
            "text": "Your report includes game-by-game breakdowns, priorities, and practice links.",
            "href": f"/batch-report/{batch_id}",
            "action_label": "View breakdown",
        }

    if total_games > 0:
        return {
            "type": "success",
            "text": (
                "Run Batch Coach to surface patterns across your games — " "or try an optional deep review on one game."
            ),
            "href": "/batch-analysis",
            "action_label": "Start Batch Coach",
        }

    return {
        "type": "success",
        "text": "Import games to unlock Batch Coach and personalized coaching.",
        "href": "/fetch-games",
        "action_label": "Import games",
    }


def parse_last_dashboard_visit(preferences: Optional[Dict[str, Any]]) -> Optional[datetime]:
    """Parse stored dashboard visit timestamp from profile preferences."""
    if not isinstance(preferences, dict):
        return None
    raw = preferences.get("last_dashboard_visit_at")
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed)
        return parsed
    except (ValueError, TypeError):
        return None


def _pluralize(count: int, singular: str, plural: str) -> str:
    return singular if count == 1 else plural


def build_dashboard_since_last_visit(user, since: Optional[datetime]) -> Dict[str, Any]:
    """Summarize activity since the user's previous dashboard visit."""
    if since is None:
        return {
            "has_previous_visit": False,
            "show_banner": False,
            "games_imported": 0,
            "games_analyzed": 0,
            "batch_reports": 0,
            "summary_lines": [],
        }

    games_imported = Game.objects.filter(user=user, created_at__gt=since).count()  # type: ignore[attr-defined]
    games_analyzed = Game.objects.filter(user=user, analysis_completed_at__gt=since).count()  # type: ignore[attr-defined]
    if games_analyzed == 0:
        games_analyzed = (
            Game.objects.filter(user=user)  # type: ignore[attr-defined]
            .filter(ANALYZED_GAME_Q)
            .filter(updated_at__gt=since)
            .count()
        )

    batch_reports = BatchAnalysisReport.objects.filter(  # type: ignore[attr-defined]
        user=user,
        status__in=["completed", "partial"],
        created_at__gt=since,
    ).count()

    summary_lines: List[str] = []
    if games_analyzed:
        summary_lines.append(f"{games_analyzed} {_pluralize(games_analyzed, 'game', 'games')} analyzed")
    if batch_reports:
        summary_lines.append(f"{batch_reports} coach {_pluralize(batch_reports, 'report', 'reports')} ready")
    if games_imported and not games_analyzed:
        summary_lines.append(f"{games_imported} {_pluralize(games_imported, 'game', 'games')} imported")

    return {
        "has_previous_visit": True,
        "show_banner": bool(summary_lines),
        "games_imported": games_imported,
        "games_analyzed": games_analyzed,
        "batch_reports": batch_reports,
        "summary_lines": summary_lines,
    }


def mark_dashboard_visit(profile: Profile) -> None:
    """Record the current time as the user's latest dashboard visit."""
    prefs = dict(profile.preferences) if isinstance(profile.preferences, dict) else {}
    prefs["last_dashboard_visit_at"] = timezone.now().isoformat()
    profile.preferences = prefs
    profile.save(update_fields=["preferences"])


def build_dashboard_hero_metrics(
    *,
    total_games: int,
    analyzed_games: int,
    average_accuracy: float,
    win_rate: float,
) -> List[Dict[str, str]]:
    """Compact hero metric chips for the dashboard."""
    metrics: List[Dict[str, str]] = []
    if total_games > 0:
        metrics.append({"label": "Analyzed", "value": f"{analyzed_games} / {total_games}"})
    if analyzed_games >= 3 and average_accuracy > 0:
        metrics.append({"label": "Avg accuracy", "value": f"{average_accuracy}%"})
    if total_games >= 10 and win_rate >= 0:
        metrics.append({"label": "Win rate", "value": f"{win_rate}%"})
    return metrics


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
