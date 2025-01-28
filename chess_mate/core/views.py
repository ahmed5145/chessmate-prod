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
from django.contrib.auth import authenticate
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
from .tasks import analyze_game_task, analyze_batch_games_task
from .task_manager import RQTaskManager

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
task_manager = RQTaskManager()

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
def register_view(request):
    """Handle user registration with email verification."""
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
                    
                # Create profile with verification token and starter credits
                verification_token = EmailVerificationToken.generate_token()
                profile = Profile.objects.create(
                    user=user,
                    email_verification_token=verification_token,
                    email_verification_sent_at=timezone.now(),
                    credits=10  # Explicitly set starter credits
                )
                
                logger.debug(f"Created profile for user: {username} with {profile.credits} credits")
                
                # Send verification email
                try:
                    send_verification_email(request, user, verification_token)
                    logger.debug(f"Sent verification email to: {email}")
                except Exception as e:
                    logger.error(f"Error sending verification email: {str(e)}", exc_info=True)
                    # Don't fail registration if email fails, but log it
                    pass

            return Response(
                {
                    "message": "Registration successful! Please check your email to verify your account.",
                    "email": email
                },
                status=status.HTTP_201_CREATED
            )

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

@ensure_csrf_cookie
@rate_limit(endpoint_type='AUTH')
@api_view(['POST'])
def login_view(request):
    """
    Handle user login with email verification check.
    """
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
        return Response({
            "message": "Login successful!",
            "tokens": tokens,
            "user": {
                "username": user.username,
                "email": user.email
            }
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return Response(
            {"error": "An error occurred during login."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def fetch_games(request):
    """
    Fetch games from Chess.com or Lichess APIs based on the username and platform provided.
    """
    user = request.user
    data = request.data
    platform = data.get("platform")
    username = data.get("username")
    game_mode = data.get("game_mode", "all")
    num_games = int(data.get("num_games", 10))

    if not platform or not username:
        return Response(
            {"error": "Platform and username are required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    allowed_game_modes = ["all", "bullet", "blitz", "rapid", "classical"]
    if game_mode not in allowed_game_modes:
        return Response(
            {"error": "Invalid game mode. Allowed modes: all, bullet, blitz, rapid, classical."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        with transaction.atomic():
            profile = Profile.objects.select_for_update().get(user=user)
            required_credits = num_games
            
            if profile.credits < required_credits:
                return Response(
                    {"error": f"Not enough credits. Required: {required_credits}, Available: {profile.credits}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                if platform == "chess.com":
                    games = ChessComService.fetch_games(username, game_mode, limit=num_games)
                elif platform == "lichess":
                    games = LichessService.fetch_games(username, game_mode, limit=num_games)
                else:
                    return Response(
                        {"error": "Invalid platform. Use 'chess.com' or 'lichess'."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if not games:
                    return Response(
                        {"message": "No games found for the given username and criteria."},
                        status=status.HTTP_200_OK
                    )
                
                logger.info(f"Fetched {len(games)} games from {platform} for user {username}")
            except Exception as e:
                logger.error(f"Error fetching games from {platform}: {str(e)}")
                return Response(
                    {"error": f"Failed to fetch games from {platform}. Please try again later."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            saved_games = []
            saved_count = 0
            for game_data in games:
                try:
                    # Ensure game_id exists and is unique
                    game_id = game_data.get("game_id")
                    if not game_id:
                        logger.warning(f"Skipping game without game_id: {game_data}")
                        continue
                        
                    # Check if game already exists
                    if Game.objects.filter(user=user, platform=platform, game_id=game_id).exists():
                        logger.info(f"Game {game_id} already exists for user {user.username}")
                        continue

                    game = Game.objects.create(
                        user=user,
                        platform=platform,
                        game_id=game_id,
                        pgn=game_data.get("pgn", ""),
                        result=game_data.get("result", "unknown"),
                        white=game_data.get("white", ""),
                        black=game_data.get("black", ""),
                        opponent=game_data.get("opponent", "Unknown"),
                        opening_name=game_data.get("opening_name", "Unknown Opening"),
                        date_played=game_data.get("played_at") or datetime.now()
                    )
                    saved_count += 1
                    saved_games.append({
                        "id": game.id,
                        "platform": game.platform,
                        "white": game.white,
                        "black": game.black,
                        "opponent": game.opponent,
                        "result": game.result,
                        "date_played": game.date_played,
                        "opening_name": game.opening_name,
                        "game_id": game.game_id
                    })
                    
                    if saved_count >= num_games:
                        break
                except Exception as e:
                    logger.error(f"Error saving game: {str(e)}")
                    continue

            if saved_count > 0:
                profile.credits -= saved_count
                profile.save()

                Transaction.objects.create(
                    user=user,
                    transaction_type='usage',
                    credits=saved_count,
                    status='completed'
                )

                logger.info(f"Successfully saved {saved_count} games for user {user.username}")
                return Response(
                    {
                        "message": f"Successfully fetched and saved {saved_count} games!",
                        "games_saved": saved_count,
                        "credits_deducted": saved_count,
                        "credits_remaining": profile.credits,
                        "games": saved_games
                    },
                    status=status.HTTP_201_CREATED
                )
            else:
                logger.warning(f"No new games were saved for user {user.username}")
                return Response(
                    {
                        "message": "No new games were saved. They might already exist in your account.",
                        "games_saved": 0,
                        "credits_deducted": 0,
                        "credits_remaining": profile.credits,
                        "games": []
                    },
                    status=status.HTTP_200_OK
                )

    except Profile.DoesNotExist:
        logger.error(f"Profile not found for user {user.username}")
        return Response(
            {"error": "User profile not found."},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error in fetch_games: {str(e)}")
        return Response(
            {"error": "Failed to fetch games. Please try again later."},
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
    
    games = games.order_by("-date_played")
    
    games_data = [
        {
            "id": game.id,
            "white": game.white,
            "black": game.black,
            "result": game.result,
            "date_played": game.date_played,
            "platform": game.platform,
            "analysis": game.analysis
        }
        for game in games
    ]
    return Response({"games": games_data}, status=status.HTTP_200_OK)

@rate_limit(endpoint_type='ANALYSIS')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_game(request, game_id):
    """Start analysis for a specific game."""
    try:
        game = Game.objects.get(id=game_id)
        
        # Check if user has permission to analyze this game
        if not game.user == request.user and not request.user.is_staff:
            return Response(
                {'error': 'You do not have permission to analyze this game'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Clear any existing analysis
        GameAnalysis.objects.filter(game=game).delete()
        
        # Create a new analysis job
        depth = request.data.get('depth', 20)
        use_ai = request.data.get('use_ai', True)
        
        result = task_manager.create_analysis_job(
            game_id=game_id,
            depth=depth,
            use_ai=use_ai
        )
        
        if result['status'] == 'created':
            return Response({
                'status': 'started',
                'task_id': result['task_id']
            })
        else:
            return Response({
                'error': result.get('error', 'Failed to start analysis')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Game.DoesNotExist:
        return Response(
            {'error': 'Game not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_analysis_status(request, task_id):
    """Check the status of an analysis task."""
    try:
        result = task_manager.get_job_status(task_id)
        
        if result['status'] == 'completed':
            return Response({
                'status': 'completed',
                'result': result.get('result')
            })
        elif result['status'] == 'failed':
            return Response({
                'status': 'failed',
                'error': result.get('message', 'Analysis failed')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({
                'status': 'in_progress',
                'message': result.get('message', 'Analysis in progress')
            })
            
    except Exception as e:
        return Response({
            'status': 'error',
            'error': str(e)
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
        analysis = GameAnalysis.objects.get(game=game)
        return Response({"analysis": analysis.analysis_data}, status=status.HTTP_200_OK)
    except Game.DoesNotExist:
        return Response({"error": "Game not found or access denied."}, status=status.HTTP_404_NOT_FOUND)
    except GameAnalysis.DoesNotExist:
        return Response({"error": "Analysis not found for this game."}, status=status.HTTP_404_NOT_FOUND)

@rate_limit(endpoint_type='ANALYSIS')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def batch_analyze(request):
    """Analyze multiple games for a user."""
    user = request.user
    num_games = request.data.get('num_games', 5)
    depth = request.data.get('depth', 20)
    use_ai = request.data.get('use_ai', True)
    include_unanalyzed = request.data.get('include_unanalyzed', True)

    try:
        # Get games based on the include_unanalyzed parameter
        if include_unanalyzed:
            games = Game.objects.filter(user=user).order_by('-date_played')[:num_games]
        else:
            games = Game.objects.filter(user=user, analysis__isnull=True).order_by('-date_played')[:num_games]
            
        if not games:
            return Response({"error": "No games found to analyze"}, status=status.HTTP_400_BAD_REQUEST)

        # Create a task group for this batch
        game_ids = list(games.values_list('id', flat=True))
        
        # Start the Celery task
        task = analyze_batch_games_task.delay(
            game_ids=game_ids,
            depth=depth,
            use_ai=use_ai
        )

        # Return task ID for status checking
        return Response({
            "message": "Batch analysis started",
            "task_id": task.id,
            "total_games": len(game_ids),
            "estimated_time": len(game_ids) * 2  # Rough estimate: 2 minutes per game
        })

    except Exception as e:
        logger.error("Error setting up batch analysis: %s", str(e))
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_batch_analysis_status(request, task_id):
    """Check the status of a batch analysis task."""
    try:
        task = AsyncResult(task_id)
        
        if task.ready():
            if task.successful():
                result = task.get()
                
                # Add feedback source information to the response
                if isinstance(result, dict) and 'results' in result:
                    for game_id, game_result in result['results'].items():
                        if isinstance(game_result, dict) and 'results' in game_result:
                            analysis_result = game_result['results']
                            if 'feedback' not in analysis_result:
                                analysis_result['feedback'] = {
                                    'source': 'error_fallback',
                                    'error': 'Failed to generate feedback'
                                }
                            elif 'source' not in analysis_result['feedback']:
                                analysis_result['feedback']['source'] = (
                                    'openai_analysis' if 'ai_suggestions' in analysis_result['feedback']
                                    else 'statistical_analysis'
                                )
                
                return Response({
                    "status": "completed",
                    "results": result
                })
            else:
                error = str(task.result)
                return Response({
                    "status": "failed",
                    "error": error
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # Get progress from cache
            progress = cache.get(f"batch_analysis_progress_{task_id}")
            if progress:
                # Add feedback source to in-progress results
                if isinstance(progress, dict) and 'current_results' in progress:
                    for game_id, game_result in progress['current_results'].items():
                        if isinstance(game_result, dict) and 'results' in game_result:
                            analysis_result = game_result['results']
                            if 'feedback' in analysis_result and 'source' not in analysis_result['feedback']:
                                analysis_result['feedback']['source'] = (
                                    'openai_analysis' if 'ai_suggestions' in analysis_result['feedback']
                                    else 'statistical_analysis'
                                )
                
                return Response({
                    "status": "in_progress",
                    "progress": progress
                })
            else:
                return Response({
                    "status": "in_progress",
                    "progress": {
                        "current": 0,
                        "total": 0
                    }
                })
            
    except Exception as e:
        logger.error(f"Error checking batch analysis status: {str(e)}")
        return Response({
            "status": "error",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def generate_dynamic_feedback(results):
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
    """
    Return user-specific games and statistics for the dashboard.
    """
    user = request.user
    games = Game.objects.filter(user=user)
    
    # Calculate statistics
    total_games = games.count()
    analyzed_games = games.exclude(analysis__isnull=True).count()
    unanalyzed_games = total_games - analyzed_games
    
    # Calculate win/loss/draw statistics
    wins = games.filter(result__iexact='win').count()
    losses = games.filter(result__iexact='loss').count()
    draws = games.filter(result__iexact='draw').count()
    
    # Get recent games
    recent_games = games.order_by('-date_played')[:5].values(
        'id',
        'platform',
        'white',
        'black',
        'opponent',
        'result',
        'date_played',
        'opening_name',
        'analysis'
    )
    
    response_data = {
        'total_games': total_games,
        'analyzed_games': analyzed_games,
        'unanalyzed_games': unanalyzed_games,
        'statistics': {
            'wins': wins,
            'losses': losses,
            'draws': draws,
            'win_rate': round((wins / total_games * 100) if total_games > 0 else 0, 2)
        },
        'recent_games': list(recent_games)
    }
    
    return Response(response_data, status=status.HTTP_200_OK)

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
            return Response({
                'error': 'Error creating checkout session',
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

@api_view(['POST'])
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

@rate_limit(endpoint_type='AUTH')
@api_view(['POST'])
def request_password_reset(request):
    """
    Handle password reset request.
    """
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
    Set CSRF cookie and return it in the response.
    """
    return JsonResponse({
        "detail": "CSRF cookie set",
        "csrfToken": get_token(request)
    })
