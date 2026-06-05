"""URL routes for credit balance and Stripe checkout."""

from django.urls import path

from . import views_credits

urlpatterns = [
    path("", views_credits.credits_balance_view, name="credits-balance"),
    path("packages/", views_credits.credits_packages_view, name="credits-packages"),
    path("purchase/", views_credits.purchase_credits_checkout_view, name="purchase-credits-checkout"),
    path("confirm/", views_credits.confirm_purchase_view, name="confirm-purchase"),
]
