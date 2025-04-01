"""
Profile-related views for the ChessMate application.
Including profile management, user statistics, and subscription endpoints.
"""

# Standard library imports
import logging
from typing import Dict, Any, Optional

# Django imports
from django.conf import settings
from django.utils import timezone
from django.db import transaction

# Third-party imports
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import stripe

# Local application imports
from .models import Profile, Game, GameAnalysis, Subscription, SubscriptionTier
from .serializers import ProfileSerializer, SubscriptionSerializer

# Configure logging
logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    """
    Retrieve the profile for the logged-in user.
    """
    try:
        user = request.user
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            # Create profile if it doesn't exist
            profile = Profile.objects.create(
                user=user,
                credits=settings.DEFAULT_CREDITS,
                analysis_count=0
            )
            
        serializer = ProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error retrieving user profile: {str(e)}")
        return Response(
            {"error": "Failed to retrieve user profile"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_user_profile(request):
    """
    Update the profile for the logged-in user.
    """
    try:
        user = request.user
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            return Response(
                {"error": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Only allow updating certain fields
        allowed_fields = ["chess_com_username", "lichess_username", "elo_rating", "preferred_platform"]
        
        # Filter request data to only include allowed fields
        filtered_data = {}
        for field in allowed_fields:
            if field in request.data:
                filtered_data[field] = request.data[field]
                
        # Update profile with filtered data
        serializer = ProfileSerializer(profile, data=filtered_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        return Response(
            {"error": "Failed to update user profile"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_statistics(request):
    """
    Get statistics for the logged-in user.
    """
    try:
        user = request.user
        
        # Retrieve game statistics
        game_count = Game.objects.filter(user=user).count()
        analyzed_game_count = Game.objects.filter(
            user=user, 
            analysis_status='analyzed'
        ).count()
        
        # Get win/loss/draw statistics
        win_count = Game.objects.filter(
            user=user, 
            result='win'
        ).count()
        loss_count = Game.objects.filter(
            user=user, 
            result='loss'
        ).count()
        draw_count = Game.objects.filter(
            user=user, 
            result='draw'
        ).count()
        
        # Get platform distribution
        chess_com_count = Game.objects.filter(
            user=user, 
            platform='chess.com'
        ).count()
        lichess_count = Game.objects.filter(
            user=user, 
            platform='lichess'
        ).count()
        
        # Get analysis statistics
        profile = Profile.objects.get(user=user)
        
        # Build response data
        statistics = {
            "games": {
                "total": game_count,
                "analyzed": analyzed_game_count,
                "by_result": {
                    "win": win_count,
                    "loss": loss_count,
                    "draw": draw_count
                },
                "by_platform": {
                    "chess_com": chess_com_count,
                    "lichess": lichess_count
                }
            },
            "analysis": {
                "total_count": profile.analysis_count,
                "remaining_credits": profile.credits
            },
            "subscription": {
                "status": "none"
            }
        }
        
        # Add subscription info if available
        try:
            subscription = Subscription.objects.get(user=user, active=True)
            subscription_serializer = SubscriptionSerializer(subscription)
            statistics["subscription"] = subscription_serializer.data
        except Subscription.DoesNotExist:
            pass
            
        return Response(statistics, status=status.HTTP_200_OK)
    except Profile.DoesNotExist:
        return Response(
            {"error": "User profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error fetching user statistics: {str(e)}")
        return Response(
            {"error": "Failed to fetch user statistics"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_subscription_tiers(request):
    """
    Get all available subscription tiers.
    """
    try:
        tiers = SubscriptionTier.objects.filter(active=True).order_by('price')
        result = []
        
        for tier in tiers:
            tier_data = {
                "id": tier.id,
                "name": tier.name,
                "description": tier.description,
                "price": tier.price,
                "credits_per_month": tier.credits_per_month,
                "features": tier.features
            }
            result.append(tier_data)
            
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error fetching subscription tiers: {str(e)}")
        return Response(
            {"error": "Failed to fetch subscription tiers"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_subscription(request):
    """
    Create a new subscription for the user.
    """
    try:
        user = request.user
        tier_id = request.data.get('tier_id')
        payment_method_id = request.data.get('payment_method_id')
        
        # Validate inputs
        if not tier_id or not payment_method_id:
            return Response(
                {"error": "Tier ID and payment method ID are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check if user already has an active subscription
        existing_subscription = Subscription.objects.filter(
            user=user,
            active=True
        ).first()
        
        if existing_subscription:
            return Response(
                {"error": "User already has an active subscription"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Get the selected tier
        try:
            tier = SubscriptionTier.objects.get(id=tier_id, active=True)
        except SubscriptionTier.DoesNotExist:
            return Response(
                {"error": "Subscription tier not found or not active"},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Create the subscription in Stripe
        try:
            # First, attach payment method to customer
            customer = stripe.Customer.create(
                email=user.email,
                payment_method=payment_method_id,
                invoice_settings={
                    'default_payment_method': payment_method_id,
                },
            )
            
            # Create the subscription
            stripe_subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[
                    {
                        'price': tier.stripe_price_id,
                    },
                ],
                expand=['latest_invoice.payment_intent'],
            )
            
            # Save subscription in database
            with transaction.atomic():
                subscription = Subscription.objects.create(
                    user=user,
                    tier=tier,
                    stripe_subscription_id=stripe_subscription.id,
                    stripe_customer_id=customer.id,
                    start_date=timezone.now(),
                    end_date=timezone.now() + timezone.timedelta(days=30),
                    active=True
                )
                
                # Credit user's account
                profile = Profile.objects.get(user=user)
                profile.credits += tier.credits_per_month
                profile.save()
                
                return Response(
                    {
                        "subscription_id": subscription.id,
                        "stripe_subscription_id": stripe_subscription.id,
                        "customer_id": customer.id,
                        "status": stripe_subscription.status,
                        "current_period_end": stripe_subscription.current_period_end,
                        "credits_added": tier.credits_per_month,
                        "total_credits": profile.credits
                    },
                    status=status.HTTP_201_CREATED
                )
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {str(e)}")
            return Response(
                {"error": f"Payment error: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        return Response(
            {"error": f"Failed to create subscription: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    """
    Cancel the user's active subscription.
    """
    try:
        user = request.user
        
        # Get user's active subscription
        try:
            subscription = Subscription.objects.get(user=user, active=True)
        except Subscription.DoesNotExist:
            return Response(
                {"error": "No active subscription found"},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Cancel subscription in Stripe
        try:
            stripe.Subscription.delete(subscription.stripe_subscription_id)
            
            # Update subscription in database
            subscription.active = False
            subscription.end_date = timezone.now()
            subscription.save()
            
            return Response(
                {"message": "Subscription successfully canceled"},
                status=status.HTTP_200_OK
            )
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {str(e)}")
            return Response(
                {"error": f"Error canceling subscription: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        logger.error(f"Error canceling subscription: {str(e)}")
        return Response(
            {"error": f"Failed to cancel subscription: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_credits(request):
    """
    Add credits to the user's account via one-time payment.
    """
    try:
        user = request.user
        credit_amount = int(request.data.get('credit_amount', 0))
        payment_method_id = request.data.get('payment_method_id')
        
        # Validate inputs
        if credit_amount <= 0 or not payment_method_id:
            return Response(
                {"error": "Valid credit amount and payment method ID are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Calculate price (each credit costs $1)
        amount = credit_amount * 100  # in cents
        
        # Process payment
        try:
            # First, attach payment method to customer
            # If customer exists, retrieve it, otherwise create new
            try:
                profile = Profile.objects.get(user=user)
                if profile.stripe_customer_id:
                    customer = stripe.Customer.retrieve(profile.stripe_customer_id)
                    # Attach the new payment method
                    stripe.PaymentMethod.attach(
                        payment_method_id,
                        customer=customer.id
                    )
                else:
                    # Create new customer
                    customer = stripe.Customer.create(
                        email=user.email,
                        payment_method=payment_method_id
                    )
                    # Save customer ID to profile
                    profile.stripe_customer_id = customer.id
                    profile.save()
            except Profile.DoesNotExist:
                # Create new customer
                customer = stripe.Customer.create(
                    email=user.email,
                    payment_method=payment_method_id
                )
                # Create profile
                profile = Profile.objects.create(
                    user=user,
                    credits=settings.DEFAULT_CREDITS,
                    stripe_customer_id=customer.id
                )
                
            # Create payment intent
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency='usd',
                customer=customer.id,
                payment_method=payment_method_id,
                confirm=True,
                description=f"Purchase of {credit_amount} credits"
            )
            
            # Add credits to user's account if payment successful
            if payment_intent.status == 'succeeded':
                with transaction.atomic():
                    profile.credits += credit_amount
                    profile.save()
                    
                    return Response({
                        "message": f"Successfully added {credit_amount} credits",
                        "total_credits": profile.credits,
                        "payment_intent_id": payment_intent.id
                    }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": "Payment processing failed",
                    "payment_intent_status": payment_intent.status
                }, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {str(e)}")
            return Response(
                {"error": f"Payment error: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        logger.error(f"Error adding credits: {str(e)}")
        return Response(
            {"error": f"Failed to add credits: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def webhook_handler(request):
    """
    Handle Stripe webhook events.
    """
    try:
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            logger.error(f"Invalid payload: {str(e)}")
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {str(e)}")
            return Response(status=status.HTTP_400_BAD_REQUEST)
            
        # Handle the event
        if event['type'] == 'invoice.payment_succeeded':
            handle_subscription_payment(event)
        elif event['type'] == 'customer.subscription.deleted':
            handle_subscription_canceled(event)
            
        return Response(status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}")
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
def handle_subscription_payment(event):
    """
    Handle successful subscription payment.
    """
    try:
        invoice = event['data']['object']
        subscription_id = invoice['subscription']
        
        # Find matching subscription in database
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=subscription_id,
                active=True
            )
            
            # Extend subscription end date
            subscription.end_date = timezone.now() + timezone.timedelta(days=30)
            subscription.save()
            
            # Add credits to user's account
            profile = Profile.objects.get(user=subscription.user)
            profile.credits += subscription.tier.credits_per_month
            profile.save()
            
            logger.info(f"Subscription {subscription_id} renewed successfully")
        except Subscription.DoesNotExist:
            logger.warning(f"Subscription {subscription_id} not found for payment {invoice['id']}")
    except Exception as e:
        logger.error(f"Error handling subscription payment: {str(e)}")
        
def handle_subscription_canceled(event):
    """
    Handle subscription cancellation.
    """
    try:
        subscription_obj = event['data']['object']
        subscription_id = subscription_obj['id']
        
        # Find matching subscription in database
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=subscription_id,
                active=True
            )
            
            # Mark subscription as inactive
            subscription.active = False
            subscription.end_date = timezone.now()
            subscription.save()
            
            logger.info(f"Subscription {subscription_id} canceled successfully")
        except Subscription.DoesNotExist:
            logger.warning(f"Subscription {subscription_id} not found for cancellation")
    except Exception as e:
        logger.error(f"Error handling subscription cancellation: {str(e)}") 