"""
Dashboard-related views for the ChessMate application.
This module handles user dashboard functionality including statistics and insights.
"""

# pylint: disable=no-member

import logging
import sys
from datetime import timedelta

from django.db.models import (
    Case,
    Count,
    IntegerField,
    Q,
    When,
)
from django.utils import timezone
from rest_framework import status

# Third-party imports
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .cache import cache_delete, cache_get, cache_set, generate_cache_key

# Local application imports
from .models import Game, GameAnalysis, Profile

# Configure logging
logger = logging.getLogger(__name__)
DASHBOARD_EXCEPTIONS = (ValueError, TypeError, RuntimeError, AttributeError, KeyError)

for module_name in (
    "core.dashboard_views",
    "chess_mate.core.dashboard_views",
    "chessmate_prod.chess_mate.core.dashboard_views",
):
    sys.modules.setdefault(module_name, sys.modules[__name__])


class _CacheManager:
    def get(self, key, default=None):
        return cache_get(key, default)

    def set(self, key, value, timeout=None):
        return cache_set(key, value, timeout=timeout)

    def delete(self, key):
        return cache_delete(key)


cache_manager = _CacheManager()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_view(request):
    """
    Get dashboard data for the current user.
    This view is heavily optimized for performance since it's frequently accessed.
    """
    try:
        user = request.user

        # Check cache first
        cache_key = generate_cache_key("dashboard_data", user.id)
        cached_data = cache_manager.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        # Get user's profile with a single query
        try:
            profile = Profile.objects.select_related("user").get(user=user)  # type: ignore[attr-defined]
        except Profile.DoesNotExist:  # type: ignore[attr-defined]
            return Response({"error": "User profile not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get recent games with optimized query - limit select fields
        recent_games = (
            Game.objects.filter(user=user)  # type: ignore[attr-defined]
            .order_by("-date_played")
            .values("id", "white", "black", "result", "date_played", "platform", "opening_name", "status")[:5]
        )

        # Use database aggregation instead of Python counting
        game_stats = Game.objects.filter(user=user).aggregate(  # type: ignore[attr-defined]
            total_games=Count("id"),
            analyzed_games=Count(
                Case(
                    When(Q(status="analyzed") | Q(analysis_status="analyzed"), then=1),
                    output_field=IntegerField(),
                )
            ),
            wins=Count(Case(When(result="win", then=1), output_field=IntegerField())),
            losses=Count(Case(When(result="loss", then=1), output_field=IntegerField())),
            draws=Count(Case(When(result="draw", then=1), output_field=IntegerField())),
        )

        # Calculate percentages at the database level when possible
        total_games = game_stats["total_games"]
        analysis_count = game_stats["analyzed_games"]
        win_count = game_stats["wins"]
        loss_count = game_stats["losses"]
        draw_count = game_stats["draws"]

        analyzed_game_stats = Game.objects.filter(user=user).filter(  # type: ignore[attr-defined]
            Q(status="analyzed") | Q(analysis_status="analyzed")
        ).aggregate(
            wins=Count(Case(When(result="win", then=1), output_field=IntegerField())),
            losses=Count(Case(When(result="loss", then=1), output_field=IntegerField())),
            draws=Count(Case(When(result="draw", then=1), output_field=IntegerField())),
        )
        analyzed_win_count = analyzed_game_stats["wins"]
        analyzed_loss_count = analyzed_game_stats["losses"]
        analyzed_draw_count = analyzed_game_stats["draws"]

        if total_games > 0:
            win_rate = (win_count / total_games) * 100
            loss_rate = (loss_count / total_games) * 100
            draw_rate = (draw_count / total_games) * 100
        else:
            win_rate = loss_rate = draw_rate = 0

        # Get performance by time control using database aggregation
        time_control_performance = {}
        for time_control in ["bullet", "blitz", "rapid", "classical"]:
            # Query games with this time control category
            tc_stats = Game.objects.filter(user=user, time_control_category=time_control).aggregate(  # type: ignore[attr-defined]
                count=Count("id"), wins=Count(Case(When(result="win", then=1), output_field=IntegerField()))
            )

            tc_count = tc_stats["count"]
            tc_wins = tc_stats["wins"]

            if tc_count > 0:
                win_percentage = (tc_wins / tc_count) * 100
            else:
                win_percentage = 0

            time_control_performance[time_control] = {"total": tc_count, "win_rate": round(win_percentage, 1)}

        # Get platform stats using database aggregation
        platform_stats = (
            Game.objects.filter(user=user)  # type: ignore[attr-defined]
            .values("platform")
            .annotate(count=Count("id"), wins=Count(Case(When(result="win", then=1), output_field=IntegerField())))
        )

        platform_data = {}
        for platform in platform_stats:
            platform_name = platform["platform"]
            game_count = platform["count"]
            win_count = platform["wins"]

            if game_count > 0:
                win_percentage = (win_count / game_count) * 100
            else:
                win_percentage = 0

            platform_data[platform_name] = {"total": game_count, "win_rate": round(win_percentage, 1)}

        # Get analysis insights
        analysis_insights = []
        if analysis_count > 0:
            # Get most recent analyzed games with mistakes
            recent_analyses = (
                GameAnalysis.objects.select_related("game")  # type: ignore[attr-defined]
                .filter(game__user=user, analysis_data__has_key="mistakes")
                .order_by("-created_at")[:3]
            )

            for analysis in recent_analyses:
                game = analysis.game
                mistakes = analysis.analysis_data.get("mistakes", [])
                if mistakes:
                    analysis_insights.append(
                        {
                            "game_id": game.id,
                            "date": game.date_played,
                            "opponent": (
                                game.black
                                if game.white.lower() == profile.get_platform_username(game.platform).lower()
                                else game.white
                            ),
                            "mistake_count": len(mistakes),
                            "summary": analysis.analysis_data.get("summary", "No summary available"),
                        }
                    )

        # Construct the response data
        dashboard_data = {
            "user": {
                "username": user.username,
                "chess_com_username": profile.chess_com_username,
                "lichess_username": profile.lichess_username,
                "credits": profile.credits,
                "memberships": {  # Placeholder - would be populated from membership data
                    "is_premium": False,
                    "plan": "Free",
                },
            },
            "game_stats": {
                "total": total_games,
                "total_games": total_games,
                "analyzed": analysis_count,
                "analyzed_games": analysis_count,
                "wins": win_count,
                "win_count": win_count,
                "losses": loss_count,
                "loss_count": loss_count,
                "draws": draw_count,
                "draw_count": draw_count,
                "win_rate": round(win_rate, 1),
                "loss_rate": round(loss_rate, 1),
                "draw_rate": round(draw_rate, 1),
            },
            "recent_games": list(recent_games),
            "time_control_performance": time_control_performance,
            "platform_stats": platform_data,
            "analysis_insights": analysis_insights,
            "insights": analysis_insights,
            "openings": [],
            "performance": {
                "overall": {
                    "win_count": analyzed_win_count,
                    "loss_count": analyzed_loss_count,
                    "draw_count": analyzed_draw_count,
                },
                "time_controls": time_control_performance,
                "platforms": platform_data,
            },
            "ratings": {
                "bullet": profile.bullet_rating,
                "blitz": profile.blitz_rating,
                "rapid": profile.rapid_rating,
                "classical": profile.classical_rating,
            },
        }

        # Cache the dashboard data
        cache_manager.set(cache_key, dashboard_data, timeout=300)  # Cache for 5 minutes

        return Response(dashboard_data, status=status.HTTP_200_OK)

    except DASHBOARD_EXCEPTIONS as e:
        logger.error("Error in dashboard view: %s", e, exc_info=True)
        return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def refresh_dashboard(request):
    """
    Force refresh of dashboard data by clearing the cache.
    """
    try:
        user = request.user
        cache_key = generate_cache_key("dashboard_data", user.id)

        # Clear dashboard cache
        cache_manager.delete(cache_key)

        return Response(
            {"message": "Dashboard cache cleared, data will be refreshed on next request"}, status=status.HTTP_200_OK
        )
    except DASHBOARD_EXCEPTIONS as e:
        logger.error("Error refreshing dashboard data: %s", e)
        return Response(
            {"error": "Failed to refresh dashboard data: " + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_performance_trend(request):
    """
    Get user performance trend over time.
    """
    try:
        user = request.user
        period = request.query_params.get("period", "month")

        # Check cache first
        cache_key = generate_cache_key("performance_trend", user.id, period)
        cached_data = cache_manager.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        # Set time period based on request
        if period == "week":
            start_date = timezone.now() - timedelta(days=7)
        elif period == "year":
            start_date = timezone.now() - timedelta(days=365)
        else:
            start_date = timezone.now() - timedelta(days=30)

        analyzed_games = (
            Game.objects.filter(user=user, date_played__gte=start_date)  # type: ignore[attr-defined]
            .filter(Q(status="analyzed") | Q(analysis_status="analyzed"))
            .order_by("date_played")
        )

        time_series = []
        running_total = 0.0
        analyzed_count = 0

        for game in analyzed_games:
            accuracy = None
            analysis_payload = getattr(game, "analysis", None) or {}
            if isinstance(analysis_payload, dict):
                analysis_results = analysis_payload.get("analysis_results", analysis_payload)
                summary = analysis_results.get("summary", {}) if isinstance(analysis_results, dict) else {}
                if isinstance(summary, dict):
                    accuracy = summary.get("user_accuracy", summary.get("accuracy"))

            if accuracy is None:
                game_analysis = getattr(game, "gameanalysis", None)
                if game_analysis and getattr(game_analysis, "analysis_data", None):
                    summary = game_analysis.analysis_data.get("summary", {})
                    if isinstance(summary, dict):
                        accuracy = summary.get("user_accuracy", summary.get("accuracy"))

            if accuracy is None:
                continue

            analyzed_count += 1
            running_total += float(accuracy)
            average_accuracy = running_total / analyzed_count

            time_series.append(
                {
                    "game_id": game.id,
                    "date": game.date_played.isoformat(),
                    "accuracy": round(float(accuracy), 1),
                    "result": game.result,
                    "avg_accuracy": round(average_accuracy, 1),
                }
            )

        # Cache the results
        cache_manager.set(cache_key, time_series, timeout=600)  # Cache for 10 minutes

        return Response(time_series, status=status.HTTP_200_OK)

    except DASHBOARD_EXCEPTIONS as e:
        logger.error("Error getting performance trend: %s", e, exc_info=True)
        return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_mistake_analysis(request):
    """
    Get analysis of user's most common mistakes.
    """
    try:
        user = request.user

        # Check cache first
        cache_key = generate_cache_key("mistake_analysis", user.id)
        cached_data = cache_manager.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        # Get all analyzed games
        analyzed_games = Game.objects.filter(user=user).filter(Q(status="analyzed") | Q(analysis_status="analyzed"))  # type: ignore[attr-defined]

        if analyzed_games.count() == 0:
            return Response({"message": "No analyzed games found"}, status=status.HTTP_200_OK)

        # Count mistakes by type
        mistake_types = {}
        piece_mistakes = {}
        phase_mistakes = {"opening": 0, "middlegame": 0, "endgame": 0}
        total_mistakes = 0

        for game in analyzed_games:
            if not game.analysis or not game.analysis.get("analysis_results"):
                continue

            mistakes = game.analysis.get("analysis_results", {}).get("mistakes", [])
            for mistake in mistakes:
                # Count by mistake type
                mistake_type = mistake.get("type", "Unknown")
                mistake_types[mistake_type] = mistake_types.get(mistake_type, 0) + 1

                # Count by piece involved in the mistake
                piece = mistake.get("piece", "unknown")
                piece_mistakes[piece] = piece_mistakes.get(piece, 0) + 1

                # Count by game phase
                phase = mistake.get("phase", "Unknown")
                if phase in phase_mistakes:
                    phase_mistakes[phase] += 1

                total_mistakes += 1

        # Calculate percentages
        mistake_type_analysis = []
        for m_type, count in sorted(mistake_types.items(), key=lambda x: x[1], reverse=True):
            if total_mistakes > 0:
                percentage = (count / total_mistakes) * 100
            else:
                percentage = 0

            mistake_type_analysis.append({"type": m_type, "count": count, "percentage": round(percentage, 2)})

        phase_analysis = []
        for phase, count in phase_mistakes.items():
            if total_mistakes > 0:
                percentage = (count / total_mistakes) * 100
            else:
                percentage = 0

            phase_analysis.append({"phase": phase, "count": count, "percentage": round(percentage, 2)})

        piece_analysis = {}
        for piece, count in piece_mistakes.items():
            if total_mistakes > 0:
                percentage = (count / total_mistakes) * 100
            else:
                percentage = 0

            piece_analysis[piece] = round(percentage, 2)

        phase_analysis_map = {item["phase"]: item["percentage"] for item in phase_analysis}

        # Prepare result
        result = {
            "total_mistakes": total_mistakes,
            "analyzed_games": analyzed_games.count(),
            "avg_mistakes_per_game": (
                round(total_mistakes / analyzed_games.count(), 2) if analyzed_games.count() > 0 else 0
            ),
            "by_type": mistake_type_analysis,
            "by_game_phase": phase_analysis_map,
            "by_phase": phase_analysis,
            "by_piece": piece_analysis,
        }

        # Cache for 1 hour
        cache_manager.set(cache_key, result, timeout=60 * 60)

        return Response(result, status=status.HTTP_200_OK)

    except DASHBOARD_EXCEPTIONS as e:
        logger.error("Error getting mistake analysis: %s", e)
        return Response(
            {"error": "Failed to retrieve mistake analysis: " + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
