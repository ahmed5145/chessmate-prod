"""
Game-related views for the ChessMate application.
Including game retrieval, analysis, and batch processing endpoints.
"""

# Standard library imports
import logging
import json
from typing import Dict, Any, List, Optional, Union, cast

# Django imports
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.db import transaction

# Third-party imports
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from celery.result import AsyncResult  # type: ignore

# Local application imports
from .models import Game, GameAnalysis, Profile
from .chess_services import ChessComService, LichessService, save_game
from .game_analyzer import GameAnalyzer
from .ai_feedback import AIFeedbackGenerator
from .decorators import rate_limit
from .tasks import analyze_game_task, analyze_batch_games_task
from .task_manager import TaskManager
from .cache_manager import CacheManager
from .constants import MAX_BATCH_SIZE
from .error_handling import (
    api_error_handler, create_success_response,
    ResourceNotFoundError, InvalidOperationError, CreditLimitError,
    ChessServiceError
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize task manager
task_manager = TaskManager()

# Initialize cache manager
cache_manager = CacheManager()

# Initialize game services
chess_com_service = ChessComService()
lichess_service = LichessService()

@api_view(["GET"])
@permission_classes([IsAuthenticated])
@api_error_handler
def user_games_view(request):
    """
    Retrieve all saved games for the logged-in user.
    """
    user = request.user
    games = Game.objects.filter(user=user).values(
        "id",
        "platform",
        "white",
        "black",
        "opponent",
        "result",
        "date_played",
        "opening_name",
        "analysis"
    ).order_by("-date_played")
    
    return create_success_response(data=list(games))

@rate_limit(endpoint_type='FETCH')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@api_error_handler
def fetch_games(request):
    """
    Fetch games from Chess.com or Lichess for the user.
    """
    user = request.user
    
    try:
        profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        raise ResourceNotFoundError("User profile")
    
    platform = request.data.get('platform')
    username = request.data.get('username')
    game_type = request.data.get('game_type', 'rapid')
    num_games = int(request.data.get('num_games', 10))
    
    # Validate parameters
    if not platform or not username:
        from .error_handling import ValidationError
        errors = []
        if not platform:
            errors.append({"field": "platform", "message": "Platform is required"})
        if not username:
            errors.append({"field": "username", "message": "Username is required"})
        raise ValidationError(errors)
        
    # Check credits
    if profile.credits < 1:
        raise CreditLimitError(required=1, available=profile.credits)
        
    # Normalize parameters
    platform = platform.lower()
    username = username.strip()
    
    # Limit number of games
    if num_games > 50:
        num_games = 50  # Cap at 50 games max
        
    # Get games based on platform
    games_data = []
    try:
        if platform == 'chess.com':
            games_data = chess_com_service.get_user_games(username, game_type, num_games)
        elif platform == 'lichess':
            games_data = lichess_service.get_user_games(username, game_type, num_games)
        else:
            from .error_handling import ValidationError
            raise ValidationError([{
                "field": "platform", 
                "message": "Invalid platform. Supported platforms are 'chess.com' and 'lichess'"
            }])
    except Exception as e:
        # Convert service-specific exceptions to our standard format
        raise ChessServiceError(platform, str(e))
        
    # Save games to database
    saved_games = []
    for game_data in games_data:
        # Check if user is white or black player
        is_white = False
        is_black = False
        
        if platform == 'chess.com':
            is_white = game_data.get('white', {}).get('username', '').lower() == username.lower()
            is_black = game_data.get('black', {}).get('username', '').lower() == username.lower()
        elif platform == 'lichess':
            is_white = game_data.get('players', {}).get('white', {}).get('user', {}).get('name', '').lower() == username.lower()
            is_black = game_data.get('players', {}).get('black', {}).get('user', {}).get('name', '').lower() == username.lower()
            
        if is_white or is_black:
            # Save the game
            game = save_game(user, platform, game_data)
            if game:
                saved_games.append(game.id)
                
    # Deduct credits
    if saved_games:
        profile.credits -= 1
        profile.save()
                
    return create_success_response(
        data={
            "saved_games": saved_games,
            "remaining_credits": profile.credits
        },
        message=f"Successfully fetched {len(saved_games)} games"
    )

@rate_limit(endpoint_type='ANALYZE')
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@api_error_handler
def analyze_game(request, game_id):
    """
    Analyze a single game and return the task ID.
    """
    user = request.user
    
    try:
        profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        raise ResourceNotFoundError("User profile")
    
    # Check if game exists and belongs to user
    try:
        game = Game.objects.get(id=game_id, user=user)
    except Game.DoesNotExist:
        raise ResourceNotFoundError("Game", game_id)
        
    # Check if game is already being analyzed
    if game.analysis_status == 'analyzing':
        # If there's an existing task, return its ID
        existing_task = task_manager.get_task_for_game(game_id)
        if existing_task:
            return create_success_response(
                data={"task_id": existing_task, "status": "in_progress"},
                message="Analysis is already in progress"
            )
            
    # Check if analysis already exists and is complete
    if game.analysis_status == 'completed':
        try:
            analysis = GameAnalysis.objects.get(game=game)
            return create_success_response(
                data={"analysis_id": analysis.id, "status": "completed"},
                message="Analysis is already completed"
            )
        except GameAnalysis.DoesNotExist:
            # This shouldn't happen normally, but we reset status if it does
            game.analysis_status = 'not_started'
            game.save()
            
    # Check credits
    analysis_cost = 2  # Standard analysis cost
    
    # Get optional parameters with defaults
    depth = int(request.data.get('depth', settings.STOCKFISH_DEPTH))
    lines = int(request.data.get('lines', 3))
    
    # Adjust cost based on parameters
    if depth > 20:
        analysis_cost += 1
    if lines > 3:
        analysis_cost += 1
        
    if profile.credits < analysis_cost:
        raise CreditLimitError(required=analysis_cost, available=profile.credits)
        
    # Update game status to 'analyzing'
    game.analysis_status = 'analyzing'
    game.save()
    
    # Queue the analysis task
    task = analyze_game_task.delay(
        game_id=game.id,
        depth=depth,
        multi_pv=lines
    )
    
    # Register the task
    task_manager.register_task(str(task.id), 'game_analysis', game.id)
    
    # Deduct credits
    profile.credits -= analysis_cost
    profile.save()
    
    return create_success_response(
        data={
            "task_id": str(task.id),
            "status": "submitted",
            "credits_used": analysis_cost,
            "remaining_credits": profile.credits
        },
        message="Game analysis started successfully",
        status_code=status.HTTP_202_ACCEPTED
    )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
@api_error_handler
def get_game_analysis(request, game_id):
    """
    Get the analysis results for a game.
    """
    user = request.user
    
    # Check if game exists and belongs to user
    try:
        game = Game.objects.get(id=game_id, user=user)
    except Game.DoesNotExist:
        raise ResourceNotFoundError("Game", game_id)
        
    # Check if analysis exists
    try:
        analysis = GameAnalysis.objects.get(game=game)
    except GameAnalysis.DoesNotExist:
        if game.analysis_status == 'analyzing':
            task_id = task_manager.get_task_for_game(game_id)
            if task_id:
                return create_success_response(
                    data={"task_id": task_id, "status": "in_progress"},
                    message="Analysis is in progress"
                )
        raise ResourceNotFoundError("Analysis", f"for game {game_id}")
        
    # Return the analysis data
    analysis_data = {
        "id": analysis.id,
        "game_id": game.id,
        "created_at": analysis.created_at,
        "updated_at": analysis.updated_at,
        "data": analysis.data,
        "depth": analysis.depth,
        "lines": analysis.lines,
        "evaluation": analysis.evaluation,
        "best_moves": analysis.best_moves,
        "critical_positions": analysis.critical_positions,
        "inaccuracies": analysis.inaccuracies,
        "mistakes": analysis.mistakes,
        "blunders": analysis.blunders
    }
    
    return create_success_response(data=analysis_data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check_analysis_status(request, task_id):
    """
    Check the status of an analysis task.
    """
    try:
        user = request.user
        
        # Check if task exists and belongs to user
        task_info = task_manager.get_task_info(task_id)
        if not task_info or task_info.get('user_id') != user.id:
            return Response(
                {"error": "Task not found or does not belong to user"},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Get task result
        task_result = AsyncResult(task_id)
        
        # Process task status
        if task_result.state == 'PENDING':
            response_data = {
                "status": "PENDING",
                "message": "Task is waiting for execution",
                "progress": 0
            }
        elif task_result.state == 'STARTED' or task_result.state == 'PROGRESS':
            response_data = {
                "status": "IN_PROGRESS",
                "message": "Task is in progress",
                "progress": task_info.get('progress', 30)  # Default to 30% if no progress info
            }
        elif task_result.state == 'SUCCESS':
            result = task_result.result
            game_id = task_info.get('game_id')
            
            response_data = {
                "status": "COMPLETED",
                "message": "Task completed successfully",
                "progress": 100,
                "game_id": game_id,
                "result": result
            }
        elif task_result.state == 'FAILURE':
            response_data = {
                "status": "FAILED",
                "message": f"Task failed: {str(task_result.result)}",
                "progress": 0
            }
        else:
            response_data = {
                "status": task_result.state,
                "message": f"Unknown task state: {task_result.state}",
                "progress": 0
            }
            
        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error checking analysis status: {str(e)}")
        return Response(
            {"error": f"Failed to check analysis status: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@rate_limit(endpoint_type='ANALYZE')
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def batch_analyze(request):
    """
    Analyze multiple games in batch.
    """
    try:
        user = request.user
        profile = Profile.objects.get(user=user)
        
        # Get game IDs from request
        game_ids = request.data.get('game_ids', [])
        
        # Validate game IDs
        if not game_ids or not isinstance(game_ids, list):
            return Response(
                {"error": "Valid game IDs are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Limit batch size
        if len(game_ids) > MAX_BATCH_SIZE:
            return Response(
                {"error": f"Batch size is limited to {MAX_BATCH_SIZE} games at a time"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check if games exist and belong to user
        valid_games = []
        for game_id in game_ids:
            try:
                game = Game.objects.get(id=game_id, user=user)
                valid_games.append(game_id)
            except Game.DoesNotExist:
                logger.warning(f"Game {game_id} not found or does not belong to user {user.id}")
                # Skip invalid games
                continue
                
        if not valid_games:
            return Response(
                {"error": "No valid games found"},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Check credits
        required_credits = len(valid_games)
        if profile.credits < required_credits:
            return Response(
                {
                    "error": f"Insufficient credits. Analyzing {len(valid_games)} games requires {required_credits} credits.",
                    "required_credits": required_credits,
                    "available_credits": profile.credits
                },
                status=status.HTTP_402_PAYMENT_REQUIRED
            )
            
        # Update game status for all games
        Game.objects.filter(id__in=valid_games).update(analysis_status='analyzing')
        
        # Start batch analysis task
        task = analyze_batch_games_task.delay(valid_games)
        
        # Register task with task manager
        task_manager.register_batch_task(task.id, valid_games, user.id)
        
        # Deduct credits
        profile.credits -= required_credits
        profile.save()
        
        return Response(
            {
                "task_id": task.id,
                "status": "started",
                "message": f"Batch analysis of {len(valid_games)} games started",
                "games_count": len(valid_games),
                "remaining_credits": profile.credits
            },
            status=status.HTTP_202_ACCEPTED
        )
    except Profile.DoesNotExist:
        return Response(
            {"error": "User profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error starting batch analysis: {str(e)}")
        return Response(
            {"error": f"Failed to start batch analysis: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check_batch_analysis_status(request, task_id):
    """
    Check the status of a batch analysis task.
    """
    try:
        user = request.user
        
        # Check if task exists and belongs to user
        task_info = task_manager.get_task_info(task_id)
        if not task_info or task_info.get('user_id') != user.id:
            return Response(
                {"error": "Task not found or does not belong to user"},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Get task result
        task_result = AsyncResult(task_id)
        
        # Process task status
        if task_result.state == 'PENDING':
            response_data = {
                "status": "PENDING",
                "message": "Batch analysis is waiting for execution",
                "progress": 0
            }
        elif task_result.state == 'STARTED' or task_result.state == 'PROGRESS':
            response_data = {
                "status": "IN_PROGRESS",
                "message": "Batch analysis is in progress",
                "progress": task_info.get('progress', 30)  # Default to 30% if no progress info
            }
        elif task_result.state == 'SUCCESS':
            result = task_result.result
            game_ids = task_info.get('game_ids', [])
            
            # Collect analysis results for each game
            game_results = {}
            for game_id in game_ids:
                game_result = result.get(str(game_id))
                if game_result:
                    game_results[game_id] = game_result
                    
            response_data = {
                "status": "COMPLETED",
                "message": "Batch analysis completed successfully",
                "progress": 100,
                "game_ids": game_ids,
                "results": game_results
            }
        elif task_result.state == 'FAILURE':
            response_data = {
                "status": "FAILED",
                "message": f"Batch analysis failed: {str(task_result.result)}",
                "progress": 0
            }
        else:
            response_data = {
                "status": task_result.state,
                "message": f"Unknown task state: {task_result.state}",
                "progress": 0
            }
            
        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error checking batch analysis status: {str(e)}")
        return Response(
            {"error": f"Failed to check batch analysis status: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_ai_feedback(request, game_id):
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
            return Response(
                {"error": "Game not found or does not belong to user"},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Check if game has been analyzed
        if game.analysis_status != 'analyzed' or not game.analysis:
            return Response(
                {"error": "Game must be analyzed before generating AI feedback"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check credits
        if profile.credits < 2:  # AI feedback costs 2 credits
            return Response(
                {"error": "Insufficient credits. Generating AI feedback requires 2 credits."},
                status=status.HTTP_402_PAYMENT_REQUIRED
            )
            
        # Initialize AI feedback generator
        feedback_generator = AIFeedbackGenerator(api_key=settings.OPENAI_API_KEY)
        
        # Extract analysis data from game
        analysis_results = game.analysis.get('analysis_results', {})
        
        # Generate feedback
        feedback = feedback_generator.generate_feedback(analysis_results, game)
        
        # Update game analysis with feedback
        with transaction.atomic():
            if 'feedback' not in game.analysis:
                game.analysis['feedback'] = {}
                
            game.analysis['feedback'] = {
                'source': 'openai',
                'timestamp': timezone.now().isoformat(),
                'feedback': feedback
            }
            game.save()
            
            # Deduct credits
            profile.credits -= 2
            profile.save()
            
        return Response(
            {
                "message": "AI feedback generated successfully",
                "feedback": feedback,
                "remaining_credits": profile.credits
            },
            status=status.HTTP_200_OK
        )
    except Profile.DoesNotExist:
        return Response(
            {"error": "User profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error generating AI feedback: {str(e)}")
        return Response(
            {"error": f"Failed to generate AI feedback: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 