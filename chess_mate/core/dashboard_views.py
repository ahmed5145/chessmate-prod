"""
Dashboard-related views for the ChessMate application.
This module handles user dashboard functionality including statistics and insights.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.db.models import (
    Avg,
    Case,
    Count,
    F,
    FloatField,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    When,
)
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone
from rest_framework import status

# Third-party imports
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .cache import cache_delete, cache_get, cache_set, cacheable, generate_cache_key
from .cache_invalidation import invalidates_cache
from .error_handling import api_error_handler

# Local application imports
from .models import Game, GameAnalysis, Profile

# Configure logging
logger = logging.getLogger(__name__)


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
        cached_data = cache_get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        # Get user's profile with a single query
        try:
            profile = Profile.objects.select_related("user").get(user=user)
        except Profile.DoesNotExist:
            return Response({"error": "User profile not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get recent games with optimized query - limit select fields
        recent_games = (
            Game.objects.filter(user=user)
            .order_by("-date_played")
            .values("id", "white", "black", "result", "date_played", "platform", "opening_name", "status")[:5]
        )

        # Use database aggregation instead of Python counting
        game_stats = Game.objects.filter(user=user).aggregate(
            total_games=Count("id"),
            analyzed_games=Count(Case(When(status="analyzed", then=1), output_field=IntegerField())),
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
            tc_stats = Game.objects.filter(user=user, time_control_category=time_control).aggregate(
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
            Game.objects.filter(user=user)
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
                GameAnalysis.objects.select_related("game")
                .filter(game__user=user, result__has_key="mistakes")
                .order_by("-created_at")[:3]
            )

            for analysis in recent_analyses:
                game = analysis.game
                mistakes = analysis.result.get("mistakes", [])
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
                            "summary": analysis.result.get("summary", "No summary available"),
                        }
                    )

        # Construct the response data
        dashboard_data = {
            "user": {
                "username": user.username,
                "credits": profile.credits,
                "memberships": {  # Placeholder - would be populated from membership data
                    "is_premium": False,
                    "plan": "Free",
                },
            },
            "game_stats": {
                "total": total_games,
                "analyzed": analysis_count,
                "wins": win_count,
                "losses": loss_count,
                "draws": draw_count,
                "win_rate": round(win_rate, 1),
                "loss_rate": round(loss_rate, 1),
                "draw_rate": round(draw_rate, 1),
            },
            "recent_games": list(recent_games),
            "time_control_performance": time_control_performance,
            "platform_stats": platform_data,
            "analysis_insights": analysis_insights,
            "ratings": {
                "bullet": profile.bullet_rating,
                "blitz": profile.blitz_rating,
                "rapid": profile.rapid_rating,
                "classical": profile.classical_rating,
            },
        }

        # Cache the dashboard data
        cache_set(cache_key, dashboard_data, timeout=300)  # Cache for 5 minutes

        return Response(dashboard_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in dashboard view: {str(e)}", exc_info=True)
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
        cache_delete(cache_key)

        return Response(
            {"message": "Dashboard cache cleared, data will be refreshed on next request"}, status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Error refreshing dashboard data: {str(e)}")
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
        cached_data = cache_get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        # Set time period based on request
        if period == "week":
            start_date = timezone.now() - timedelta(days=7)
            # Use TruncDate for grouping by day
            truncate_date = TruncDate("date_played")
            interval = "day"
        elif period == "month":
            start_date = timezone.now() - timedelta(days=30)
            truncate_date = TruncDate("date_played")
            interval = "day"
        elif period == "year":
            start_date = timezone.now() - timedelta(days=365)
            truncate_date = TruncMonth("date_played")
            interval = "month"
        else:
            start_date = timezone.now() - timedelta(days=30)
            truncate_date = TruncDate("date_played")
            interval = "day"

        # Use database-level aggregation and grouping
        performance_data = (
            Game.objects.filter(user=user, date_played__gte=start_date)
            .annotate(date=truncate_date)
            .values("date")
            .annotate(
                total=Count("id"),
                wins=Count(Case(When(result="win", then=1), output_field=IntegerField())),
                losses=Count(Case(When(result="loss", then=1), output_field=IntegerField())),
                draws=Count(Case(When(result="draw", then=1), output_field=IntegerField())),
            )
            .order_by("date")
        )

        # Format the results
        time_series = []
        for day_data in performance_data:
            date = day_data["date"]
            total = day_data["total"]
            wins = day_data["wins"]
            losses = day_data["losses"]
            draws = day_data["draws"]

            # Calculate percentages
            win_percentage = (wins / total * 100) if total > 0 else 0
            loss_percentage = (losses / total * 100) if total > 0 else 0
            draw_percentage = (draws / total * 100) if total > 0 else 0

            time_series.append(
                {
                    "date": date.strftime("%Y-%m-%d") if interval == "day" else date.strftime("%Y-%m"),
                    "total": total,
                    "wins": wins,
                    "losses": losses,
                    "draws": draws,
                    "win_percentage": round(win_percentage, 1),
                    "loss_percentage": round(loss_percentage, 1),
                    "draw_percentage": round(draw_percentage, 1),
                }
            )

        result = {"period": period, "interval": interval, "data": time_series}

        # Cache the results
        cache_set(cache_key, result, timeout=600)  # Cache for 10 minutes

        return Response(result, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error getting performance trend: {str(e)}", exc_info=True)
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
        cached_data = cache_get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        # Get all analyzed games
        analyzed_games = Game.objects.filter(user=user, status="analyzed")

        if analyzed_games.count() == 0:
            return Response({"error": "No analyzed games found"}, status=status.HTTP_404_NOT_FOUND)

        # Count mistakes by type
        mistake_types = {}
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

        # Prepare result
        result = {
            "total_mistakes": total_mistakes,
            "analyzed_games": analyzed_games.count(),
            "avg_mistakes_per_game": (
                round(total_mistakes / analyzed_games.count(), 2) if analyzed_games.count() > 0 else 0
            ),
            "by_type": mistake_type_analysis,
            "by_phase": phase_analysis,
        }

        # Cache for 1 hour
        cache_set(cache_key, result, timeout=60 * 60)

        return Response(result, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error getting mistake analysis: {str(e)}")
        return Response(
            {"error": "Failed to retrieve mistake analysis: " + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
