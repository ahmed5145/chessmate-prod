"""
AI Feedback-related views for the ChessMate application.
Includes endpoints for generating and retrieving AI-powered game analysis feedback.
"""

import json

# Standard library imports
import logging
from typing import Any, Dict, List, Optional

# Django imports
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status

# Third-party imports
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .ai_feedback import AIFeedbackGenerator

# Local application imports
from .models import Game, GameAnalysis, Profile

# Configure logging
logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_game_feedback(request, game_id):
    """
    Generate AI feedback for a specific game.
    """
    try:
        user = request.user
        profile = Profile.objects.get(user=user)

        # Check if game exists and belongs to user
        try:
            game = Game.objects.get(id=game_id, user=user)
        except Game.DoesNotExist:
            return Response({"error": "Game not found or does not belong to user"}, status=status.HTTP_404_NOT_FOUND)

        # Check if game has been analyzed
        if game.analysis_status != "analyzed" or not game.analysis:
            return Response(
                {"error": "Game must be analyzed before generating AI feedback"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check if feedback already exists and if user wants to regenerate
        force_regenerate = request.data.get("force_regenerate", False)
        if not force_regenerate and game.analysis.get("feedback"):
            return Response(
                {"message": "Feedback already exists for this game", "feedback": game.analysis.get("feedback")},
                status=status.HTTP_200_OK,
            )

        # Check credits
        feedback_cost = 2  # AI feedback costs 2 credits
        if profile.credits < feedback_cost:
            return Response(
                {
                    "error": f"Insufficient credits. Generating AI feedback requires {feedback_cost} credits.",
                    "required_credits": feedback_cost,
                    "available_credits": profile.credits,
                },
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        # Initialize AI feedback generator
        feedback_generator = AIFeedbackGenerator(api_key=settings.OPENAI_API_KEY)

        # Get specific focus areas if provided
        focus_areas = request.data.get("focus_areas", [])

        # Extract analysis data from game
        analysis_results = game.analysis.get("analysis_results", {})

        # Generate feedback
        feedback = feedback_generator.generate_feedback(analysis_results, game, focus_areas)

        # Update game analysis with feedback
        with transaction.atomic():
            if "feedback" not in game.analysis:
                game.analysis["feedback"] = {}

            game.analysis["feedback"] = {
                "source": "openai",
                "timestamp": timezone.now().isoformat(),
                "generated_for": focus_areas if focus_areas else "general",
                "content": feedback,
            }
            game.save()

            # Deduct credits
            profile.credits -= feedback_cost
            profile.save()

        return Response(
            {
                "message": "AI feedback generated successfully",
                "feedback": game.analysis["feedback"],
                "remaining_credits": profile.credits,
            },
            status=status.HTTP_200_OK,
        )
    except Profile.DoesNotExist:
        return Response({"error": "User profile not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error generating AI feedback: {str(e)}")
        return Response(
            {"error": f"Failed to generate AI feedback: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_game_feedback(request, game_id):
    """
    Retrieve AI feedback for a specific game.
    """
    try:
        user = request.user

        # Check if game exists and belongs to user
        try:
            game = Game.objects.get(id=game_id, user=user)
        except Game.DoesNotExist:
            return Response({"error": "Game not found or does not belong to user"}, status=status.HTTP_404_NOT_FOUND)

        # Check if feedback exists
        if not game.analysis or not game.analysis.get("feedback"):
            return Response({"error": "No feedback available for this game"}, status=status.HTTP_404_NOT_FOUND)

        return Response({"game_id": game_id, "feedback": game.analysis.get("feedback")}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error retrieving AI feedback: {str(e)}")
        return Response(
            {"error": f"Failed to retrieve AI feedback: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_comparative_feedback(request):
    """
    Generate AI feedback comparing multiple games.
    """
    try:
        user = request.user
        profile = Profile.objects.get(user=user)

        # Get game IDs from request
        game_ids = request.data.get("game_ids", [])

        # Validate game IDs
        if not game_ids or not isinstance(game_ids, list) or len(game_ids) < 2:
            return Response(
                {"error": "At least two valid game IDs are required for comparison"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check if games exist and belong to user
        games = []
        for game_id in game_ids:
            try:
                game = Game.objects.get(id=game_id, user=user)

                # Check if game has been analyzed
                if game.analysis_status != "analyzed" or not game.analysis:
                    return Response(
                        {"error": f"Game {game_id} must be analyzed before generating comparative feedback"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                games.append(game)
            except Game.DoesNotExist:
                return Response(
                    {"error": f"Game {game_id} not found or does not belong to user"}, status=status.HTTP_404_NOT_FOUND
                )

        # Check credits
        feedback_cost = 3  # Comparative feedback costs 3 credits
        if profile.credits < feedback_cost:
            return Response(
                {
                    "error": f"Insufficient credits. Generating comparative feedback requires {feedback_cost} credits.",
                    "required_credits": feedback_cost,
                    "available_credits": profile.credits,
                },
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        # Initialize AI feedback generator
        feedback_generator = AIFeedbackGenerator(api_key=settings.OPENAI_API_KEY)

        # Get comparison focus if provided
        comparison_focus = request.data.get("comparison_focus", "overall")

        # Prepare games data for comparison
        games_data = []
        for game in games:
            games_data.append(
                {
                    "id": game.id,
                    "white": game.white,
                    "black": game.black,
                    "result": game.result,
                    "date_played": game.date_played,
                    "opening_name": game.opening_name,
                    "analysis_results": game.analysis.get("analysis_results", {}),
                }
            )

        # Generate comparative feedback
        comparative_feedback = feedback_generator.generate_comparative_feedback(games_data, comparison_focus)

        # Create a unique key for this comparison
        comparison_key = f"comparative_{'_'.join(str(g.id) for g in games)}"

        # Store feedback in the first game
        with transaction.atomic():
            first_game = games[0]

            if "comparative_feedback" not in first_game.analysis:
                first_game.analysis["comparative_feedback"] = {}

            first_game.analysis["comparative_feedback"][comparison_key] = {
                "source": "openai",
                "timestamp": timezone.now().isoformat(),
                "comparison_focus": comparison_focus,
                "compared_games": [g.id for g in games],
                "content": comparative_feedback,
            }
            first_game.save()

            # Deduct credits
            profile.credits -= feedback_cost
            profile.save()

        return Response(
            {
                "message": "Comparative AI feedback generated successfully",
                "feedback": first_game.analysis["comparative_feedback"][comparison_key],
                "remaining_credits": profile.credits,
            },
            status=status.HTTP_200_OK,
        )
    except Profile.DoesNotExist:
        return Response({"error": "User profile not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error generating comparative AI feedback: {str(e)}")
        return Response(
            {"error": f"Failed to generate comparative AI feedback: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_improvement_suggestions(request):
    """
    Get AI-generated improvement suggestions based on all analyzed games.
    """
    try:
        user = request.user
        profile = Profile.objects.get(user=user)

        # Check for minimum number of analyzed games
        analyzed_games = Game.objects.filter(user=user, analysis_status="analyzed")

        if analyzed_games.count() < 3:
            return Response(
                {"error": "At least 3 analyzed games are required for improvement suggestions"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check credits
        suggestion_cost = 5  # Improvement suggestions cost 5 credits
        if profile.credits < suggestion_cost:
            return Response(
                {
                    "error": f"Insufficient credits. Getting improvement suggestions requires {suggestion_cost} credits.",
                    "required_credits": suggestion_cost,
                    "available_credits": profile.credits,
                },
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        # Initialize AI feedback generator
        feedback_generator = AIFeedbackGenerator(api_key=settings.OPENAI_API_KEY)

        # Collect data from recent games (last 10 or fewer)
        recent_games = analyzed_games.order_by("-date_played")[:10]
        games_data = []

        for game in recent_games:
            if not game.analysis or not game.analysis.get("analysis_results"):
                continue

            games_data.append(
                {
                    "id": game.id,
                    "white": game.white,
                    "black": game.black,
                    "result": game.result,
                    "date_played": game.date_played,
                    "opening_name": game.opening_name,
                    "analysis_results": game.analysis.get("analysis_results", {}),
                }
            )

        # Generate improvement suggestions
        improvement_suggestions = feedback_generator.generate_improvement_suggestions(games_data)

        # Store suggestions in user profile
        with transaction.atomic():
            if not profile.improvement_suggestions:
                profile.improvement_suggestions = {}

            suggestion_id = str(timezone.now().timestamp())
            profile.improvement_suggestions[suggestion_id] = {
                "source": "openai",
                "timestamp": timezone.now().isoformat(),
                "based_on_games": [g["id"] for g in games_data],
                "content": improvement_suggestions,
            }
            profile.save()

            # Deduct credits
            profile.credits -= suggestion_cost
            profile.save()

        return Response(
            {
                "message": "Improvement suggestions generated successfully",
                "suggestions": profile.improvement_suggestions[suggestion_id],
                "remaining_credits": profile.credits,
            },
            status=status.HTTP_200_OK,
        )
    except Profile.DoesNotExist:
        return Response({"error": "User profile not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error generating improvement suggestions: {str(e)}")
        return Response(
            {"error": f"Failed to generate improvement suggestions: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
