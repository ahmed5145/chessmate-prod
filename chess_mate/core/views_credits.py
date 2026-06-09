"""
Credit balance, Stripe checkout, and webhooks.
"""

import logging

import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .abuse_limits import (
    check_checkout_allowed,
    checkout_limit_response,
    record_checkout_session,
)
from .credit_fulfillment import (
    CreditFulfillmentError,
    fulfill_checkout_from_webhook_event,
    fulfill_checkout_session,
)
from .credit_packages import credit_model_for_api, get_package, list_packages_for_api
from .decorators import rate_limit
from .payment import PaymentProcessor

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def credits_balance_view(request):
    """GET /api/v1/credits/ — current credit balance."""
    from .models import Profile

    profile, _ = Profile.objects.get_or_create(user=request.user)
    return Response({"credits": profile.credits or 0}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def credits_packages_view(request):
    """GET /api/v1/credits/packages/ — purchasable packages with batch framing."""
    credit_model = credit_model_for_api()
    return Response(
        {
            "packages": list_packages_for_api(),
            **credit_model,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@rate_limit(endpoint_type="CREDITS")
def purchase_credits_checkout_view(request):
    """
    POST /api/v1/purchase-credits/

    Body: { "package_id": "basic" | "pro" | "premium" }
    Returns Stripe Checkout URL.
    """
    package_id = request.data.get("package_id")
    package = get_package(package_id)
    if not package:
        return Response({"detail": "Invalid package selection."}, status=status.HTTP_400_BAD_REQUEST)

    if not getattr(settings, "STRIPE_SECRET_KEY", ""):
        return Response(
            {"detail": "Payments are not configured on this server."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    checkout_allowed, retry_after = check_checkout_allowed(request.user)
    if not checkout_allowed:
        return checkout_limit_response(retry_after)

    try:
        session = PaymentProcessor.create_checkout_session(
            user_id=request.user.id,
            package_id=package["id"],
            amount=package["price_cents"],
            credits=package["credits"],
        )
    except Exception as exc:
        logger.warning("Stripe checkout failed for user %s: %s", request.user.id, exc)
        return Response(
            {"detail": "Could not start checkout. Please try again later."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    record_checkout_session(request.user)
    return Response(
        {"checkout_url": session.url, "session_id": session.id},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def confirm_purchase_view(request):
    """
    POST /api/v1/confirm-purchase/

    Body: { "payment_id": "<stripe_checkout_session_id>" }
    """
    session_id = request.data.get("payment_id") or request.data.get("session_id")
    if not session_id:
        return Response({"detail": "payment_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    if not getattr(settings, "STRIPE_SECRET_KEY", ""):
        return Response(
            {"detail": "Payments are not configured on this server."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        result = fulfill_checkout_session(session_id=session_id, user=request.user)
    except CreditFulfillmentError as exc:
        logger.warning("Confirm purchase failed for user %s: %s", request.user.id, exc)
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        logger.warning(
            "Stripe verify failed for user %s session %s: %s",
            request.user.id,
            session_id,
            exc,
        )
        return Response({"detail": "Could not verify payment."}, status=status.HTTP_400_BAD_REQUEST)

    return Response(result, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def stripe_webhook_view(request):
    """
    POST /api/v1/webhooks/stripe/

    Stripe Dashboard → Webhooks → checkout.session.completed
    Signing secret → STRIPE_WEBHOOK_SECRET on EB.
    """
    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "").strip()
    if not webhook_secret:
        logger.warning("Stripe webhook received but STRIPE_WEBHOOK_SECRET is not configured")
        return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError as exc:
        logger.error("Stripe webhook invalid payload: %s", exc)
        return Response(status=status.HTTP_400_BAD_REQUEST)
    except stripe.error.SignatureVerificationError as exc:
        logger.error("Stripe webhook invalid signature: %s", exc)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    try:
        result = fulfill_checkout_from_webhook_event(event)
        if result:
            logger.info(
                "Webhook fulfilled session for user credits_added=%s",
                result.get("credits_added"),
            )
    except CreditFulfillmentError as exc:
        logger.warning("Webhook fulfillment skipped: %s", exc)
    except Exception as exc:
        logger.exception("Webhook fulfillment error: %s", exc)
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(status=status.HTTP_200_OK)


stripe_webhook_view = csrf_exempt(stripe_webhook_view)
