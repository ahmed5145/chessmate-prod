"""
Profile-related views for the ChessMate application.
Including profile management, user statistics, and subscription endpoints.
"""

# Standard library imports
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

# Django imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Third-party imports
import stripe

# Local imports - Error handling
from .error_handling import (
    api_error_handler,
    create_error_response,
    create_success_response,
)

# Local imports - Cache utilities
from .cache import CACHE_BACKEND_REDIS, cacheable, invalidate_cache_for

# Local imports - Constants
from .constants import CREDIT_VALUES

# Configure logging
logger = logging.getLogger(__name__)

# Set up Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY

# Get the user model
User = get_user_model()


def get_basic_profile(user):
    """
    Get basic profile information without relying on Profile model import.
    This is a fallback method when the main profile view encounters import errors.
    
    Returns basic user data that can be safely accessed without relying on 
    potentially problematic imports.
    """
    try:
        # Create basic data structure with user information
        response_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "date_joined": user.date_joined.isoformat() if hasattr(user, 'date_joined') else None,
            "is_active": user.is_active,
            "profile": {
                "credits": 0,  # Default value
                "chess_com_username": "",
                "lichess_username": "",
                "preferences": {},
            },
            "subscription": None,
        }
        
        # Attempt to get profile data directly through user relation, avoiding imports
        if hasattr(user, 'profile'):
            try:
                profile = user.profile
                response_data["profile"]["credits"] = getattr(profile, 'credits', 0)
                response_data["profile"]["chess_com_username"] = getattr(profile, 'chess_com_username', "")
                response_data["profile"]["lichess_username"] = getattr(profile, 'lichess_username', "")
                response_data["profile"]["preferences"] = getattr(profile, 'preferences', {})
            except Exception as e:
                logger.error(f"Error accessing profile attributes: {e}")
        
        return response_data
    except Exception as e:
        logger.error(f"Error in get_basic_profile: {e}")
        # Return minimal data if everything else fails
        return {
            "username": user.username if hasattr(user, 'username') else "unknown",
            "email": user.email if hasattr(user, 'email') else "unknown",
            "profile": {"credits": 0},
            "subscription": None,
        }


@api_view(["GET"])
@api_error_handler
def profile_view(request):
    """Get the authenticated user's profile information."""
    try:
        # Check if user is authenticated
        if not request.user.is_authenticated:
            logger.warning(f"Unauthenticated user tried to access profile view")
            return Response(
                {"status": "error", "message": "Authentication credentials were not provided"},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        # Log authentication details for debugging
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        logger.info(f"Auth header present: {bool(auth_header)}")
        logger.info(f"Authenticated user: {request.user.username}")
        
        # Get or create user profile
        try:
            from .models import Profile
            profile, created = Profile.objects.get_or_create(user=request.user)
            if created:
                logger.info(f"Created new profile for user {request.user.username}")
                
            # Prepare user data
            user_data = {
                "id": request.user.id,
                "username": request.user.username,
                "email": request.user.email,
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "date_joined": request.user.date_joined,
                "last_login": request.user.last_login
            }
            
            # Prepare profile data
            profile_data = {
                "bio": getattr(profile, 'bio', ''),
                "chess_com_username": profile.chess_com_username,
                "lichess_username": profile.lichess_username,
                "rating": max(profile.blitz_rating, profile.rapid_rating, profile.classical_rating),  # Use max rating as general rating
                "credits": profile.credits,
                "email_verified": profile.email_verified,
                "created_at": profile.created_at,
                "updated_at": profile.updated_at
            }
            
            # Get subscription info if available
            subscription_data = {}
            try:
                from .models import Subscription
                active_subscription = Subscription.objects.filter(
                    user=request.user, 
                    status='active', 
                    end_date__gt=timezone.now()
                ).first()
                
                if active_subscription:
                    subscription_data = {
                        "tier": active_subscription.tier.name,
                        "price": active_subscription.tier.price,
                        "end_date": active_subscription.end_date,
                        "features": active_subscription.tier.features
                    }
            except Exception as e:
                logger.warning(f"Error getting subscription data: {str(e)}")
                # Continue without subscription data
                
            # Combine all data
            combined_data = {
                "user": user_data,
                "profile": profile_data
            }
            
            if subscription_data:
                combined_data["subscription"] = subscription_data
                
            return Response({"status": "success", "data": combined_data}, status=status.HTTP_200_OK)
            
        except ImportError:
            logger.error("Failed to import Profile model in profile_view")
            # Return a basic response instead of calling fallback_profile_view
            return Response(
                {
                    "status": "success",
                    "data": {
                        "user": {
                            "username": request.user.username,
                            "email": request.user.email,
                        },
                        "profile": {
                            "credits": getattr(request.user.profile, 'credits', 10),
                            "chess_com_username": getattr(request.user.profile, 'chess_com_username', '') or '',
                            "lichess_username": getattr(request.user.profile, 'lichess_username', '') or '',
                            "email_verified": getattr(request.user.profile, 'email_verified', False),
                            "rating": 1200,  # Default rating
                        }
                    }
                },
                status=status.HTTP_200_OK
            )
            
    except Exception as e:
        logger.error(f"Error in profile_view: {str(e)}", exc_info=True)
        # Return a basic response instead of calling fallback_profile_view
        return Response(
            {
                "status": "success",
                "data": {
                    "user": {
                        "username": request.user.username,
                        "email": request.user.email,
                    },
                    "profile": {
                        "credits": getattr(request.user.profile, 'credits', 10),
                        "chess_com_username": getattr(request.user.profile, 'chess_com_username', '') or '',
                        "lichess_username": getattr(request.user.profile, 'lichess_username', '') or '',
                        "email_verified": getattr(request.user.profile, 'email_verified', False),
                        "rating": 1200,  # Default rating
                    }
                }
            },
            status=status.HTTP_200_OK
        )


@api_view(["GET"])
@api_error_handler
def fallback_profile_view(request):
    """
    Fallback profile view for basic profile information.
    Uses standard DRF authentication and error handling.
    """
    logger.info("fallback_profile_view called")
    
    if not request.user.is_authenticated:
        logger.warning("Unauthenticated user tried to access fallback_profile_view")
        return Response(
            {"status": "error", "message": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    try:
        # Log information about the authenticated user
        logger.info(f"User authenticated: {request.user.username}")
        
        # Get user data
        user_data = {
            "username": request.user.username,
            "email": request.user.email,
        }
        
        # Get profile data
        profile_data = {}
        try:
            profile = request.user.profile
            profile_data = {
                "credits": profile.credits,
                "chess_com_username": profile.chess_com_username or "",
                "lichess_username": profile.lichess_username or "",
                "email_verified": profile.email_verified,
                "rating": max(profile.blitz_rating, profile.rapid_rating, profile.classical_rating),
            }
        except Exception as e:
            logger.warning(f"Error getting profile data: {str(e)}")
            profile_data = {"credits": 10, "rating": 1200}  # Provide defaults
        
        # Combine and return the data
        return Response(
            {
                "status": "success",
                "data": {
                    "user": user_data,
                    "profile": profile_data
                }
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error in fallback_profile_view: {str(e)}", exc_info=True)
        return Response(
            {"status": "error", "message": "An error occurred retrieving profile data"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
@api_error_handler
@invalidate_cache_for(key_prefix="user_profile")
def update_profile(request):
    """
    Update user profile information.
    This will invalidate the profile cache.
    """
    try:
        # Import here to avoid circular imports
        from .models import Profile
        from django.contrib.auth.models import User
        
        user = request.user

        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            profile = Profile.objects.create(user=user)

        # Update user info
        if "username" in request.data:
            username = request.data.get("username")
            # Ensure username is unique
            if User.objects.filter(username=username).exclude(id=user.id).exists():
                return Response({"error": "Username already taken"}, status=status.HTTP_400_BAD_REQUEST)
            user.username = username

        if "email" in request.data:
            email = request.data.get("email")
            # Ensure email is unique
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                return Response({"error": "Email already registered"}, status=status.HTTP_400_BAD_REQUEST)
            user.email = email

        if "first_name" in request.data:
            user.first_name = request.data.get("first_name")

        if "last_name" in request.data:
            user.last_name = request.data.get("last_name")

        # Update profile info
        if "chess_com_username" in request.data:
            profile.chess_com_username = request.data.get("chess_com_username")

        if "lichess_username" in request.data:
            profile.lichess_username = request.data.get("lichess_username")

        if "preferences" in request.data:
            preferences = request.data.get("preferences")
            if isinstance(preferences, dict):
                # Update only provided preference fields
                if profile.preferences is None:
                    profile.preferences = {}
                profile.preferences.update(preferences)

        # Save changes
        with transaction.atomic():
            user.save()
            profile.save()

        # Return updated profile data
        return profile_view(request)
    except ImportError as e:
        logger.error(f"Import error in update_profile: {str(e)}")
        return Response({"error": "Profile update feature temporarily unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}")
        return Response({"error": f"Error updating profile: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@api_error_handler
@invalidate_cache_for(key_prefix="user_profile")
def add_credits(request):
    """
    Add credits to the user's profile.
    Invalidates the profile cache.
    """
    try:
        # Import here to avoid circular imports
        from .models import Profile
        
        user = request.user

        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            profile = Profile.objects.create(user=user)

        credit_plan = request.data.get("plan")

        if credit_plan not in CREDIT_VALUES:
            return Response(
                {"error": f'Invalid credit plan. Available plans: {", ".join(CREDIT_VALUES.keys())}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Add credits to profile
        credit_amount = CREDIT_VALUES[credit_plan]
        profile.credits += credit_amount
        profile.last_credit_purchase = timezone.now()
        profile.save()

        # Return updated profile
        return create_success_response(
            data={"credits_added": credit_amount, "total_credits": profile.credits},
            message=f"Successfully added {credit_amount} credits",
        )
    except ImportError as e:
        logger.error(f"Import error in add_credits: {str(e)}")
        return Response({"error": "Credits feature temporarily unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        logger.error(f"Error adding credits: {str(e)}")
        return Response({"error": f"Error adding credits: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@api_error_handler
@cacheable(prefix="user_progress", timeout=60 * 60, cache_backend=CACHE_BACKEND_REDIS)
def user_progress(request):
    """
    Get the user's progress statistics.
    Cached for 1 hour to improve performance.
    """
    # Import here to avoid circular imports
    from .models import Game, GameAnalysis
    
    user = request.user

    # Get total games analyzed
    analysis_count = GameAnalysis.objects.filter(game__user=user).count()

    # Get improvement metrics if available
    recent_games = Game.objects.filter(user=user).order_by("-date_played")[:20]
    
    # Calculate improvement metrics
    improvement_data: dict[str, Any] = {
        "recent_game_count": len(recent_games),
        "accuracy_avg": None,
        "accuracy_trend": None,
        "accuracy_improvement": None,
        "common_mistakes": None,
    }

    # If we have game analyses, calculate accuracy trends
    if analysis_count > 0:
        # Get recent analyses
        recent_analyses = GameAnalysis.objects.filter(game__user=user).order_by("-created_at")[:10]

        # Extract accuracy data
        accuracies = []
        mistakes_counter: dict[str, int] = {}

        for analysis in recent_analyses:
            # Check if analysis data is available
            if not analysis.result or "accuracy" not in analysis.result:
                continue

            accuracies.append(analysis.result.get("accuracy", 0))

            # Count mistake types
            mistakes = analysis.result.get("mistakes", [])
            for mistake in mistakes:
                mistake_type = mistake.get("type", "unknown")
                if mistake_type in mistakes_counter:
                    mistakes_counter[mistake_type] += 1
                else:
                    mistakes_counter[mistake_type] = 1

        # Calculate accuracy trend if we have enough data
        if accuracies:
            accuracy_avg = sum(accuracies) / len(accuracies)
            improvement_data["accuracy_avg"] = round(accuracy_avg, 1)
            
            if len(accuracies) >= 4:
                # Split into two groups to see if there's improvement
                half = len(accuracies) // 2
                first_half = accuracies[:half]
                second_half = accuracies[half:]
                
                first_avg = sum(first_half) / len(first_half)
                second_avg = sum(second_half) / len(second_half)
                
                # Determine trend based on difference
                improvement_data["accuracy_improvement"] = round(second_avg - first_avg, 1)
                
                # Set trend status
                diff = second_avg - first_avg
                if diff > 3:
                    improvement_data["accuracy_trend"] = "improving"
                elif diff < -3:
                    improvement_data["accuracy_trend"] = "declining"
                else:
                    improvement_data["accuracy_trend"] = "stable"

            # Most common mistakes
            if mistakes_counter:
                sorted_mistakes = sorted(mistakes_counter.items(), key=lambda x: x[1], reverse=True)
                improvement_data["common_mistakes"] = [{"type": k, "count": v} for k, v in sorted_mistakes[:3]]

    return create_success_response(data=improvement_data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@api_error_handler
def get_user_statistics(request):
    """
    Get statistics for the logged-in user.
    """
    # Import here to avoid circular imports
    from .models import Game, Profile
    
    user = request.user

    # Retrieve game statistics
    game_count = Game.objects.filter(user=user).count()
    analyzed_game_count = Game.objects.filter(user=user, analysis_status="analyzed").count()

    # Get win/loss/draw statistics
    win_count = Game.objects.filter(user=user, result="win").count()
    loss_count = Game.objects.filter(user=user, result="loss").count()
    draw_count = Game.objects.filter(user=user, result="draw").count()

    # Get platform distribution
    chess_com_count = Game.objects.filter(user=user, platform="chess.com").count()
    lichess_count = Game.objects.filter(user=user, platform="lichess").count()

    # Get analysis statistics
    profile = Profile.objects.get(user=user)

    # Build response data
    statistics = {
        "games": {
            "total": game_count,
            "analyzed": analyzed_game_count,
            "by_result": {"win": win_count, "loss": loss_count, "draw": draw_count},
            "by_platform": {"chess_com": chess_com_count, "lichess": lichess_count},
        },
        "analysis": {"remaining_credits": profile.credits},
        "subscription": {"status": "none"},
    }

    # Add subscription info if available
    try:
        # Import Subscription here to avoid potential circular imports
        from .models import Subscription
        
        try:
            subscription = Subscription.objects.get(user=user, is_active=True)
            subscription_serializer = SubscriptionSerializer(subscription)
            statistics["subscription"] = subscription_serializer.data
        except Subscription.DoesNotExist:
            pass
        except Exception as e:
            logger.error(f"Error fetching subscription for statistics for user {user.id}: {e}")
            statistics["subscription"] = {"status": "error", "message": "Subscription data unavailable"}
    except ImportError as e:
        logger.error(f"Import error when trying to access Subscription model: {e}")
        statistics["subscription"] = {"status": "error", "message": "Subscription feature unavailable"}
    except Exception as e:
        logger.error(f"Unexpected error when trying to access subscription data: {e}")
        statistics["subscription"] = {"status": "error", "message": "Subscription data error"}

    return create_success_response(data=statistics)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@api_error_handler
def get_subscription_tiers(request):
    """
    Get all available subscription tiers.
    """
    try:
        # Import here to avoid circular imports
        from .models import SubscriptionTier
        
        tiers = SubscriptionTier.objects.filter(is_active=True).order_by("price")
        serializer = SubscriptionTierSerializer(tiers, many=True)
        return create_success_response(data=serializer.data)
    except ImportError as e:
        logger.error(f"Import error when trying to access SubscriptionTier model: {e}")
        return create_success_response(data=[], message="Subscription tiers unavailable")
    except Exception as e:
        logger.error(f"Error fetching subscription tiers: {e}")
        return create_success_response(data=[], message="Error fetching subscription tiers")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@api_error_handler
@invalidate_cache_for(key_prefix="user_profile")
def create_subscription(request):
    """
    Create a new subscription for the user.
    """
    try:
        # Import here to avoid circular imports
        from .models import Profile, Subscription, SubscriptionTier
        
        user = request.user
        tier_id = request.data.get("tier_id")
        payment_method_id = request.data.get("payment_method_id")

        # Validate inputs
        if not tier_id or not payment_method_id:
            return Response({"error": "Tier ID and payment method ID are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Check if user already has an active subscription
        existing_subscription = Subscription.objects.filter(user=user, is_active=True).first()

        if existing_subscription:
            return Response({"error": "User already has an active subscription"}, status=status.HTTP_400_BAD_REQUEST)

        # Get the selected tier
        try:
            tier = SubscriptionTier.objects.get(id=tier_id, is_active=True)
        except SubscriptionTier.DoesNotExist:
            return Response({"error": "Subscription tier not found or not active"}, status=status.HTTP_404_NOT_FOUND)

        # Create the subscription in Stripe
        try:
            # First, attach payment method to customer
            customer = stripe.Customer.create(
                email=user.email,
                payment_method=payment_method_id,
                invoice_settings={
                    "default_payment_method": payment_method_id,
                },
            )

            # Create the subscription
            stripe_subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[
                    {
                        "price": tier.stripe_price_id,
                    },
                ],
                expand=["latest_invoice.payment_intent"],
            )

            # Save subscription in database
            with transaction.atomic():
                subscription = Subscription.objects.create(
                    user=user,
                    tier=tier,
                    stripe_subscription_id=stripe_subscription.id,
                    stripe_customer_id=customer.id,
                    plan=tier.name,
                    credits_per_period=tier.credits_per_period,
                    credits_remaining=tier.credits_per_period,
                    start_date=timezone.now(),
                    end_date=timezone.now() + timedelta(days=tier.period_length),
                    is_active=True,
                    status="active",
                    next_billing_date=timezone.now() + timedelta(days=tier.period_length),
                )

                # Credit user's account
                profile = Profile.objects.get(user=user)
                profile.credits += tier.credits_per_period
                profile.save()

                return create_success_response(
                    data={
                        "subscription_id": subscription.id,
                        "stripe_subscription_id": stripe_subscription.id,
                        "customer_id": customer.id,
                        "status": stripe_subscription.status,
                        "plan": tier.name,
                        "credits_per_period": tier.credits_per_period,
                    },
                    message="Subscription created successfully",
                    status_code=status.HTTP_201_CREATED,
                )
        except Exception as e:
            if hasattr(e, 'stripe_error'):
                logger.error(f"Stripe error: {str(e)}")
                return Response({"error": f"Payment error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                logger.error(f"Error creating subscription: {str(e)}")
                return Response({"error": f"Subscription error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
    except ImportError as e:
        logger.error(f"Import error when trying to access subscription models: {e}")
        return Response({"error": "Subscription feature temporarily unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@api_error_handler
@invalidate_cache_for(key_prefix="user_profile")
def cancel_subscription(request):
    """
    Cancel the user's active subscription.
    """
    try:
        # Import here to avoid circular imports
        from .models import Subscription
        
        user = request.user

        # Get user's active subscription
        try:
            subscription = Subscription.objects.get(user=user, is_active=True)
        except Subscription.DoesNotExist:
            return Response({"error": "No active subscription found"}, status=status.HTTP_404_NOT_FOUND)

        # Cancel subscription in Stripe
        try:
            # Cancel in Stripe
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True,
            )

            # Update local subscription
            subscription.status = "canceled"
            subscription.save()

            return create_success_response(
                data={"subscription_id": subscription.stripe_subscription_id, "status": "canceled"},
                message="Subscription successfully canceled",
            )
        except Exception as e:
            if hasattr(e, 'stripe_error'):
                logger.error(f"Stripe error: {str(e)}")
                return Response({"error": f"Error canceling subscription: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                logger.error(f"Error canceling subscription: {str(e)}")
                return Response({"error": f"Subscription error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
    except ImportError as e:
        logger.error(f"Import error when trying to access Subscription model: {e}")
        return Response({"error": "Subscription feature temporarily unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def webhook_handler(request):
    """
    Handle Stripe webhook events.
    """
    try:
        # Get payload and verify signature
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)

        # Process the event
        event_type = event["type"]
        
        # Handle different event types
        if event_type == "invoice.payment_succeeded":
            handle_subscription_payment(event)
        elif event_type == "customer.subscription.deleted":
            handle_subscription_canceled(event)
            
        return Response(status=status.HTTP_200_OK)
    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        return Response(status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        if hasattr(e, 'sig_verification_error'):
            logger.error(f"Invalid signature: {str(e)}")
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            logger.error(f"Webhook error: {str(e)}")
            return Response(status=status.HTTP_400_BAD_REQUEST)


def handle_subscription_payment(event):
    """
    Handle successful subscription payment.
    """
    try:
        # Import here to avoid circular imports
        from .models import Profile, Subscription
        
        invoice = event["data"]["object"]
        subscription_id = invoice["subscription"]

        # Find matching subscription in database
        try:
            subscription = Subscription.objects.get(stripe_subscription_id=subscription_id, is_active=True)

            # Extend subscription end date and reset credits
            subscription.end_date = timezone.now() + timedelta(days=subscription.tier.period_length)
            subscription.next_billing_date = subscription.end_date
            subscription.credits_remaining = subscription.credits_per_period
            subscription.last_credit_reset = timezone.now()
            subscription.save()

            # Add credits to user's account
            profile = Profile.objects.get(user=subscription.user)
            profile.credits += subscription.credits_per_period
            profile.save()

            logger.info(f"Subscription {subscription_id} renewed successfully")
        except Subscription.DoesNotExist:
            logger.warning(f"Subscription {subscription_id} not found for payment {invoice['id']}")
        except Profile.DoesNotExist:
            logger.warning(f"Profile not found for user from subscription {subscription_id}")
        except Exception as e:
            logger.error(f"Error processing subscription payment details: {str(e)}")
    except ImportError as e:
        logger.error(f"Import error in handle_subscription_payment: {str(e)}")
    except Exception as e:
        logger.error(f"General error handling subscription payment: {str(e)}")


def handle_subscription_canceled(event):
    """
    Handle subscription cancellation.
    """
    try:
        # Import here to avoid circular imports
        from .models import Subscription
        
        subscription_obj = event["data"]["object"]
        subscription_id = subscription_obj["id"]

        # Find matching subscription in database
        try:
            subscription = Subscription.objects.get(stripe_subscription_id=subscription_id, is_active=True)

            # Mark subscription as inactive
            subscription.is_active = False
            subscription.status = "canceled"
            subscription.end_date = timezone.now()
            subscription.save()

            logger.info(f"Subscription {subscription_id} canceled successfully")
        except Subscription.DoesNotExist:
            logger.warning(f"Subscription {subscription_id} not found for cancellation")
        except Exception as e:
            logger.error(f"Error processing subscription cancellation details: {str(e)}")
    except ImportError as e:
        logger.error(f"Import error in handle_subscription_canceled: {str(e)}")
    except Exception as e:
        logger.error(f"General error handling subscription cancellation: {str(e)}")


@api_view(["GET"])
@api_error_handler
def minimal_profile_view(request):
    """
    A minimal profile view that manually handles authentication.
    This serves as a reliable endpoint for clients to get basic user profile info.
    """
    # Log request details for debugging
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    logger.info(f"minimal_profile_view called with auth header: {bool(auth_header)}")
    
    try:
        # First check if DRF authentication worked
        if request.user.is_authenticated:
            logger.info(f"User authenticated via DRF: {request.user.username}")
            user = request.user
        # If not, try to manually decode the token
        elif auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            logger.info(f"Attempting manual token authentication")
            
            from rest_framework_simplejwt.tokens import AccessToken
            from django.contrib.auth.models import User
            
            try:
                # Decode the token
                decoded_token = AccessToken(token)
                user_id = decoded_token['user_id']
                
                # Fetch the user
                user = User.objects.get(id=user_id)
                logger.info(f"Manual token authentication successful for user: {user.username}")
            except Exception as e:
                logger.warning(f"Manual token authentication failed: {str(e)}")
                return Response(
                    {"status": "error", "message": "Invalid authentication token"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        else:
            logger.warning("No authentication provided")
            return Response(
                {"status": "error", "message": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # At this point we have a valid user
        # Construct basic user data
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "date_joined": user.date_joined.isoformat() if hasattr(user, 'date_joined') else None,
        }
        
        # Try to get profile data if available
        profile_data = {
            "credits": 10,  # Default value if we can't get profile
            "chess_com_username": "",
            "lichess_username": "",
            "email_verified": False,
            "rating": 1200,  # Default rating
        }
        
        try:
            if hasattr(user, 'profile'):
                profile = user.profile
                profile_data = {
                    "credits": getattr(profile, 'credits', 10),
                    "chess_com_username": getattr(profile, 'chess_com_username', ""),
                    "lichess_username": getattr(profile, 'lichess_username', ""),
                    "email_verified": getattr(profile, 'email_verified', False),
                    "bullet_rating": getattr(profile, 'bullet_rating', 1200),
                    "blitz_rating": getattr(profile, 'blitz_rating', 1200),
                    "rapid_rating": getattr(profile, 'rapid_rating', 1200),
                    "classical_rating": getattr(profile, 'classical_rating', 1200),
                }
                # Add computed rating field that matches the Profile.rating property
                profile_data["rating"] = max(
                    profile_data["bullet_rating"],
                    profile_data["blitz_rating"],
                    profile_data["rapid_rating"],
                    profile_data["classical_rating"]
                )
        except Exception as e:
            logger.warning(f"Error retrieving profile for user {user.username}: {str(e)}")
            # Continue with default profile data
        
        # Log success for monitoring
        logger.info(f"Successfully retrieved minimal profile for user {user.username}")
        
        # Return combined data
        return Response(
            {
                "status": "success",
                "data": {
                    "user": user_data,
                    "profile": profile_data
                }
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error in minimal_profile_view: {str(e)}", exc_info=True)
        return Response(
            {"status": "error", "message": "An error occurred retrieving profile data"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
