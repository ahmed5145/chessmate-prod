"""
Idempotent Stripe Checkout → profile credits fulfillment.
Used by confirm-purchase API and Stripe webhooks.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F

from .models import Profile, Transaction
from .payment import PaymentProcessor

logger = logging.getLogger(__name__)


class CreditFulfillmentError(Exception):
    """Raised when checkout session cannot be applied to credits."""


def fulfill_checkout_session(
    *,
    session_id: str,
    user,
    payment_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Add credits for a paid Stripe Checkout session (idempotent).

    Returns dict with keys: credits, credits_added, already_confirmed.
    """
    session_id = (session_id or "").strip()
    if not session_id:
        raise CreditFulfillmentError("session_id is required")

    if payment_data is None:
        payment_data = PaymentProcessor.verify_payment(session_id)
    if not payment_data:
        raise CreditFulfillmentError("Payment not completed")

    metadata_user_id = payment_data.get("user_id")
    if metadata_user_id is not None and str(metadata_user_id) != str(user.id):
        raise CreditFulfillmentError("Payment belongs to a different account")

    credits_to_add = int(payment_data.get("credits") or 0)
    if credits_to_add <= 0:
        raise CreditFulfillmentError("Invalid credit amount on payment")

    with transaction.atomic():
        existing = Transaction.objects.filter(
            user=user,
            stripe_payment_id=session_id,
            status="completed",
        ).first()
        if existing:
            profile = Profile.objects.get(user=user)
            return {
                "credits": profile.credits,
                "credits_added": 0,
                "already_confirmed": True,
            }

        profile, _ = Profile.objects.select_for_update().get_or_create(user=user)
        profile.credits = F("credits") + credits_to_add
        profile.save(update_fields=["credits"])
        profile.refresh_from_db(fields=["credits"])

        amount_dollars = float(payment_data.get("amount") or 0) / 100.0
        Transaction.objects.create(
            user=user,
            transaction_type="purchase",
            amount=amount_dollars,
            credits=credits_to_add,
            status="completed",
            stripe_payment_id=session_id,
        )

    logger.info(
        "Fulfilled checkout session %s: +%s credits for user %s",
        session_id,
        credits_to_add,
        user.id,
    )
    return {
        "credits": profile.credits,
        "credits_added": credits_to_add,
        "already_confirmed": False,
    }


def fulfill_checkout_from_webhook_event(
    event: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Apply credits for checkout.session.completed (mode=payment).
    Returns fulfillment result or None if event was ignored.
    """
    if event.get("type") != "checkout.session.completed":
        return None

    session = event.get("data", {}).get("object") or {}
    if session.get("mode") != "payment":
        return None
    if session.get("payment_status") != "paid":
        return None

    session_id = session.get("id")
    metadata = session.get("metadata") or {}
    user_id = metadata.get("user_id")
    if not user_id:
        logger.warning(
            "checkout.session.completed missing user_id metadata: %s", session_id
        )
        return None

    User = get_user_model()
    try:
        user = User.objects.get(pk=int(user_id))
    except (User.DoesNotExist, TypeError, ValueError):
        logger.warning("checkout.session.completed user_id=%s not found", user_id)
        return None

    payment_data = {
        "amount": session.get("amount_total"),
        "credits": int(metadata.get("credits") or 0),
        "user_id": str(user_id),
        "package_id": metadata.get("package_id"),
    }
    return fulfill_checkout_session(
        session_id=session_id,
        user=user,
        payment_data=payment_data,
    )
