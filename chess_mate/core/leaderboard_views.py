"""
Leaderboard-related views for the ChessMate application.
"""

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .cache import CACHE_BACKEND_REDIS, cacheable
from .error_handling import api_error_handler, create_success_response
from .models import Game, GameAnalysis, Profile, User

# Configure logging
logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([AllowAny])
@api_error_handler
@cacheable(prefix="leaderboard", timeout=60 * 5, cache_backend=CACHE_BACKEND_REDIS)
def leaderboard(request):
    """
    Get the leaderboard data.
    Cached for 5 minutes to improve performance and reduce database load.
    """
    # Get leaderboard type from query params
    board_type = request.query_params.get("type", "analysis")
    time_period = request.query_params.get("period", "week")
    limit = int(request.query_params.get("limit", 10))

    # Cap limit at 50 to prevent excessive data retrieval
    if limit > 50:
        limit = 50

    # Determine time filter based on period
    if time_period == "day":
        time_filter = timezone.now() - timedelta(days=1)
    elif time_period == "week":
        time_filter = timezone.now() - timedelta(days=7)
    elif time_period == "month":
        time_filter = timezone.now() - timedelta(days=30)
    elif time_period == "year":
        time_filter = timezone.now() - timedelta(days=365)
    else:  # 'all'
        time_filter = None

    # Get leaderboard data based on type
    if board_type == "analysis":
        leaders = _get_analysis_leaderboard(time_filter, limit)
    elif board_type == "games":
        leaders = _get_games_leaderboard(time_filter, limit)
    elif board_type == "accuracy":
        leaders = _get_accuracy_leaderboard(time_filter, limit)
    elif board_type == "improvement":
        leaders = _get_improvement_leaderboard(time_filter, limit)
    else:
        # Default to analysis leaderboard
        leaders = _get_analysis_leaderboard(time_filter, limit)

    return create_success_response(data={"type": board_type, "period": time_period, "leaders": leaders})


def _get_analysis_leaderboard(time_filter: Optional[timezone.datetime], limit: int) -> List[Dict[str, Any]]:
    """
    Get leaderboard based on number of analyses performed.
    """
    query = (
        GameAnalysis.objects.values("game__user__username", "game__user__id")
        .annotate(count=Count("id"), avg_depth=Avg("depth"))
        .order_by("-count")
    )

    # Apply time filter if specified
    if time_filter:
        query = query.filter(created_at__gte=time_filter)

    # Limit results
    query = query[:limit]

    # Format results
    results = []
    for idx, item in enumerate(query):
        results.append(
            {
                "rank": idx + 1,
                "username": item["game__user__username"],
                "user_id": item["game__user__id"],
                "analysis_count": item["count"],
                "avg_depth": round(item["avg_depth"], 1) if item["avg_depth"] else None,
            }
        )

    return results


def _get_games_leaderboard(time_filter: Optional[timezone.datetime], limit: int) -> List[Dict[str, Any]]:
    """
    Get leaderboard based on number of games imported.
    """
    query = Game.objects.values("user__username", "user__id").annotate(count=Count("id")).order_by("-count")

    # Apply time filter if specified
    if time_filter:
        query = query.filter(created_at__gte=time_filter)

    # Limit results
    query = query[:limit]

    # Format results
    results = []
    for idx, item in enumerate(query):
        results.append(
            {
                "rank": idx + 1,
                "username": item["user__username"],
                "user_id": item["user__id"],
                "games_count": item["count"],
            }
        )

    return results


def _get_accuracy_leaderboard(time_filter: Optional[timezone.datetime], limit: int) -> List[Dict[str, Any]]:
    """
    Get leaderboard based on average accuracy in analyzed games.
    """
    # This query requires JSON field extraction - approach depends on database
    query = GameAnalysis.objects.filter(result__has_key="accuracy")

    # Apply time filter if specified
    if time_filter:
        query = query.filter(created_at__gte=time_filter)

    # We'll do a two-step process - first get all analyses with accuracy
    analyses = list(query.values("game__user__username", "game__user__id", "result"))

    # Process them to calculate average accuracy
    user_accuracies = {}
    user_counts = {}

    for analysis in analyses:
        user_id = analysis["game__user__id"]
        username = analysis["game__user__username"]
        accuracy = analysis["result"].get("accuracy", 0)

        if accuracy:
            if user_id in user_accuracies:
                user_accuracies[user_id] += accuracy
                user_counts[user_id] += 1
            else:
                user_accuracies[user_id] = accuracy
                user_counts[user_id] = 1
                user_accuracies[f"username_{user_id}"] = username

    # Calculate averages and create sorted list
    avg_accuracies = []
    for user_id, total_accuracy in user_accuracies.items():
        if isinstance(user_id, int):  # Skip the username entries
            avg_accuracy = total_accuracy / user_counts[user_id]
            avg_accuracies.append(
                {
                    "user_id": user_id,
                    "username": user_accuracies[f"username_{user_id}"],
                    "avg_accuracy": avg_accuracy,
                    "game_count": user_counts[user_id],
                }
            )

    # Sort by average accuracy
    avg_accuracies.sort(key=lambda x: x["avg_accuracy"], reverse=True)

    # Format results with rank and limit
    results = []
    for idx, item in enumerate(avg_accuracies[:limit]):
        results.append(
            {
                "rank": idx + 1,
                "username": item["username"],
                "user_id": item["user_id"],
                "avg_accuracy": round(item["avg_accuracy"], 1),
                "games_analyzed": item["game_count"],
            }
        )

    return results


def _get_improvement_leaderboard(time_filter: Optional[timezone.datetime], limit: int) -> List[Dict[str, Any]]:
    """
    Get leaderboard based on improvement over time.
    This is more complex and requires comparing older and newer analyses.
    """
    # For improvement, we need a longer time range to measure change
    improvement_cutoff = timezone.now() - timedelta(days=90)

    # Get users with enough analyses for meaningful comparison
    # We need at least 3 analyses in the last period to ensure reliable data
    if time_filter:
        recent_count = 3
        active_users = (
            GameAnalysis.objects.filter(created_at__gte=time_filter)
            .values("game__user")
            .annotate(count=Count("id"))
            .filter(count__gte=recent_count)
            .values_list("game__user", flat=True)
        )

        # Nothing to calculate if we don't have active users
        if not active_users:
            return []

        # Get older analyses for comparison
        recent_analyses = (
            GameAnalysis.objects.filter(
                game__user__in=active_users, created_at__gte=time_filter, result__has_key="accuracy"
            )
            .values("game__user__username", "game__user__id", "created_at", "result")
            .order_by("created_at")
        )

        older_analyses = (
            GameAnalysis.objects.filter(
                game__user__in=active_users,
                created_at__lt=time_filter,
                created_at__gte=improvement_cutoff,
                result__has_key="accuracy",
            )
            .values("game__user__id", "created_at", "result")
            .order_by("created_at")
        )
    else:
        # If no time filter, we use the last 90 days as recent and anything older within the year as baseline
        additional_cutoff = timezone.now() - timedelta(days=365)

        recent_analyses = (
            GameAnalysis.objects.filter(created_at__gte=improvement_cutoff, result__has_key="accuracy")
            .values("game__user__username", "game__user__id", "created_at", "result")
            .order_by("created_at")
        )

        older_analyses = (
            GameAnalysis.objects.filter(
                created_at__lt=improvement_cutoff, created_at__gte=additional_cutoff, result__has_key="accuracy"
            )
            .values("game__user__id", "created_at", "result")
            .order_by("created_at")
        )

    # Process data
    user_improvements = {}

    # Calculate baseline accuracies from older analyses
    baseline_accuracies = {}
    for analysis in older_analyses:
        user_id = analysis["game__user__id"]
        accuracy = analysis["result"].get("accuracy", 0)

        if not accuracy:
            continue

        if user_id in baseline_accuracies:
            baseline_accuracies[user_id]["total"] += accuracy
            baseline_accuracies[user_id]["count"] += 1
        else:
            baseline_accuracies[user_id] = {"total": accuracy, "count": 1}

    # Calculate recent accuracies and compare with baseline
    for analysis in recent_analyses:
        user_id = analysis["game__user__id"]
        username = analysis["game__user__username"]
        accuracy = analysis["result"].get("accuracy", 0)

        if not accuracy:
            continue

        # Initialize user data if needed
        if user_id not in user_improvements:
            user_improvements[user_id] = {
                "username": username,
                "recent_total": 0,
                "recent_count": 0,
                "baseline_avg": None,
            }

            # Set baseline if available
            if user_id in baseline_accuracies and baseline_accuracies[user_id]["count"] > 0:
                baseline_avg = baseline_accuracies[user_id]["total"] / baseline_accuracies[user_id]["count"]
                user_improvements[user_id]["baseline_avg"] = baseline_avg

        # Add recent accuracy data
        user_improvements[user_id]["recent_total"] += accuracy
        user_improvements[user_id]["recent_count"] += 1

    # Calculate improvement percentages
    improvement_list = []
    for user_id, data in user_improvements.items():
        # Only include users with baseline and recent data
        if data["baseline_avg"] and data["recent_count"] > 0:
            recent_avg = data["recent_total"] / data["recent_count"]
            improvement = recent_avg - data["baseline_avg"]

            improvement_list.append(
                {
                    "user_id": user_id,
                    "username": data["username"],
                    "improvement": improvement,
                    "baseline_accuracy": data["baseline_avg"],
                    "recent_accuracy": recent_avg,
                }
            )

    # Sort by improvement
    improvement_list.sort(key=lambda x: x["improvement"], reverse=True)

    # Format results
    results = []
    for idx, item in enumerate(improvement_list[:limit]):
        results.append(
            {
                "rank": idx + 1,
                "username": item["username"],
                "user_id": item["user_id"],
                "improvement": round(item["improvement"], 1),
                "baseline_accuracy": round(item["baseline_accuracy"], 1),
                "recent_accuracy": round(item["recent_accuracy"], 1),
            }
        )

    return results
