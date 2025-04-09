"""
Serializers for the ChessMate application.
These serializers convert Django models to JSON and vice versa.
"""

from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Game, GameAnalysis, Profile, Subscription, SubscriptionTier


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the User model."""

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "date_joined"]
        read_only_fields = ["id", "date_joined"]


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer for the Profile model."""

    class Meta:
        model = Profile
        fields = [
            "id",
            "credits",
            "bullet_rating",
            "blitz_rating",
            "rapid_rating",
            "classical_rating",
            "chess_com_username",
            "lichess_username",
            "email_verified",
            "email_verification_token",
            "email_verification_sent_at",
            "email_verified_at",
            "preferences",
            "created_at",
            "updated_at",
            "rating_history",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "email_verified", "email_verified_at"]
        extra_kwargs = {
            'email_verification_token': {'write_only': True},
        }


class GameSerializer(serializers.ModelSerializer):
    """Serializer for the Game model."""

    class Meta:
        model = Game
        fields = [
            "id",
            "platform",
            "game_id",
            "result",
            "white",
            "black",
            "opponent",
            "opening_name",
            "date_played",
            "time_control",
            "time_control_type",
            "eco_code",
            "white_elo",
            "black_elo",
            "analysis_status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class GameAnalysisSerializer(serializers.ModelSerializer):
    """Serializer for the GameAnalysis model."""

    class Meta:
        model = GameAnalysis
        fields = [
            "id",
            "game",
            "metrics",
            "phase_metrics",
            "time_metrics",
            "tactical_metrics",
            "positional_metrics",
            "feedback",
            "time_control_feedback",
            "study_plan",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SubscriptionTierSerializer(serializers.ModelSerializer):
    """Serializer for the SubscriptionTier model."""

    class Meta:
        model = SubscriptionTier
        fields = [
            "id",
            "name",
            "slug",
            "price",
            "description",
            "features",
            "credits_per_period",
            "period_length",
            "is_active",
        ]
        read_only_fields = ["id"]


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for the Subscription model."""

    tier = SubscriptionTierSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "user",
            "tier",
            "plan",
            "status",
            "start_date",
            "end_date",
            "next_billing_date",
            "is_active",
            "credits_per_period",
            "credits_remaining",
            "last_credit_reset",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "user", "tier"]
