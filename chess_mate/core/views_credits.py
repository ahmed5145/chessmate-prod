"""
Credit balance and Stripe checkout (batch-coach aligned packages).
"""

import logging

from django.conf import settings
from django.db import transaction
from django.db.models import F
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .credit_packages import get_package, list_packages_for_api
from .models import Profile, Transaction
from .payment import PaymentProcessor

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def credits_balance_view(request):
    """GET /api/v1/credits/ — current credit balance."""
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return Response({"credits": profile.credits or 0}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def credits_packages_view(request):
    """GET /api/v1/credits/packages/ — purchasable packages with batch framing."""
    return Response(
        {
            "packages": list_packages_for_api(),
            "credits_per_imported_game": 1,
            "batch_credits_per_game": int(getattr(settings, "BATCH_CREDITS_PER_GAME", 0)),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
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

    return Response({"checkout_url": session.url, "session_id": session.id}, status=status.HTTP_200_OK)


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
        payment_data = PaymentProcessor.verify_payment(session_id)
    except Exception as exc:
        logger.warning("Stripe verify failed for user %s session %s: %s", request.user.id, session_id, exc)
        return Response({"detail": "Could not verify payment."}, status=status.HTTP_400_BAD_REQUEST)

    if not payment_data:
        return Response(
            {"detail": "Payment not completed yet. Wait a few seconds and refresh, or contact support."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    metadata_user_id = payment_data.get("user_id")
    if metadata_user_id is not None and str(metadata_user_id) != str(request.user.id):
        logger.warning(
            "Stripe session %s user_id=%s does not match request user %s",
            session_id,
            metadata_user_id,
            request.user.id,
        )
        return Response({"detail": "This payment belongs to a different account."}, status=status.HTTP_403_FORBIDDEN)

    credits_to_add = int(payment_data.get("credits") or 0)
    if credits_to_add <= 0:
        return Response({"detail": "Invalid credit amount on payment."}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        existing = Transaction.objects.filter(
            user=request.user,
            stripe_payment_id=session_id,
            status="completed",
        ).first()
        if existing:
            profile = Profile.objects.get(user=request.user)
            return Response(
                {"credits": profile.credits, "credits_added": 0, "already_confirmed": True},
                status=status.HTTP_200_OK,
            )

        profile, _ = Profile.objects.select_for_update().get_or_create(user=request.user)
        profile.credits = F("credits") + credits_to_add
        profile.save(update_fields=["credits"])
        profile.refresh_from_db(fields=["credits"])

        amount_dollars = float(payment_data.get("amount") or 0) / 100.0
        Transaction.objects.create(
            user=request.user,
            transaction_type="purchase",
            amount=amount_dollars,
            credits=credits_to_add,
            status="completed",
            stripe_payment_id=session_id,
        )

    return Response(
        {"credits": profile.credits, "credits_added": credits_to_add},
        status=status.HTTP_200_OK,
    )
