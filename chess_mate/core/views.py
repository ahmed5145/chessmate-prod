"""
This module contains the views for the ChessMate application, including endpoints for fetching, 
analyzing, and providing feedback on chess games, as well as user authentication and registration.
"""

# Standard library imports
import os
import json
import logging
import httpx
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, cast

# Django imports
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.mail import send_mail
from django.db import connection, transaction, OperationalError
from django_ratelimit.decorators import ratelimit   # type: ignore
from django.db import models
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.tokens import default_token_generator
from django.utils.html import strip_tags
from django.views.decorators.http import require_GET
from django.core.validators import validate_email
from django.contrib.auth.password_validation import validate_password
from django.db.utils import IntegrityError
from django.middleware.csrf import get_token

# Third-party imports
import requests
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
import chess.engine
from openai import OpenAI
from celery.result import AsyncResult  # type: ignore
from django.core.cache import cache

# Local application imports
from .models import Game, GameAnalysis, Profile, Transaction
from .chess_services import ChessComService, LichessService, save_game
from .game_analyzer import GameAnalyzer
from .validators import validate_password_complexity
from .ai_feedback import AIFeedbackGenerator
from .decorators import rate_limit
from .payment import PaymentProcessor, CREDIT_PACKAGES
from .utils import generate_feedback_without_ai
from .tasks import analyze_game_task, analyze_batch_games_task, update_user_stats_task, update_ratings_for_linked_account
from .task_manager import TaskManager
from .cache_manager import CacheManager
from .constants import MAX_BATCH_SIZE

STOCKFISH_PATH = os.getenv("STOCKFISH_PATH")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize stripe
try:
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY
except ImportError:
    stripe = None  # type: ignore
    logger.warning("Stripe package not installed. Payment features will be disabled.")

def get_openai_client() -> Optional[OpenAI]:
    """Get OpenAI client with proper error handling."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OpenAI API key not set. AI features will be disabled.")
        return None
    return OpenAI(api_key=api_key)

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Initialize feedback generator with proper error handling
try:
    ai_feedback_generator = AIFeedbackGenerator(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    logger.error(f"Error initializing AI feedback generator: {str(e)}")
    ai_feedback_generator = None  # type: ignore

# Initialize task manager
task_manager = TaskManager()

@api_view(['GET'])
def debug_request(request):
    """
    Debug endpoint to check request details and server configuration.
    """
    debug_info = {
        'request_method': request.method,
        'headers': dict(request.headers),
        'query_params': dict(request.GET),
        'user': str(request.user),
        'is_authenticated': request.user.is_authenticated,
        'server_time': timezone.now().isoformat(),
        'database_connection': 'OK' if connection.ensure_connection() else 'ERROR',
        'redis_connection': 'OK' if settings.CACHES['default']['BACKEND'].endswith('RedisCache') else 'Not using Redis',
    }
    return Response(debug_info, status=status.HTTP_200_OK)

def index(request):
    """
    Render the index page.
    """
    return render(request, "index.html")

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_saved_games(request):
    """
    Retrieve saved games for the logged-in user.
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
    
    return Response(list(games), status=status.HTTP_200_OK)

class EmailVerificationToken:
    @staticmethod
    def generate_token():
        return str(uuid.uuid4())

    @staticmethod
    def is_valid(token, max_age_days=7):
        try:
            # Add token validation logic here if needed
            return True
        except Exception:
            return False

@rate_limit(endpoint_type='AUTH')
@api_view(['POST'])
@csrf_exempt  # Exempt registration from CSRF
def register_view(request):
    """Handle user registration with email verification."""
    response = Response()  # Create response object early to add CORS headers
    response["Access-Control-Allow-Origin"] = request.headers.get('origin', '*')
    response["Access-Control-Allow-Credentials"] = 'true'
    
    try:
        data = request.data
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")

        # Validate required fields
        if not all([username, email, password]):
            return Response(
                {"error": "All fields are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate email format
        try:
            validate_email(email)
        except ValidationError as e:
            return Response(
                {"error": str(e), "field": "email"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "Email already registered.", "field": "email"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            return Response(
                {"error": "Username already taken.", "field": "username"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate password
        try:
            validate_password(password)
        except ValidationError as e:
            return Response(
                {"error": str(e), "field": "password"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # Create inactive user first
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    is_active=False
                )
                logger.debug(f"Created user: {username}")
                    
                # Get or create profile with verification token and starter credits
                verification_token = EmailVerificationToken.generate_token()
                profile, created = Profile.objects.get_or_create(
                        user=user,
                    defaults={
                        'email_verification_token': verification_token,
                        'email_verification_sent_at': timezone.now(),
                        'credits': 10
                    }
                )
                
                if not created:
                    profile.email_verification_token = verification_token
                    profile.email_verification_sent_at = timezone.now()
                    profile.save()
                
                logger.debug(f"Created profile for user: {username} with {profile.credits} credits")
                
                # Send verification email
                try:
                    send_verification_email(request, user, verification_token)
                    logger.debug(f"Sent verification email to: {email}")
                except Exception as e:
                    logger.error(f"Error sending verification email: {str(e)}", exc_info=True)
                    # Don't fail registration if email fails, but log it
                    pass
            
            # Create response with success message
            response = Response(
                {
                    "message": "Registration successful! Please check your email to verify your account.",
                    "email": email
                },
                status=status.HTTP_201_CREATED
            )
            
            # Set CSRF cookie
            token = get_token(request)
            response.set_cookie(
                'csrftoken',
                token,
                max_age=None,  # Session length
                path='/',
                secure=False,  # Set to True in production with HTTPS
                samesite='None',  # Required for cross-origin requests
                httponly=False  # Allow JavaScript access
            )
            
            return response

        except IntegrityError as e:
            logger.error(f"Database integrity error: {str(e)}", exc_info=True)
            return Response(
                {"error": "Username or email already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Database error: {str(e)}", exc_info=True)
            return Response(
                {"error": "An unexpected error occurred during registration."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    except Exception as e:
        logger.error(f"Unexpected registration error: {str(e)}", exc_info=True)
        return Response(
            {"error": "An unexpected error occurred during registration."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def send_verification_email(request, user, token):
    """
    Send verification email to user with verification link.
    """
    try:
        # Generate verification URL using the verify.html page
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        verification_url = request.build_absolute_uri(f'/api/verify-email/{uidb64}/{token}/')
        
        # Get or create user profile
        profile = Profile.objects.get_or_create(user=user)[0]
        profile.email_verification_token = token
        profile.email_verification_sent_at = timezone.now()
        profile.save()

        # Send email with verification link
        subject = 'Verify Your ChessMate Account'
        html_message = render_to_string('email/verify_email.html', {
            'user': user,
            'verification_url': verification_url,
        })
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Verification email sent to {user.email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send verification email: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Error in send_verification_email: {str(e)}")
        return False

@api_view(["GET"])
def verify_email(request, uidb64, token):
    """
    Verify email and activate user account.
    """
    try:
        # First decode the uidb64 to get the user id
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        profile = Profile.objects.get(user=user)
        
        logger.debug(f"Verifying email for user {user.username} with token {token}")
        logger.debug(f"Profile token: {profile.email_verification_token}")
        
        if profile.email_verification_token == token:
            # Check if token is expired (24 hours)
            if profile.email_verification_sent_at and \
               (timezone.now() - profile.email_verification_sent_at) > timedelta(hours=24):
                logger.error("Token expired")
                return render(request, 'email/verification_error.html', {
                    'message': 'Verification link has expired. Please request a new one.'
                })
            
            user.is_active = True
            user.save()
            
            profile.email_verified = True
            profile.email_verified_at = timezone.now()
            profile.save()
            
            logger.info(f"Email verified successfully for user {user.username}")
            return render(request, 'email/verification_success.html', {
                'message': 'Email verified successfully. You can now log in.'
            })
        
        logger.error(f"Invalid token for user {user.username}")
        return render(request, 'email/verification_error.html', {
            'message': 'Invalid verification link.'
        })
        
    except (TypeError, ValueError, OverflowError, User.DoesNotExist, Profile.DoesNotExist) as e:
        logger.error(f"Error verifying email: {str(e)}")
        return render(request, 'email/verification_error.html', {
            'message': 'Invalid verification link.'
        })

@rate_limit(endpoint_type='AUTH')
@api_view(['POST'])
@csrf_exempt  # Exempt login from CSRF
def login_view(request):
    """
    Handle user login with email verification check.
    """
    response = Response()  # Create response object early to add CORS headers
    response["Access-Control-Allow-Origin"] = request.headers.get('origin', '*')
    response["Access-Control-Allow-Credentials"] = 'true'
    
    try:
        data = request.data
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return Response(
                {"error": "Both email and password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.is_active:
            return Response(
                {"error": "Please verify your email before logging in."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=user.username, password=password)
        if user is None:
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_400_BAD_REQUEST
            )

        tokens = get_tokens_for_user(user)
        
        # Create response with tokens
        response = Response({
            "message": "Login successful!",
            "tokens": tokens,
            "user": {
                "username": user.username,
                "email": user.email
            }
        }, status=status.HTTP_200_OK)
        
        # Set CSRF cookie
        token = get_token(request)
        response.set_cookie(
            'csrftoken',
            token,
            max_age=None,  # Session length
            path='/',
            secure=False,  # Set to True in production with HTTPS
            samesite='None',  # Required for cross-origin requests
            httponly=False  # Allow JavaScript access
        )
        
        return response
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return Response(
            {"error": "An error occurred during login."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def fetch_games(request):
    """Fetch games from chess platforms."""
    try:
        username = request.data.get('username')
        platform = request.data.get('platform', 'chess.com')
        game_type = request.data.get('game_type', 'rapid')  # Default to rapid instead of all
        num_games = int(request.data.get('num_games', 10))

        # Validate game type
        valid_game_types = ['blitz', 'rapid', 'bullet', 'daily', 'classical']
        if game_type not in valid_game_types:
            return Response(
                {"error": f"Invalid game type. Must be one of: {', '.join(valid_game_types)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not username:
            return Response(
                {"error": "Username is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                profile = Profile.objects.select_for_update().get(user=request.user)
                required_credits = num_games
                
                if profile.credits < required_credits:
                    return Response(
                        {"error": f"Insufficient credits. Need {required_credits} credits."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Initialize service based on platform
                if platform == 'chess.com':
                    service = ChessComService()
                elif platform == 'lichess':
                    service = LichessService()
                else:
                    return Response(
                        {"error": "Invalid platform"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Fetch and save games
                result = service.fetch_games(
                    username=username,
                    user=request.user,
                    game_type=game_type,
                    limit=num_games
                )

                saved_count = result.get('saved', 0)
                skipped_count = result.get('skipped', 0)

                # Deduct credits based on saved games
                if saved_count > 0:
                    profile.credits -= saved_count
                    profile.save()
                    
                    Transaction.objects.create(
                        user=request.user,
                        transaction_type='usage',
                        credits=saved_count,
                        status='completed'
                    )

                return Response({
                    'success': True,
                    'games_saved': saved_count,
                    'games_skipped': skipped_count,
                    'credits_remaining': profile.credits
                })

        except Profile.DoesNotExist:
            logger.error(f"Profile not found for user {request.user.username}")
            return Response(
                {"error": "User profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        logger.error(f"Error fetching games: {str(e)}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_games_view(request):
    """
    Fetch games specific to the logged-in user.
    """
    user = request.user
    platform = request.query_params.get('platform', 'all')
    
    # Base query filtering by user
    games = Game.objects.filter(user=user)
    
    # Apply platform filter if specified
    if platform != 'all':
        games = games.filter(platform=platform)
    
    # Get all required fields and convert datetime to string
    games_data = []
    for game in games.order_by("-date_played"):
        # Determine opponent based on user's color
        opponent = game.opponent
        if not opponent or opponent == "Unknown":
            opponent = game.black if game.white.lower() == user.username.lower() else game.white

        game_data = {
            "id": game.id,
            "platform": game.platform,
            "white": game.white,
            "black": game.black,
            "opponent": opponent,
            "result": game.result,
            "date_played": game.date_played.isoformat() if game.date_played else None,
            "opening_name": game.opening_name or "Unknown Opening",
            "analysis": game.analysis,
            "status": game.status,  # Send the actual status from the database
            "white_elo": game.white_elo,
            "black_elo": game.black_elo,
            "time_control": game.time_control
        }
        games_data.append(game_data)
    
    return Response(games_data, status=status.HTTP_200_OK)

@rate_limit(endpoint_type='ANALYSIS')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_game(request, game_id):
    """Analyze a specific game."""
    try:
        task_manager = TaskManager()
        
        with transaction.atomic():
            # Get game and verify status
            game = Game.objects.select_for_update().get(id=game_id)
            
            # Check if game is already analyzed
            if game.status == 'analyzed':
                return Response({
                    'status': 'completed',
                    'message': 'Game is already analyzed',
                    'task_id': None
                })

            # Get or create task
            existing_task = task_manager.get_existing_task(game_id)
            if existing_task:
                return Response({
                    'status': existing_task.get('status', 'unknown'),
                    'message': 'Task already exists',
                    'task_id': existing_task.get('task_id')
                })

            # Create new task
            depth = int(request.data.get('depth', 20))
            use_ai = bool(request.data.get('use_ai', True))
            
            # Update game status to analyzing
            game.status = 'analyzing'
            game.save(update_fields=['status'])
            
            # Create task
            task = analyze_game_task.delay(game_id, depth, use_ai)
            task_manager.create_task(game_id, task.id)
            
            return Response({
                'status': 'started',
                'message': 'Analysis task created',
                'task_id': task.id
            })

    except Game.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Game not found'
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"Error creating analysis task: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Failed to create analysis task: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_analysis_status(request, task_id):
    """Check the status of a game analysis task."""
    try:
        task_manager = TaskManager()
        task = AsyncResult(task_id)
        
        if task.ready():
            if task.successful():
                result = task.get()
                if isinstance(result, dict):
                    # Handle the case where we have analysis results
                    if 'analysis_results' in result:
                        return Response({
                            "status": "completed",
                            "analysis": result.get('analysis_results'),
                            "feedback": result.get('feedback'),
                            "game_id": result.get('game_id')
                        })
                    
                    # Normalize status for consistency
                    if result.get('status') in ['SUCCESS', 'COMPLETED', 'completed']:
                        result['status'] = 'completed'
                    elif not result.get('status'):
                        result['status'] = 'completed'
                    
                    # Ensure game_id is included
                    if 'game_id' not in result and 'status' in result:
                        task_data = task_manager.get_task_by_id(task_id)
                        if task_data and 'game_id' in task_data:
                            result['game_id'] = task_data['game_id']
                    return Response(result)
                
                # Handle non-dict results
                return Response({
                    "status": "completed",
                    "result": result
                })
            else:
                error = str(task.result)
                return Response({
                    "status": "failed",
                    "message": error
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Task is still running
            return Response({
                "status": "in_progress",
                "progress": task.info.get('progress', 0) if task.info else 0,
                "message": "Analysis in progress"
            })
    except Exception as e:
        logger.error(f"Error checking analysis status: {str(e)}", exc_info=True)
        return Response({
            "status": "error",
            "message": f"Error checking analysis status: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_game_analysis(request, game_id):
    """
    Get the analysis for a specific game by its ID.
    """
    user = request.user
    try:
        game = Game.objects.get(id=game_id, user=user)
        
        # First try to get analysis from GameAnalysis model
        try:
            analysis = GameAnalysis.objects.get(game=game)
            return Response({"analysis": analysis.analysis_data}, status=status.HTTP_200_OK)
        except GameAnalysis.DoesNotExist:
            # If not found in GameAnalysis, check Game model
            if game.analysis:
                return Response({"analysis": game.analysis}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Analysis not found for this game."}, status=status.HTTP_404_NOT_FOUND)
                
    except Game.DoesNotExist:
        return Response({"error": "Game not found or access denied."}, status=status.HTTP_404_NOT_FOUND)

@rate_limit(endpoint_type='ANALYSIS')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def batch_analyze(request):
    """Start batch analysis of games."""
    try:
        user = request.user
        num_games = int(request.data.get('num_games', 10))
        time_control = request.data.get('time_control', 'all')
        include_analyzed = request.data.get('include_analyzed', False)
        depth = int(request.data.get('depth', 20))
        use_ai = request.data.get('use_ai', True)
        
        logger.info(f"Batch analysis request - User: {user.username}, Games: {num_games}, "
                   f"Time Control: {time_control}, Include analyzed: {include_analyzed}, "
                   f"Depth: {depth}, Use AI: {use_ai}")

        # Validate input
        if num_games <= 0 or num_games > MAX_BATCH_SIZE:
            return Response(
                {"error": f"Number of games must be between 1 and {MAX_BATCH_SIZE}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get games based on criteria
        games_query = Game.objects.filter(user=user)
        
        # Apply time control filter if specified
        if time_control != 'all':
            games_query = games_query.filter(time_control=time_control)
        
        # Convert include_analyzed to boolean if it's a string
        if isinstance(include_analyzed, str):
            include_analyzed = include_analyzed.lower() == 'true'
            
        # Filter out analyzed games if specified
        if not include_analyzed:
            games_query = games_query.filter(
                models.Q(analysis__isnull=True) | 
                models.Q(analysis={})
            )
        
        # Get total count for logging
        total_games = games_query.count()
        logger.info(f"Found {total_games} games matching criteria")
            
        # Order by most recent first and limit to requested number
        games = list(games_query.order_by('-date_played')[:num_games])
            
        if not games:
            logger.warning(f"No games found for user {user.username} with criteria: "
                         f"time_control={time_control}, include_analyzed={include_analyzed}")
            return Response(
                {"error": "No games found matching the criteria. Please check if you have uploaded any games or try including analyzed games."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create batch analysis task
        task_manager = TaskManager()
        game_ids = [game.id for game in games]
        task_result = task_manager.create_batch_analysis_job(
            game_ids=game_ids,
            depth=depth,
            use_ai=use_ai
        )
        
        if task_result.get('status') == 'error' or not task_result.get('task_id'):
            logger.error(f"Failed to create batch analysis task: {task_result.get('message', 'Unknown error')}")
            return Response(
                {"error": task_result.get('message', 'Failed to create batch analysis task')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        # Update game statuses to analyzing
        Game.objects.filter(id__in=game_ids).update(status='analyzing')
        
        # Calculate estimated time
        estimated_time = num_games * 2  # Rough estimate: 2 minutes per game
        
        return Response({
            'task_id': task_result['task_id'],
            'total_games': len(game_ids),
            'status': 'PROGRESS',
            'estimated_time': estimated_time,
            'message': f'Starting analysis of {len(game_ids)} games'
        })
        
    except Exception as e:
        logger.error(f"Error in batch_analyze view: {str(e)}", exc_info=True)
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_batch_analysis_status(request, task_id):
    """Check the status of a batch analysis task."""
    try:
        task_manager = TaskManager()
        task_result = task_manager.get_job_status(task_id)
        
        if not task_result:
            return Response({
                'state': 'FAILURE',
                'meta': {
                    'error': 'Task not found',
                    'current': 0,
                    'total': 0,
                    'message': 'Task not found',
                    'progress': 0
                }
            }, status=status.HTTP_404_NOT_FOUND)
            
        task_state = task_result.get('status', 'PENDING')
        task_info = task_result.get('info', {})
        
        # Handle different task states
        if task_state == 'SUCCESS':
            completed_games = task_info.get('completed_games', [])
            failed_games = task_info.get('failed_games', [])
            aggregate_metrics = task_info.get('aggregate_metrics', {})
            
            # Fetch completed games data
            completed_game_data = []
            if completed_games:
                completed_game_data = list(Game.objects.filter(
                    id__in=completed_games
                ).values('id', 'date_played', 'time_control', 'analysis'))
            
            return Response({
                'state': 'SUCCESS',
                'meta': {
                    'current': len(completed_games),
                    'total': task_info.get('total_games', 0),
                    'message': task_info.get('message', 'Analysis complete'),
                    'progress': 100
                },
                'completed_games': completed_game_data,
                'failed_games': failed_games,
                'aggregate_metrics': aggregate_metrics
            })
            
        elif task_state in ['STARTED', 'PROGRESS']:
            current = task_info.get('current', 0)
            total = task_info.get('total', 0)
            progress = int((current / total * 100) if total > 0 else 0)
            
            return Response({
                'state': 'PROGRESS',
                'meta': {
                    'current': current,
                    'total': total,
                    'message': task_info.get('message', 'Analysis in progress...'),
                    'progress': progress
                }
            })
            
        elif task_state == 'PENDING':
            return Response({
                'state': 'PENDING',
                'meta': {
                    'current': 0,
                    'total': task_info.get('total_games', 0),
                    'message': 'Task pending...',
                    'progress': 0
                }
            })
            
        else:  # FAILURE or other states
            return Response({
                'state': 'FAILURE',
                'meta': {
                    'error': task_info.get('error', 'Task failed'),
                    'current': 0,
                    'total': task_info.get('total_games', 0),
                    'message': task_info.get('message', 'Analysis failed'),
                    'progress': 0
                }
            })
            
    except Exception as e:
        logger.error(f"Error checking batch analysis status: {str(e)}", exc_info=True)
        return Response({
            'state': 'FAILURE',
            'meta': {
                'error': str(e),
                'current': 0,
                'total': 0,
                'message': f'Error checking status: {str(e)}',
                'progress': 0
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def generate_dynamic_feedback(results):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    feedback = {
        "timeManagement": {"avgTimePerMove": 0, "suggestion": ""},
        "opening": {"playedMoves": [], "suggestion": ""},
        "endgame": {"evaluation": "", "suggestion": ""},
        "tacticalOpportunities": []
    }

    total_moves = 0
    for game_analysis in results.values():
        for move in game_analysis:
            if move["is_capture"]:
                feedback["tacticalOpportunities"].append(
                    f"Tactical opportunity on move {move['move_number']}"
                )
            feedback["timeManagement"]["avgTimePerMove"] += move.get("time_spent", 0)
            total_moves += 1
            if move["move_number"] <= 5:
                feedback["opening"]["playedMoves"].append(move["move"])

    if total_moves > 0:
        feedback["timeManagement"]["avgTimePerMove"] /= total_moves

    # Generate refined suggestions via OpenAI
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a chess analysis expert providing specific, actionable feedback to help players improve their game."},
                {"role": "user", "content": f"Provide actionable feedback for chess analysis: {json.dumps(feedback)}"}
            ],
            max_tokens=200,
            temperature=0.7
        )
        dynamic_feedback = response.choices[0].message.content.strip()
        feedback["dynamicFeedback"] = dynamic_feedback
    except Exception as e:
        logger.error("Error generating feedback with OpenAI: %s", e)

    return feedback

def extract_suggestion(feedback_text, section):
    """
    Extract the suggestion for a specific section from the dynamic feedback text.
    """
    try:
        start_index = feedback_text.index(f"{section} Suggestion:") + len(f"{section} Suggestion:")
        end_index = feedback_text.index("\n", start_index)
        return feedback_text[start_index:end_index].strip()
    except ValueError:
        return "No suggestion available."

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def game_feedback_view(request, game_id):
    """
    Provide feedback for a specific game by its ID.
    """
    user = request.user
    game = Game.objects.filter(id=game_id, player=user).first()
    if not game:
        return JsonResponse({"error": "Game not found."}, status=404)

    game_analysis = GameAnalysis.objects.filter(game=game)
    if not game_analysis.exists():
        return JsonResponse({"error": "Analysis not found for this game."}, status=404)

    feedback = generate_dynamic_feedback({game.id: game_analysis})
    return JsonResponse({"feedback": feedback}, status=200)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def batch_feedback_view(request):
    """
    Generate and return feedback for a batch of games.
    """
    user = request.user
    game_ids = request.data.get("game_ids", [])
    use_ai = request.data.get("use_ai", True)

    games = Game.objects.filter(id__in=game_ids, player=user)
    if not games.exists():
        return Response({"error": "No valid games found."}, status=404)

    analyzer = GameAnalyzer()
    batch_feedback = {}

    try:
        for game in games:
            game_analysis = GameAnalysis.objects.filter(game=game)
            if game_analysis.exists():
                feedback = analyzer.generate_feedback(game_analysis)
                
                # Generate AI feedback if requested
                if use_ai and os.getenv("OPENAI_API_KEY"):
                    try:
                        ai_feedback = ai_feedback_generator.generate_personalized_feedback(
                            game_analysis=game_analysis,
                            player_profile={
                                "username": user.username,
                                "rating": getattr(user.profile, "rating", None),
                                "total_games": getattr(user.profile, "total_games", 0),
                                "preferred_openings": getattr(user.profile, "preferred_openings", [])
                            }
                        )
                        feedback["ai_suggestions"] = ai_feedback
                    except Exception as e:
                        logger.error("Error generating AI feedback: %s", str(e))
                
            batch_feedback[game.id] = feedback
    finally:
        analyzer.close_engine()

    return Response({"batch_feedback": batch_feedback}, status=200)

#==================================Login Logic==================================

# Helper function to generate tokens for a user
def get_tokens_for_user(user):
    """
    Generate JWT tokens for a given user.
    """
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }

@api_view(["POST"])
@csrf_exempt  # Exempt logout from CSRF
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Handle user logout by blacklisting the refresh token.
    """
    try:
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return Response({"error": "Refresh token is required."},
            status=status.HTTP_400_BAD_REQUEST)
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({"message": "Logout successful!"},
                        status=status.HTTP_200_OK)
    except AttributeError:
        return Response({"error": "Blacklisting is not enabled."},
                        status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

#================================== Testing Data ==================================
def game_analysis_view(request, game_id):
    """
    Provide a mock analysis for a specific game by its ID.
    """
    analysis = [
        {"move": "e4", "score": 0.3},
        {"move": "e5", "score": 0.2},
        {"move": "Nf3", "score": 0.5},
    ]
    return JsonResponse({"game_id": game_id, "analysis": analysis})

#================================== Dashboard ==================================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_view(request):
    """Get user dashboard data."""
    user = request.user
    games = Game.objects.filter(user=user)
    
    # Get the user's profile for rating
    profile = Profile.objects.get(user=user)
    
    # Calculate basic statistics
    total_games = games.count()
    
    # Calculate win rate
    win_rate = 0
    if total_games > 0:
        wins = games.filter(result='win').count()
        win_rate = round((wins / total_games) * 100, 2)
    
    # Calculate average accuracy from analyzed games
    analyzed_games = games.filter(analysis__isnull=False)
    avg_accuracy = 0
    if analyzed_games.exists():
        accuracies = [
            game.analysis.get('average_accuracy', 0) 
            for game in analyzed_games 
            if isinstance(game.analysis, dict)
        ]
        if accuracies:
            avg_accuracy = round(sum(accuracies) / len(accuracies), 2)
    
    # Get recent games
    recent_games = games.order_by('-date_played')[:5].values(
        'id', 'white', 'black', 'result', 'opening_name', 'date_played', 'opponent', 'analysis'
    )
    
    return Response({
        'total_games': total_games,
        'win_rate': win_rate,
        'average_accuracy': avg_accuracy,
        'credits': profile.credits,
        'recent_games': list(recent_games)  # Convert to list to ensure serialization
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def all_games_view(request):
    """
    Fetch all available games (generic endpoint).
    """
    games = Game.objects.all().order_by("-played_at")  # Fetch all games
    games_data = [
        {
            "id": game.id,
            "title": game.title,
            "result": game.result,
            "played_at": game.played_at,
        }
        for game in games
    ]
    return Response({"games": games_data}, status=status.HTTP_200_OK)

@rate_limit(endpoint_type='CREDITS')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_credits(request):
    """Get the current user's credit balance."""
    try:
        with transaction.atomic():
            profile = Profile.objects.select_for_update().get(user=request.user)
            logger.info(f"Retrieved credits for user {request.user.username}: {profile.credits}")
            return Response({'credits': profile.credits})
    except Profile.DoesNotExist:
        logger.error(f"Profile not found for user {request.user.username}")
        return Response({'error': 'Profile not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting credits for user {request.user.username}: {str(e)}")
        return Response({'error': str(e)}, status=500)

@rate_limit(endpoint_type='CREDITS')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deduct_credits(request):
    """Deduct credits from the user's balance."""
    try:
        with transaction.atomic():
            amount = int(request.data.get('amount', 1))
            profile = Profile.objects.select_for_update().get(user=request.user)
            
            logger.info(f"Attempting to deduct {amount} credits from user {request.user.username} (current balance: {profile.credits})")
            
            if profile.credits < amount:
                logger.warning(f"Insufficient credits for user {request.user.username}: has {profile.credits}, needs {amount}")
                return Response({
                    'error': 'Insufficient credits',
                    'credits': profile.credits
                }, status=400)
            
            profile.credits -= amount
            profile.save()
            
            # Record the transaction
            Transaction.objects.create(
                user=request.user,
                transaction_type='usage',
                amount=0,
                credits=amount,
                status='completed'
            )
            
            logger.info(f"Successfully deducted {amount} credits. New balance: {profile.credits}")
            return Response({'credits': profile.credits})
    except Profile.DoesNotExist:
        logger.error(f"Profile not found for user {request.user.username}")
        return Response({'error': 'Profile not found'}, status=404)
    except ValueError:
        logger.error(f"Invalid amount provided: {request.data.get('amount')}")
        return Response({'error': 'Invalid amount'}, status=400)
    except Exception as e:
        logger.error(f"Error deducting credits: {str(e)}")
        return Response({'error': str(e)}, status=500)

@rate_limit(endpoint_type='CREDITS')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase_credits(request):
    """Create a checkout session for credit purchase."""
    try:
        package_id = request.data.get('package_id')
        logger.info(f"Attempting to create checkout session for package {package_id} for user {request.user.username}")
        
        if not package_id or package_id not in CREDIT_PACKAGES:
            logger.error(f"Invalid package ID: {package_id}")
            return Response({'error': f'Invalid package: {package_id}'}, status=400)
        
        if not settings.STRIPE_SECRET_KEY:
            logger.error("Stripe secret key not configured")
            return Response({'error': 'Payment processing is not configured'}, status=500)
        
        package = CREDIT_PACKAGES[package_id]
        try:
            checkout_session = PaymentProcessor.create_checkout_session(
                user_id=request.user.id,
                package_id=package_id,
                amount=package['price'],
                credits=package['credits']
            )
            
            logger.info(f"Successfully created checkout session for user {request.user.username}")
            return Response({
                'success': True,
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id
            })
        except Exception as e:
            logger.error(f"Error in PaymentProcessor: {str(e)}")
            return Response(
                {'error': 'Error creating checkout session',
                'details': str(e)
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        return Response({
            'error': 'Error processing request',
            'details': str(e)
        }, status=500)

@rate_limit(endpoint_type='CREDITS')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_purchase(request):
    """Confirm a credit purchase and add credits to user's account."""
    session_id = request.data.get('session_id')
    logger.info(f"Confirming purchase for session {session_id} for user {request.user.username}")
    
    if not session_id:
        return Response({'error': 'Session ID required'}, status=400)
    
    try:
        # First check if this payment was already processed
        existing_transaction = Transaction.objects.filter(
            stripe_payment_id=session_id,
            status='completed'
        ).first()
        
        if existing_transaction:
            logger.warning(f"Payment {session_id} was already processed")
            profile = Profile.objects.get(user=request.user)
            return Response({
                'success': True,
                'credits': profile.credits,
                'added_credits': existing_transaction.credits,
                'already_processed': True
            })

        # Then verify the payment outside the transaction
        payment_data = PaymentProcessor.verify_payment(session_id)
        if not payment_data:
            logger.error(f"Invalid or expired session: {session_id}")
            return Response({'error': 'Invalid or expired session'}, status=400)

        # Finally, update credits in a transaction
        with transaction.atomic():
            profile = Profile.objects.select_for_update(nowait=True).get(user=request.user)
            old_credits = profile.credits
            profile.credits += payment_data['credits']
            profile.save()
            
            # Record the transaction
            new_transaction = Transaction.objects.create(
                user=request.user,
                transaction_type='purchase',
                amount=payment_data['amount'],
                credits=payment_data['credits'],
                status='completed',
                stripe_payment_id=session_id
            )
            
            logger.info(f"Purchase confirmed. Credits updated from {old_credits} to {profile.credits}")
            return Response({
                'success': True,
                'credits': profile.credits,
                'added_credits': payment_data['credits']
            })
            
    except Profile.DoesNotExist:
        logger.error(f"Profile not found for user {request.user.username}")
        return Response({'error': 'Profile not found'}, status=404)
    except transaction.TransactionManagementError as e:
        logger.error(f"Transaction error: {str(e)}")
        return Response({
            'error': 'Transaction error',
            'details': 'Please try again in a moment'
        }, status=500)
    except Exception as e:
        logger.error(f"Error confirming purchase: {str(e)}")
        return Response({
            'error': 'Error processing purchase',
            'details': str(e)
        }, status=500)

@api_view(["POST"])
@csrf_exempt  # Exempt token refresh from CSRF
def token_refresh_view(request):
    """Refresh the user's access token."""
    try:
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'Refresh token is required'}, status=400)

        refresh = RefreshToken(refresh_token)
        access_token = str(refresh.access_token)

        return Response({
            'access': access_token
        })
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@csrf_exempt  # Exempt from CSRF as user isn't logged in
@rate_limit(endpoint_type='AUTH')
@api_view(['POST'])
def request_password_reset(request):
    """Handle password reset request."""
    try:
        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal that the user doesn't exist
            return Response(
                {"message": "If an account exists with this email, you will receive a password reset link."},
                status=status.HTTP_200_OK
            )

        # Generate password reset token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build reset URL
        current_site = get_current_site(request)
        reset_url = f"http://{current_site.domain}/reset-password/{uid}/{token}/"
        
        # Send reset email
        try:
            send_password_reset_email(user, reset_url)
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            return Response(
                {"error": "Failed to send password reset email. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {"message": "Password reset link has been sent to your email."},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Password reset request error: {str(e)}")
        return Response(
            {"error": "An error occurred. Please try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["POST"])
@csrf_exempt  # Exempt password reset from CSRF
def reset_password(request):
    """
    Handle password reset with token.
    """
    try:
        uid = request.data.get("uid")
        token = request.data.get("token")
        new_password = request.data.get("new_password")

        if not all([uid, token, new_password]):
            return Response(
                {"error": "All fields are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            uid = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"error": "invalid_token", "message": "Invalid reset link."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {"error": "expired_token", "message": "Invalid or expired reset link."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate password complexity
        try:
            validate_password_complexity(new_password)
        except ValidationError as e:
            return Response(
                {"error": "complexity", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if new password is the same as old password
        if user.check_password(new_password):
            return Response(
                {"error": "same_password", "message": "New password cannot be the same as your old password."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password
        user.set_password(new_password)
        user.save()

        return Response(
            {"message": "Password has been reset successfully."},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        return Response(
            {"error": "server_error", "message": "An error occurred. Please try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    Handle user profile operations.
    """
    try:
        if request.method == "GET":
            profile = Profile.objects.get(user=request.user)
            return Response({
                "username": request.user.username,
                "email": request.user.email,
                "rating": profile.rating,
                "credits": profile.credits,
                "preferences": profile.preferences,
                "created_at": profile.created_at,
                "games_analyzed": Game.objects.filter(user=request.user).count(),
            })
        
        elif request.method == "PATCH":
            data = request.data
            user = request.user
            profile = Profile.objects.get(user=user)
            
            # Update username if provided and available
            new_username = data.get("username")
            if new_username and new_username != user.username:
                if User.objects.filter(username=new_username).exists():
                    return Response(
                        {"error": "Username already taken."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                user.username = new_username
            
            # Update preferences
            new_preferences = data.get("preferences")
            if new_preferences:
                profile.preferences = {
                    **profile.preferences,
                    **new_preferences
                }
            
            # Save changes
            user.save()
            profile.save()
            
            return Response({
                "message": "Profile updated successfully.",
                "username": user.username,
                "preferences": profile.preferences
            })
            
    except Profile.DoesNotExist:
        return Response(
            {"error": "Profile not found."},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Profile operation error: {str(e)}")
        return Response(
            {"error": "An error occurred. Please try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def send_password_reset_email(user, reset_url):
    """Send password reset email to user."""
    subject = "Reset your ChessMate password"
    html_message = render_to_string(
        "email/password_reset.html",
        {
            "user": user,
            "reset_url": reset_url
        }
    )
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )

@api_view(['GET'])
def health_check(request):
    """
    Health check endpoint for monitoring application status.
    """
    return Response({"status": "healthy"}, status=status.HTTP_200_OK)

@api_view(['GET'])
@ensure_csrf_cookie
def csrf(request):
    """
    Get CSRF token for the client.
    """
    response = Response({'detail': 'CSRF cookie set'})
    if settings.DEBUG:
        response["Access-Control-Allow-Origin"] = request.headers.get('origin', 'http://localhost:3000')
    response["Access-Control-Allow-Credentials"] = 'true'
    return response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_ai_feedback(request, game_id):
    """Generate AI feedback for an analyzed game."""
    try:
        game = Game.objects.get(id=game_id, user=request.user)
        
        if not game.analysis or not game.analysis.get('analysis_complete'):
            return Response(
                {"error": "Game must be analyzed first"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check if user has enough credits
        profile = Profile.objects.get(user=request.user)
        if profile.credits < 1:
            return Response(
                {"error": "Insufficient credits"},
                status=status.HTTP_402_PAYMENT_REQUIRED
            )
            
        try:
            analyzer = GameAnalyzer()
            feedback = analyzer.generate_ai_feedback(game.analysis['moves'], game)
            
            # Update game with feedback
            game.analysis['ai_feedback'] = feedback
            game.analysis['ai_feedback_status'] = 'completed'
            game.save()
            
            # Deduct credits
            profile.credits -= 1
            profile.save()
            
            return Response({
                'status': 'success',
                'feedback': feedback
            })
            
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            game.analysis['ai_feedback_status'] = 'failed'
            game.save()
            return Response({
                'status': 'error',
                'error': 'AI feedback temporarily unavailable',
                'detail': str(e)
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
    except Game.DoesNotExist:
        return Response(
            {"error": "Game not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error generating AI feedback: {str(e)}", exc_info=True)
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_profile(request):
    """
    Retrieve profile data for the logged-in user.
    """
    try:
        profile = Profile.objects.get(user=request.user)
        games = Game.objects.filter(user=request.user)
        
        # Calculate total games and win rate
        total_games = games.count()
        wins = games.filter(result='win').count()
        win_rate = round((wins / total_games) * 100, 2) if total_games > 0 else 0
        
        # Calculate average accuracy from analyzed games
        analyzed_games = games.filter(analysis__isnull=False).count()
        avg_accuracy = 0
        if analyzed_games > 0:
            accuracies = [
                game.analysis.get('average_accuracy', 0) 
                for game in games.filter(analysis__isnull=False) 
                if isinstance(game.analysis, dict)
            ]
            if accuracies:
                avg_accuracy = round(sum(accuracies) / len(accuracies), 2)
        
        # Get achievements
        achievements = calculate_achievements(profile, games)
        
        # Calculate performance statistics for each time control
        performance_stats = profile.get_performance_stats()
        
        # Calculate time control distribution
        time_control_distribution = {
            'bullet': 0,
            'blitz': 0,
            'rapid': 0,
            'classical': 0
        }
        
        # First count games in each category
        valid_games = 0
        for game in games:
            time_category = game.get_time_control_category()
            if time_category:
                time_control_distribution[time_category] += 1
                valid_games += 1
        
        # Then calculate percentages based on valid games count
        if valid_games > 0:
            for category in time_control_distribution:
                time_control_distribution[category] = round(
                    (time_control_distribution[category] / valid_games) * 100, 2
                )
        
        # Get rating history
        rating_history = profile.get_rating_history()
        
        profile_data = {
            'username': request.user.username,
            'email': request.user.email,
            'credits': profile.credits,
            'chesscom_username': profile.chesscom_username,
            'lichess_username': profile.lichess_username,
            'current_ratings': {
                'bullet': profile.bullet_rating,
                'blitz': profile.blitz_rating,
                'rapid': profile.rapid_rating,
                'classical': profile.classical_rating
            },
            'rating_history': rating_history,
            'performance_stats': performance_stats,
            'total_games': total_games,
            'win_rate': win_rate,
            'average_accuracy': avg_accuracy,
            'achievements': achievements,
            'time_control_distribution': time_control_distribution
        }
        
        return Response(profile_data)
        
    except Profile.DoesNotExist:
        return Response(
            {"error": "Profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error in get_profile: {str(e)}", exc_info=True)
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def calculate_time_control_stats(games):
    """Calculate statistics for different time controls."""
    stats = {
        'bullet': {'count': 0, 'wins': 0},
        'blitz': {'count': 0, 'wins': 0},
        'rapid': {'count': 0, 'wins': 0},
        'classical': {'count': 0, 'wins': 0}
    }
    
    for game in games:
        category = game.get_time_control_category()
        if category:
            stats[category]['count'] += 1
            if game.result == 'win':
                stats[category]['wins'] += 1
    
    return stats

def calculate_opening_stats(games):
    """Calculate statistics for openings."""
    openings = {}
    for game in games:
        opening = game.opening_name
        if opening not in openings:
            openings[opening] = {'count': 0, 'wins': 0}
        openings[opening]['count'] += 1
        if game.result == 'win':
            openings[opening]['wins'] += 1
    
    # Sort by frequency and get top 5
    sorted_openings = dict(sorted(openings.items(), key=lambda x: x[1]['count'], reverse=True)[:5])
    return sorted_openings

def calculate_color_performance(games):
    """Calculate performance statistics for white and black pieces."""
    stats = {
        'white': {'games': 0, 'wins': 0},
        'black': {'games': 0, 'wins': 0}
    }
    
    for game in games:
        if game.white.lower() == game.user.username.lower():
            stats['white']['games'] += 1
            if game.result == 'win':
                stats['white']['wins'] += 1
        else:
            stats['black']['games'] += 1
            if game.result == 'win':
                stats['black']['wins'] += 1
    
    return stats

def calculate_achievements(profile, games):
    """Calculate user achievements."""
    achievements = []
    
    # Games played achievements
    games_count = games.count()
    achievements.extend([
        {
            'name': 'Novice Player',
            'description': 'Play your first game',
            'icon': 'award',
            'completed': games_count >= 1,
            'progress': min(games_count, 1),
            'target': 1
        },
        {
            'name': 'Dedicated Player',
            'description': 'Play 50 games',
            'icon': 'award',
            'completed': games_count >= 50,
            'progress': min(games_count, 50),
            'target': 50
        },
        {
            'name': 'Century Player',
            'description': 'Play 100 games',
            'icon': 'trophy',
            'completed': games_count >= 100,
            'progress': min(games_count, 100),
            'target': 100
        },
        {
            'name': 'Chess Veteran',
            'description': 'Play 500 games',
            'icon': 'trophy',
            'completed': games_count >= 500,
            'progress': min(games_count, 500),
            'target': 500
        }
    ])
    
    # Rating achievements
    max_rating = max(
        profile.bullet_rating,
        profile.blitz_rating,
        profile.rapid_rating,
        profile.classical_rating
    )
    achievements.extend([
        {
            'name': 'Rising Star',
            'description': 'Reach 1400 rating',
            'icon': 'trending-up',
            'completed': max_rating >= 1400,
            'progress': min(max_rating, 1400),
            'target': 1400
        },
        {
            'name': 'Intermediate',
            'description': 'Reach 1600 rating',
            'icon': 'trending-up',
            'completed': max_rating >= 1600,
            'progress': min(max_rating, 1600),
            'target': 1600
        },
        {
            'name': 'Advanced',
            'description': 'Reach 1800 rating',
            'icon': 'trending-up',
            'completed': max_rating >= 1800,
            'progress': min(max_rating, 1800),
            'target': 1800
        },
        {
            'name': 'Expert',
            'description': 'Reach 2000 rating',
            'icon': 'star',
            'completed': max_rating >= 2000,
            'progress': min(max_rating, 2000),
            'target': 2000
        },
        {
            'name': 'Master',
            'description': 'Reach 2200 rating',
            'icon': 'crown',
            'completed': max_rating >= 2200,
            'progress': min(max_rating, 2200),
            'target': 2200
        }
    ])
    
    # Win streak achievements
    win_streak = 0
    max_win_streak = 0
    for game in games.order_by('date_played'):
        if game.result == 'win':
            win_streak += 1
            max_win_streak = max(max_win_streak, win_streak)
        else:
            win_streak = 0
    
    achievements.extend([
        {
            'name': 'Winning Streak',
            'description': 'Win 3 games in a row',
            'icon': 'zap',
            'completed': max_win_streak >= 3,
            'progress': min(max_win_streak, 3),
            'target': 3
        },
        {
            'name': 'Hot Streak',
            'description': 'Win 5 games in a row',
            'icon': 'flame',
            'completed': max_win_streak >= 5,
            'progress': min(max_win_streak, 5),
            'target': 5
        },
        {
            'name': 'Unstoppable',
            'description': 'Win 10 games in a row',
            'icon': 'fire',
            'completed': max_win_streak >= 10,
            'progress': min(max_win_streak, 10),
            'target': 10
        }
    ])
    
    # Analysis achievements
    analyzed_games = games.filter(analysis__isnull=False).count()
    achievements.extend([
        {
            'name': 'Analyst',
            'description': 'Analyze your first game',
            'icon': 'search',
            'completed': analyzed_games >= 1,
            'progress': min(analyzed_games, 1),
            'target': 1
        },
        {
            'name': 'Deep Thinker',
            'description': 'Analyze 10 games',
            'icon': 'brain',
            'completed': analyzed_games >= 10,
            'progress': min(analyzed_games, 10),
            'target': 10
        },
        {
            'name': 'Chess Student',
            'description': 'Analyze 50 games',
            'icon': 'book',
            'completed': analyzed_games >= 50,
            'progress': min(analyzed_games, 50),
            'target': 50
        }
    ])
    
    # Platform achievements
    has_chesscom = bool(profile.chesscom_username)
    has_lichess = bool(profile.lichess_username)
    achievements.extend([
        {
            'name': 'Chess.com Player',
            'description': 'Link your Chess.com account',
            'icon': 'link',
            'completed': has_chesscom,
            'progress': 1 if has_chesscom else 0,
            'target': 1
        },
        {
            'name': 'Lichess Player',
            'description': 'Link your Lichess account',
            'icon': 'link',
            'completed': has_lichess,
            'progress': 1 if has_lichess else 0,
            'target': 1
        },
        {
            'name': 'Chess Master',
            'description': 'Link both Chess.com and Lichess accounts',
            'icon': 'award',
            'completed': has_chesscom and has_lichess,
            'progress': (1 if has_chesscom else 0) + (1 if has_lichess else 0),
            'target': 2
        }
    ])
    
    return achievements

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def link_account(request):
    """Link a chess platform account to the user's profile."""
    try:
        platform = request.data.get('platform')
        username = request.data.get('username')

        if not platform or not username:
            return Response(
                {"error": "Platform and username are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if platform not in ['chess.com', 'lichess']:
            return Response(
                {"error": "Invalid platform"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update the profile
        profile = Profile.objects.get(user=request.user)
        
        # Update username based on platform
        if platform == 'chess.com':
            profile.chesscom_username = username
        else:
            profile.lichess_username = username

        # Get the latest game for this platform and username
        latest_game = Game.objects.filter(
            user=request.user,
            platform=platform
        ).filter(
            models.Q(white__iexact=username) |
            models.Q(black__iexact=username)
        ).order_by('-date_played').first()

        # Update ratings from the latest game if available
        if latest_game:
            time_category = latest_game.get_time_control_category()
            if time_category:
                is_white = (
                    (platform == 'chess.com' and latest_game.white.lower() == username.lower()) or
                    (platform == 'lichess' and latest_game.white.lower() == username.lower())
                )
                rating = latest_game.white_elo if is_white else latest_game.black_elo
                if rating:
                    if time_category == 'bullet':
                        profile.bullet_rating = rating
                    elif time_category == 'blitz':
                        profile.blitz_rating = rating
                    elif time_category == 'rapid':
                        profile.rapid_rating = rating
                    elif time_category == 'classical':
                        profile.classical_rating = rating

        profile.save()

        return Response({
            "message": f"Successfully linked {platform} account",
            "username": username
        })
    except Profile.DoesNotExist:
        return Response(
            {"error": "Profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error linking account: {str(e)}")
        return Response(
            {"error": "An error occurred while linking the account"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unlink_account(request):
    """Unlink a chess platform account."""
    try:
        platform = request.data.get('platform')
        if not platform:
            return Response(
                {"error": "Platform is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        profile = request.user.profile
        
        # Get the latest game before unlinking
        latest_game = None
        if platform == 'chess.com' and profile.chesscom_username:
            latest_game = (
                Game.objects.filter(
                    user=request.user,
                    platform='chess.com'
                ).filter(
                    models.Q(white__iexact=profile.chesscom_username) |
                    models.Q(black__iexact=profile.chesscom_username)
                ).order_by('-date_played').first()
            )
            profile.chesscom_username = None
        elif platform == 'lichess' and profile.lichess_username:
            latest_game = (
                Game.objects.filter(
                    user=request.user,
                    platform='lichess'
                ).filter(
                    models.Q(white__iexact=profile.lichess_username) |
                    models.Q(black__iexact=profile.lichess_username)
                ).order_by('-date_played').first()
            )
            profile.lichess_username = None
        else:
            return Response(
                {"error": "No account to unlink"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Save profile first to update username
        profile.save()

        # If no accounts are linked, reset ratings and history
        if not profile.chesscom_username and not profile.lichess_username:
            profile.bullet_rating = 1200
            profile.blitz_rating = 1200
            profile.rapid_rating = 1200
            profile.classical_rating = 1200
            profile.rating_history = {}
            profile.save()
            
            # Clear any stored rating changes
            if profile.preferences:
                keys_to_remove = [key for key in profile.preferences.keys() if key.startswith('last_rating_change_')]
                for key in keys_to_remove:
                    del profile.preferences[key]
                profile.save()
        else:
            # Update ratings based on remaining linked account
            profile.update_ratings_for_existing_games()

        return Response({
            "message": f"{platform} account unlinked successfully",
            "ratings": {
                "bullet": profile.bullet_rating,
                "blitz": profile.blitz_rating,
                "rapid": profile.rapid_rating,
                "classical": profile.classical_rating
            }
        })
    except Profile.DoesNotExist:
        return Response(
            {"error": "Profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error unlinking account: {str(e)}")
        return Response(
            {"error": "An error occurred while unlinking the account"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
