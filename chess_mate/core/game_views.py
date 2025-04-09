"""
Game-related views for the ChessMate application.
Including game retrieval, analysis, and batch processing endpoints.
"""

import json

# Standard library imports
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, cast

from celery.result import AsyncResult  # type: ignore

# Django imports
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Prefetch, Q, F, Avg
from django.http import JsonResponse, HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from rest_framework import status, viewsets
from django.utils.decorators import method_decorator

# Third-party imports
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .ai_feedback import AIFeedbackGenerator
from .cache import (
    CACHE_BACKEND_REDIS,
    cache_delete,
    cache_get,
    cache_set,
    cache_stampede_prevention,
    cacheable,
    generate_cache_key,
)
from .cache_invalidation import (
    CacheInvalidator,
    invalidate_cache,
    invalidates_cache,
    with_cache_tags,
)
from .chess_services import ChessComService, LichessService, save_game
from .chess_utils import extract_metadata_from_pgn, validate_pgn
from .constants import MAX_BATCH_SIZE
from .decorators import (
    auth_csrf_exempt,
    rate_limit,
    track_request_time,
    validate_request,
    api_login_required,
)
from .error_handling import (
    ChessServiceError,
    CreditLimitError,
    ExternalServiceError,
    InvalidOperationError,
    ResourceNotFoundError,
    ValidationError,
    api_error_handler,
    create_error_response,
    create_success_response,
    handle_api_error,
)
from .game_analyzer import GameAnalyzer

# Local application imports
from .models import Game, GameAnalysis, Player, Profile, User
from .serializers import GameAnalysisSerializer, GameSerializer
from .task_manager import TaskManager
from .tasks import analyze_game_task, batch_analyze_games_task

# Configure logging
logger = logging.getLogger(__name__)

# Initialize task manager
task_manager = TaskManager()

# Initialize game services
chess_com_service = ChessComService()
lichess_service = LichessService()

# Cache keys
USER_GAMES_CACHE_KEY = "user_games_{user_id}"
GAME_ANALYSIS_CACHE_KEY = "game_analysis_{game_id}"
GAME_DETAILS_CACHE_KEY = "game_details_{game_id}"


class GameViewSet(viewsets.ModelViewSet):
    """ViewSet for game operations."""

    serializer_class = GameSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get games for the current user with optimized query."""
        # Use select_related to fetch related user in a single query
        # This avoids n+1 query issue when serializing
        queryset = Game.objects.select_related("user").filter(user=self.request.user)

        # Add ordering to optimize database access pattern
        queryset = queryset.order_by("-date_played")

        # ⚠️ Prefetch_related for gameanalysis temporarily disabled due to database schema mismatch
        # The metrics column referenced in the database query doesn't exist in the database
        # Future fix: Run a migration to add this column or modify the serializer

        return queryset

    @action(detail=True, methods=["post"])
    @invalidates_cache("game_analysis")
    def analyze(self, request, pk=None) -> Response:
        """Start game analysis."""
        try:
            # Using select_related to fetch user in the same query
            game = self.get_object()
            depth = int(request.data.get("depth", 20))
            use_ai = bool(request.data.get("use_ai", True))

            # Create analysis task
            task = analyze_game_task.delay(game.id, depth, use_ai)

            return Response({"status": "success", "message": "Analysis started", "task_id": task.id})

        except Exception as e:
            return create_error_response(
                error_type="external_service_error", message=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"])
    @invalidates_cache("game_analysis", "user_games")
    def batch_analyze(self, request) -> Response:
        """Start batch analysis of multiple games."""
        try:
            game_ids = request.data.get("game_ids", [])
            if not game_ids:
                # Using proper ValidationError format
                raise ValidationError([{"field": "game_ids", "message": "No game IDs provided"}])

            # Limit batch size to prevent overload
            if len(game_ids) > MAX_BATCH_SIZE:
                game_ids = game_ids[:MAX_BATCH_SIZE]

            depth = int(request.data.get("depth", 20))
            use_ai = bool(request.data.get("use_ai", True))

            # Verify all games belong to the user
            user_game_count = Game.objects.filter(id__in=game_ids, user=request.user).count()

            if user_game_count != len(game_ids):
                # Using proper ValidationError format
                raise ValidationError(
                    [{"field": "game_ids", "message": "Some game IDs are invalid or don't belong to you"}]
                )

            # Create batch analysis task
            task = batch_analyze_games_task.delay(game_ids, depth, use_ai)

            return Response({"status": "success", "message": "Batch analysis started", "task_id": task.id})

        except ValidationError as e:
            return create_error_response(
                error_type="validation_failed", message=str(e), status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return create_error_response(
                error_type="external_service_error", message=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["get"])
    @method_decorator(csrf_exempt)
    def analysis_status(self, request, pk=None) -> Response:
        """Get analysis status for a game."""
        try:
            game = self.get_object()
            task_info = task_manager.get_task_status(game.id)

            if not task_info:
                return Response({"status": "not_found", "message": "No analysis task found"})

            return Response(task_info)

        except Exception as e:
            return create_error_response(
                error_type="external_service_error", message=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["get"])
    def search(self, request) -> Response:
        """Search games with filters."""
        try:
            query = request.query_params.get("q", "")
            game_status = request.query_params.get("status", "")
            date_from = request.query_params.get("date_from", "")
            date_to = request.query_params.get("date_to", "")
            platform = request.query_params.get("platform", "")
            result = request.query_params.get("result", "")
            limit = int(request.query_params.get("limit", 25))
            offset = int(request.query_params.get("offset", 0))

            # Cap limit to prevent performance issues
            if limit > 100:
                limit = 100

            # Build efficient query
            queryset = self.get_queryset()

            # Apply filters
            if query:
                queryset = queryset.filter(
                    Q(white__icontains=query) | Q(black__icontains=query) | Q(opening_name__icontains=query)
                )

            if game_status:
                queryset = queryset.filter(analysis_status=game_status)

            if platform:
                queryset = queryset.filter(platform=platform)

            if result:
                queryset = queryset.filter(result=result)

            if date_from:
                queryset = queryset.filter(date_played__gte=date_from)

            if date_to:
                queryset = queryset.filter(date_played__lte=date_to)

            # Count total without fetching all records
            total_count = queryset.count()

            # Apply pagination
            queryset = queryset[offset : offset + limit]

            serializer = self.get_serializer(queryset, many=True)
            return Response({"results": serializer.data, "count": total_count, "limit": limit, "offset": offset})

        except Exception as e:
            return create_error_response(
                error_type="validation_failed", message=str(e), status_code=status.HTTP_400_BAD_REQUEST
            )


@require_GET
@ensure_csrf_cookie
@login_required
@track_request_time
@validate_request(required_get_params=["user_id"])
@rate_limit(endpoint_type="GAMES")
def get_user_games(request):
    """Get games for a specific user."""
    try:
        user_id = request.GET.get("user_id")
        if not user_id:
            raise ValidationError([{"field": "user_id", "message": "User ID is required"}])

        # Check if requester has permission
        if int(user_id) != request.user.id and not request.user.is_staff:
            return JsonResponse(
                {"status": "error", "message": "You do not have permission to view these games"}, status=403
            )

        # Check cache
        cache_key = f"user_games:{user_id}"
        cached_games = cache_get(cache_key)
        if cached_games:
            logger.info(f"Retrieved user games from cache for user {user_id}")
            return JsonResponse({"status": "success", "games": cached_games})

        # Get games from database
        games = Game.objects.filter(players__user_id=user_id).order_by("-date_played")

        # Format response
        game_list = []
        for game in games:
            game_data = {
                "id": game.id,
                "source": game.source,
                "external_id": game.external_id,
                "date_played": game.date_played.isoformat() if game.date_played else None,
                "result": game.result,
                "players": [
                    {
                        "id": player.id,
                        "user_id": player.user_id,
                        "username": player.username,
                        "rating": player.rating,
                        "color": player.color,
                    }
                    for player in game.players.all()
                ],
                "has_analysis": hasattr(game, "analysis"),
            }
            game_list.append(game_data)

        # Cache results
        cache_set(cache_key, game_list, timeout=600)  # 10 minutes

        return JsonResponse({"status": "success", "games": game_list})

    except Exception as e:
        return handle_api_error(e, "Error retrieving user games")


@require_POST
@auth_csrf_exempt
@login_required
@track_request_time
@validate_request(required_fields=["pgn"])
@rate_limit(endpoint_type="GAMES")
def import_game(request):
    """Import a chess game from PGN notation."""
    try:
        data = json.loads(request.body)
        pgn = data.get("pgn")

        # Validate PGN
        if not validate_pgn(pgn):
            raise ValidationError([{"field": "pgn", "message": "Invalid PGN format"}])

        # Extract metadata
        metadata = extract_metadata_from_pgn(pgn)

        # Check if game already exists
        existing_game = Game.objects.filter(
            external_id=metadata.get("external_id"), source=metadata.get("source")
        ).first()

        if existing_game:
            return JsonResponse({"status": "success", "message": "Game already exists", "game_id": existing_game.id})

        # Create new game
        with transaction.atomic():
            # Create game
            game = Game.objects.create(
                source=metadata.get("source", "manual"),
                external_id=metadata.get("external_id", ""),
                date_played=metadata.get("date_played", datetime.now()),
                pgn=pgn,
                result=metadata.get("result", "*"),
                user=request.user,  # Add user reference
            )

            # Create players
            for player_data in metadata.get("players", []):
                Player.objects.create(
                    game=game,
                    user_id=player_data.get("user_id"),
                    username=player_data.get("username", ""),
                    rating=player_data.get("rating", 0),
                    color=player_data.get("color", "white"),
                )

            # Associate game with user
            if hasattr(request.user, "profile") and request.user.profile:
                request.user.profile.games.add(game)

        # Invalidate cache
        invalidate_cache(f"user_{request.user.id}_games")

        return JsonResponse({"status": "success", "message": "Game imported successfully", "game_id": game.id})

    except Exception as e:
        return handle_api_error(e, "Error importing game")


@require_GET
@ensure_csrf_cookie
@login_required
@track_request_time
@validate_request(required_get_params=["game_id"])
def get_game(request):
    """Get detailed information about a specific game."""
    try:
        game_id = request.GET.get("game_id")
        if not game_id:
            raise ValidationError([{"field": "game_id", "message": "Game ID is required"}])

        # Check cache
        cache_key = f"game:{game_id}"
        cached_game = cache_get(cache_key)
        if cached_game:
            logger.info(f"Retrieved game from cache: {game_id}")
            return JsonResponse({"status": "success", "game": cached_game})

        # Get game from database
        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            raise ResourceNotFoundError(f"Game not found: {game_id}")

        # Check permission
        if not request.user.is_staff and game.user.id != request.user.id:
                return JsonResponse(
                    {"status": "error", "message": "You do not have permission to view this game"}, status=403
                )

        # Format response
        game_data = {
            "id": game.id,
            "source": game.source,
            "external_id": game.external_id,
            "date_played": game.date_played.isoformat() if game.date_played else None,
            "pgn": game.pgn,
            "result": game.result,
            "players": [
                {
                    "id": player.id,
                    "user_id": player.user_id,
                    "username": player.username,
                    "rating": player.rating,
                    "color": player.color,
                }
                for player in game.players.all()
            ],
            "has_analysis": hasattr(game, "analysis"),
        }

        # Cache results
        cache_set(cache_key, game_data, timeout=1800)  # 30 minutes

        return JsonResponse({"status": "success", "game": game_data})

    except Exception as e:
        return handle_api_error(e, "Error retrieving game")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@auth_csrf_exempt
@track_request_time
@validate_request(required_fields=["game_id"])
@rate_limit(endpoint_type="ANALYSIS")
def analyze_game(request, game_id=None):
    """Analyze a chess game."""
    try:
        # Use request.data from DRF instead of manually parsing JSON
        data = request.data
        # Get game_id from URL param first, then request body as fallback
        game_id = game_id or data.get("game_id")

        # Validate inputs
        if not game_id:
            return Response(
                {"status": "error", "message": "Game ID is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get game from database
        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            return Response(
                {"status": "error", "message": f"Game not found: {game_id}"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        if not request.user.is_staff:
            # Check if the user is the owner of the game
            if game.user_id != request.user.id:
                return Response(
                    {"status": "error", "message": "You do not have permission to analyze this game"}, 
                    status=status.HTTP_403_FORBIDDEN
                )

        # Use hardcoded default values 
        DEFAULT_ANALYSIS_DEPTH = 20
        DEFAULT_USE_AI = True
        
        # Get analysis parameters
        depth = data.get("depth", DEFAULT_ANALYSIS_DEPTH)
        use_ai = data.get("use_ai", DEFAULT_USE_AI)

        # Use our safer analyze_game_safely function
        from .batch_analyze_games import analyze_game_safely
        
        # Call analyze_game_safely with the correct parameters
        result = analyze_game_safely(game_id, request.user.id, depth, use_ai)
        
        # Check if analysis was successful
        if result.get("status") != "success":
            return Response(
                {"status": "error", "message": result.get("message", "Unknown error")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Invalidate cache - fix the invalidate_cache call
        try:
            invalidate_cache(f"game_{game_id}")
        except Exception as cache_error:
            logger.warning(f"Cache invalidation error: {str(cache_error)}")

        # Return successful response
        return Response(
            {
                "status": "success", 
                "message": "Analysis started", 
                "task_id": result.get("task_id"),
                "game_id": game.id
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        # Log the full error for debugging
        logger.error(f"Error analyzing game: {str(e)}", exc_info=True)
        return Response(
            {"status": "error", "message": f"Error analyzing game: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@auth_csrf_exempt
@track_request_time
@validate_request(required_fields=["platform", "username"])
@rate_limit(endpoint_type="GAMES")
def import_external_games(request):
    """Import games from external sources like chess.com or lichess."""
    try:
        data = request.data
        # Use request.user.id as fallback for user_id
        user_id = data.get("user_id") or request.user.id
        platform = data.get("platform") or data.get("source")  # Support both field names
        username = data.get("username")
        game_type = data.get("game_type", "rapid")
        num_games = data.get("num_games", 10)

        logger.info(f"Importing games: user_id={user_id}, platform={platform}, username={username}")

        # Validate platform
        if not platform:
            raise ValidationError([{"field": "platform", "message": "Platform/source is required"}])

        if platform not in ["chess.com", "lichess"]:
            raise ValidationError([{"field": "platform", "message": "Invalid platform. Must be 'chess.com' or 'lichess'"}])

        if not username:
            # Try to get username from profile
            try:
                profile = Profile.objects.get(user_id=user_id)
                if platform == "chess.com":
                    username = profile.chess_com_username
                else:
                    username = profile.lichess_username
            except Profile.DoesNotExist:
                raise ValidationError([{"field": "username", "message": f"Username for {platform} is required"}])

        if not username:
            raise ValidationError([{"field": "username", "message": f"Username for {platform} is required"}])

        # Check if user has enough credits
        try:
            profile = Profile.objects.get(user_id=user_id)
            if profile.credits < num_games and not request.user.is_staff:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Insufficient credits",
                        "credits_required": num_games,
                        "credits_available": profile.credits,
                    },
                    status=402,
                )
        except Profile.DoesNotExist:
            logger.error(f"Profile not found for user_id={user_id}")

        # Import games
        if platform == "chess.com":
            service = chess_com_service
        else:
            service = lichess_service

        # Get games
        games = service.get_games(username, limit=num_games, game_type=game_type)

        # Save games
        imported_count = 0
        for game_data in games:
            try:
                # Get the user object
                user = User.objects.get(id=user_id)
                # Call save_game with correct parameters
                save_game(game_data, username, user)
                imported_count += 1
            except Exception as e:
                logger.error(f"Error saving game: {str(e)}")

        # Deduct credits if not staff
        if not request.user.is_staff:
            profile.credits -= imported_count
            profile.save()

        # Invalidate cache
        invalidate_cache(f"user_{user_id}_games")

        return JsonResponse(
            {
                "status": "success",
                "message": f"Imported {imported_count} games from {platform}",
                "imported_count": imported_count,
                "games": games[:5] if isinstance(games, list) else []  # Return preview of first 5 games
            }
        )

    except ValidationError as ve:
        return JsonResponse({"status": "error", "errors": ve.args[0]}, status=400)
    except Exception as e:
        logger.error(f"Error importing games: {str(e)}", exc_info=True)
        return JsonResponse(
            {"status": "error", "message": f"Error importing games: {str(e)}"},
            status=500
        )


@csrf_exempt
@require_GET
@ensure_csrf_cookie
@api_login_required
@track_request_time
def get_task_status(request, game_id=None):
    """Get the status of a background task."""
    try:
        # If game_id is provided in the URL path, use that
        if game_id:
            # Get task status using the game_id directly
            task_info = task_manager.get_task_status(game_id)
            
            if not task_info:
                # No task found for this game
                return JsonResponse({
                    "status": "not_found",
                    "message": "No analysis task found for this game",
                    "progress": 0
                })
            
            # If task_info already contains a 'task' key, return it directly
            if 'task' in task_info:
                return JsonResponse(task_info)
            
            # Otherwise wrap it in a response with a 'task' key for frontend compatibility
            return JsonResponse({
                "status": "success", 
                "task": {
                    "id": task_info.get("id", ""),
                    "status": task_info.get("status", "UNKNOWN"),
                    "progress": task_info.get("progress", 0),
                    "message": task_info.get("message", "Analyzing game..."),
                    "error": task_info.get("error", None)
                }
            })
        else:
            # Otherwise check for task_id in query params
            task_id = request.GET.get("task_id")
            if not task_id:
                return JsonResponse({
                    "status": "error", 
                    "message": "Either game_id in URL path or task_id query parameter is required"
                }, status=400)

            # Get task status
            task_info = task_manager.get_task_status_by_id(task_id)
            
            # Wrap the task info in a response with a 'task' key for frontend compatibility
            return JsonResponse({
                "status": "success", 
                "task": {
                    "id": task_id,
                    "status": task_info.get("status", "UNKNOWN"),
                    "progress": task_info.get("progress", 0),
                    "message": task_info.get("message", "Analyzing game..."),
                    "error": task_info.get("error", None)
                }
            })

    except Exception as e:
        logger.error(f"Error retrieving task status: {str(e)}", exc_info=True)
        return JsonResponse({
            "status": "error",
            "message": f"Error retrieving task status: {str(e)}",
            "task": {
                "status": "ERROR",
                "progress": 0,
                "message": f"Error: {str(e)}"
            }
        }, status=500)


@require_POST
@auth_csrf_exempt
@login_required
@track_request_time
@validate_request(required_fields=["game_ids"])
@rate_limit(endpoint_type="ANALYSIS")
def batch_analyze_games(request):
    """Start batch analysis of multiple games."""
    try:
        data = json.loads(request.body)
        game_ids = data.get("game_ids", [])

        # Validate inputs
        if not game_ids or not isinstance(game_ids, list):
            raise ValidationError([{"field": "game_ids", "message": "List of game IDs is required"}])

        if len(game_ids) > 10:
            raise ValidationError([{"field": "game_ids", "message": "Maximum 10 games can be analyzed in a batch"}])

        # NOTE: Credit check removed - batch analysis is now free

        # Verify each game exists and belongs to the user
        games = []
        for game_id in game_ids:
            try:
                game = Game.objects.get(id=game_id)
                games.append(game)
            except Game.DoesNotExist:
                raise ResourceNotFoundError(f"Game not found: {game_id}")

            # Check permission
            if not request.user.is_staff and game.user.id != request.user.id:
                    return JsonResponse(
                        {"status": "error", "message": f"You do not have permission to analyze game {game_id}"},
                        status=403,
                    )

        # Start batch analysis
        game_analyzer = GameAnalyzer()
        task = batch_analyze_games_task.delay(
            game_ids=game_ids, user_id=request.user.id, use_ai=data.get("use_ai", True)
        )

        # No longer deducting credits for batch analysis

        # Invalidate cache for each game
        for game_id in game_ids:
            invalidate_cache(f"game_{game_id}")

        return JsonResponse(
            {"status": "success", "message": "Batch analysis started", "task_id": task.id, "games_count": len(game_ids)}
        )

    except Exception as e:
        return handle_api_error(e, "Error starting batch game analysis")


@csrf_exempt
@api_login_required
@track_request_time
@validate_request(required_fields=["game_ids"])
def batch_get_analysis_status(request):
    """Get analysis status for multiple games at once."""
    try:
        # Get the game IDs from the request data
        data = json.loads(request.body) if isinstance(request.body, bytes) else request.body
        game_ids = data.get("game_ids", [])
        
        if not game_ids:
            return JsonResponse({"status": "error", "message": "No game IDs provided"}, status=400)
            
        # Limit the number of games to check at once
        if len(game_ids) > 20:
            return JsonResponse(
                {"status": "error", "message": "Too many games requested. Maximum is 20."}, 
                status=400
            )
            
        # Verify the user has access to these games
        if not request.user.is_staff:
            authorized_count = Game.objects.filter(
                id__in=game_ids, 
                user_id=request.user.id
            ).count()
            
            if authorized_count != len(game_ids):
                return JsonResponse(
                    {"status": "error", "message": "You don't have permission to access some of these games"}, 
                    status=403
                )
        
        # Get status for each game
        statuses = {}
        for game_id in game_ids:
            try:
                # First check if there's a task for this game
                task_info = task_manager.get_task_status(game_id)
                
                if task_info:
                    # Task exists, return its status
                    statuses[str(game_id)] = task_info
                else:
                    # Simply return pending for all games without trying to check the database
                    # This avoids issues when the database schema is inconsistent
                    statuses[str(game_id)] = {
                        "status": "PENDING",
                        "progress": 0,
                        "message": "Analysis not started yet or database inconsistency",
                    }
            except Exception as e:
                logger.warning(f"Error checking status for game {game_id}: {str(e)}")
                # Return a safe default in case of errors
                statuses[str(game_id)] = {
                    "status": "PENDING",
                    "message": f"Status check error: {str(e)[:50]}",
                }
        
        # Return the statuses
        return JsonResponse({
            "status": "success", 
            "statuses": statuses,
            "auth_info": {
                "user_id": request.user.id,
                "username": request.user.username,
                "is_authenticated": request.user.is_authenticated,
                "is_staff": request.user.is_staff
            }
        })
        
    except ValidationError as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error checking batch analysis status: {str(e)}")
        return JsonResponse({"status": "error", "message": f"Error: {str(e)}"}, status=500)


@require_GET
@ensure_csrf_cookie
@login_required
@track_request_time
@validate_request(required_get_params=["source", "username"])
@rate_limit(endpoint_type="GAMES")
def search_external_player(request):
    """Search for player on external platforms."""
    try:
        source = request.GET.get("source")
        username = request.GET.get("username")

        # Validate inputs
        if not source:
            raise ValidationError([{"field": "source", "message": "Source is required"}])

        if not username:
            raise ValidationError([{"field": "username", "message": "Username is required"}])

        if source not in ["chess.com", "lichess"]:
            raise ValidationError([{"field": "source", "message": "Invalid source. Must be 'chess.com' or 'lichess'"}])

        # Search player
        if source == "chess.com":
            service = chess_com_service
        else:
            service = lichess_service

        # Get player details
        player_info = service.get_player_info(username)

        return JsonResponse({"status": "success", "player": player_info})

    except Exception as e:
        return handle_api_error(e, f"Error searching for player on {request.GET.get('source', 'external platform')}")


@csrf_exempt
@api_login_required
@track_request_time
def get_game_analysis(request, game_id):
    """
    Get the analysis for a specific game.
    """
    try:
        # Get the game
        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": f"Game not found with ID: {game_id}"},
                status=404,
            )

        # Check permission
        if not request.user.is_staff and game.user.id != request.user.id:
            return JsonResponse(
                {"status": "error", "message": "You do not have permission to view this game"},
                status=403,
            )

        # Try to get the analysis
        try:
            analysis = GameAnalysis.objects.get(game_id=game_id)
            
            # Return the analysis data
            return JsonResponse(analysis.analysis_data)
            
        except GameAnalysis.DoesNotExist:
            return JsonResponse({}, status=200)
        except Exception as e:
            logger.error(f"Error retrieving game analysis: {str(e)}", exc_info=True)
            # Return an empty object rather than an error for better UX
            return JsonResponse({}, status=200)

    except Exception as e:
        return handle_api_error(e, "Error retrieving game analysis")
