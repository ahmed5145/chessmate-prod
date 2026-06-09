"""
Payment processing module for ChessMate application.
"""

try:
    import stripe
except ImportError:
    raise ImportError("Failed to import stripe. Please ensure stripe is installed: pip install stripe")

from django.conf import settings

from .credit_packages import CREDIT_PACKAGES as _PACKAGES

# Back-compat alias for imports expecting payment.CREDIT_PACKAGES
CREDIT_PACKAGES = {
    key: {
        "name": value["name"],
        "credits": value["credits"],
        "price": value["price_cents"],
    }
    for key, value in _PACKAGES.items()
}


def _frontend_base_url() -> str:
    return getattr(settings, "FRONTEND_URL", "").rstrip("/") or "http://localhost:3000"


def _payment_success_url() -> str:
    explicit = getattr(settings, "PAYMENT_SUCCESS_URL", "").strip()
    if explicit:
        return explicit if "{CHECKOUT_SESSION_ID}" in explicit else f"{explicit}?session_id={{CHECKOUT_SESSION_ID}}"
    return f"{_frontend_base_url()}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"


def _payment_cancel_url() -> str:
    explicit = getattr(settings, "PAYMENT_CANCEL_URL", "").strip()
    if explicit:
        return explicit
    return f"{_frontend_base_url()}/credits"


class PaymentProcessor:
    @staticmethod
    def create_checkout_session(user_id, package_id, amount, credits):
        """Create a Stripe checkout session for credit purchase."""
        if not settings.STRIPE_SECRET_KEY:
            raise ValueError("Stripe secret key not configured")

        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY

            # Convert amount to cents if it's in dollars
            amount_in_cents = int(amount * 100) if amount < 100 else amount

            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "unit_amount": amount_in_cents,
                            "product_data": {
                                "name": f"ChessMate Credits - {credits} credits",
                                "description": f"Purchase {credits} analysis credits for ChessMate",
                            },
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=_payment_success_url(),
                cancel_url=_payment_cancel_url(),
                metadata={
                    "user_id": str(user_id),
                    "package_id": str(package_id),
                    "credits": str(credits),
                },
            )
            return checkout_session
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
        except Exception as e:
            raise Exception(f"Error creating checkout session: {str(e)}")

    @staticmethod
    def verify_payment(session_id):
        """Verify a payment session."""
        if not settings.STRIPE_SECRET_KEY:
            raise ValueError("Stripe secret key not configured")

        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                metadata = session.metadata or {}
                return {
                    "amount": session.amount_total,
                    "credits": int(metadata.get("credits") or 0),
                    "user_id": metadata.get("user_id"),
                    "package_id": metadata.get("package_id"),
                }
            return None
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
        except Exception as e:
            raise Exception(f"Error verifying payment: {str(e)}")
