"""
Tests for feedback views.
"""

import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from .. import feedback_views
from ..models import AiFeedback, Game, GameAnalysis, Profile


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_user():
    user = User.objects.create_user(username="testuser", email="test@example.com", password="testpassword123")
    Profile.objects.create(
        user=user, email_verified=True, credits=100, chess_com_username="testuser", lichess_username="testuser_lichess"
    )
    return user


@pytest.fixture
def authenticated_client(api_client, test_user):
    url = reverse("login")
    data = {"email": "test@example.com", "password": "testpassword123"}
    response = api_client.post(url, data, format="json")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return api_client


@pytest.fixture
def test_game(test_user):
    game = Game.objects.create(
        user=test_user,
        platform="chess.com",
        white="testuser",
        black="opponent",
        result="win",
        pgn='[Event "Test Game"]\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6',
        opening_name="Ruy Lopez",
        date_played=timezone.now() - timedelta(days=1),
        analysis_status="analyzed",
        analysis={
            "analysis_results": {
                "summary": {
                    "user_accuracy": 85.5,
                    "key_moments": [
                        {
                            "move": 10,
                            "type": "missed_tactic",
                            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                        },
                        {
                            "move": 15,
                            "type": "blunder",
                            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                        },
                    ],
                },
                "moves": [{"move_number": 1, "move": "e4", "eval": 0.3}, {"move_number": 2, "move": "e5", "eval": 0.2}],
            }
        },
    )

    return game


@pytest.fixture
def test_feedback(test_user, test_game):
    feedback = AiFeedback.objects.create(
        user=test_user,
        game=test_game,
        content={
            "summary": "You played a strong game overall.",
            "opening_advice": "Your opening was solid, but consider developing your knight earlier.",
            "middlegame_advice": "Good tactical awareness, but missed an opportunity on move 10.",
            "endgame_advice": "Excellent endgame technique, converting your advantage efficiently.",
            "key_moments": [
                {
                    "move_number": 10,
                    "description": "Missed tactic that would have given a significant advantage.",
                    "recommendation": "Nxd5 would have won material.",
                },
                {
                    "move_number": 15,
                    "description": "Minor inaccuracy allowing counterplay.",
                    "recommendation": "Consider Bd3 to maintain control.",
                },
            ],
            "improvement_areas": ["Tactical awareness in complex positions", "Knight maneuvers in closed positions"],
        },
        model_used="gpt-4-turbo",
        credits_used=25,
        created_at=timezone.now(),
        rating=None,
    )

    return feedback


@pytest.mark.django_db
class TestFeedbackViews:
    def test_generate_ai_feedback(self, authenticated_client, test_user, test_game):
        # Initial credits
        initial_credits = test_user.profile.credits
        credits_cost = 25  # Assuming this is the cost

        # Mock the OpenAI API client
        mock_feedback_content = {
            "summary": "You played a strong game overall.",
            "opening_advice": "Your opening was solid, but consider developing your knight earlier.",
            "middlegame_advice": "Good tactical awareness, but missed an opportunity on move 10.",
            "endgame_advice": "Excellent endgame technique, converting your advantage efficiently.",
            "key_moments": [
                {
                    "move_number": 10,
                    "description": "Missed tactic that would have given a significant advantage.",
                    "recommendation": "Nxd5 would have won material.",
                }
            ],
            "improvement_areas": ["Tactical awareness in complex positions", "Knight maneuvers in closed positions"],
        }

        with patch.object(
            feedback_views, "generate_game_feedback", return_value=(mock_feedback_content, "gpt-4-turbo", credits_cost)
        ) as mock_generate:
            url = reverse("generate_ai_feedback", args=[test_game.id])
            response = authenticated_client.post(url)

            assert response.status_code == status.HTTP_201_CREATED

            # Verify feedback was created in the database
            assert AiFeedback.objects.filter(game=test_game).exists()

            feedback = AiFeedback.objects.get(game=test_game)
            assert feedback.model_used == "gpt-4-turbo"
            assert feedback.credits_used == credits_cost
            assert feedback.content == mock_feedback_content

            # Verify credits were deducted
            test_user.profile.refresh_from_db()
            assert test_user.profile.credits == initial_credits - credits_cost

            # Verify generate function was called with correct parameters
            mock_generate.assert_called_once_with(test_game)

    def test_generate_ai_feedback_insufficient_credits(self, authenticated_client, test_user, test_game):
        # Set credits lower than required
        test_user.profile.credits = 10
        test_user.profile.save()

        url = reverse("generate_ai_feedback", args=[test_game.id])
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert "message" in response.data
        assert "Insufficient credits" in response.data["message"]

        # Verify no feedback was created
        assert not AiFeedback.objects.filter(game=test_game).exists()

    def test_generate_ai_feedback_game_not_analyzed(self, authenticated_client, test_user, test_game):
        # Set game as not analyzed
        test_game.analysis_status = "not_analyzed"
        test_game.save()

        url = reverse("generate_ai_feedback", args=[test_game.id])
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "message" in response.data
        assert "not been analyzed" in response.data["message"]

        # Verify no feedback was created
        assert not AiFeedback.objects.filter(game=test_game).exists()

    def test_get_game_feedback(self, authenticated_client, test_user, test_game, test_feedback):
        url = reverse("get_game_feedback", args=[test_game.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        # Check feedback content
        assert response.data["content"]["summary"] == "You played a strong game overall."
        assert len(response.data["content"]["key_moments"]) == 2
        assert response.data["content"]["improvement_areas"][0] == "Tactical awareness in complex positions"

        # Check metadata
        assert response.data["model_used"] == "gpt-4-turbo"
        assert response.data["credits_used"] == 25
        assert response.data["created_at"] is not None
        assert response.data["rating"] is None

    def test_get_game_feedback_not_found(self, authenticated_client, test_user, test_game):
        # Delete existing feedback
        AiFeedback.objects.all().delete()

        url = reverse("get_game_feedback", args=[test_game.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_all_feedback(self, authenticated_client, test_user, test_game, test_feedback):
        # Create another game and feedback for the same user
        game2 = Game.objects.create(
            user=test_user,
            platform="lichess",
            white="opponent",
            black="testuser_lichess",
            result="loss",
            pgn='[Event "Test Game 2"]\n1. d4 d5',
            opening_name="Queen's Pawn",
            date_played=timezone.now() - timedelta(days=3),
            analysis_status="analyzed",
        )

        feedback2 = AiFeedback.objects.create(
            user=test_user,
            game=game2,
            content={
                "summary": "You struggled in this game.",
                "opening_advice": "Consider a different response to d4.",
            },
            model_used="gpt-4-turbo",
            credits_used=25,
            created_at=timezone.now() - timedelta(days=2),
        )

        url = reverse("get_all_feedback")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        # Check that we got both feedbacks
        assert len(response.data) == 2

        # Verify they're ordered by created_at (newest first)
        assert response.data[0]["id"] == test_feedback.id
        assert response.data[1]["id"] == feedback2.id

    def test_rate_feedback(self, authenticated_client, test_user, test_feedback):
        url = reverse("rate_feedback", args=[test_feedback.id])
        data = {"rating": 4, "comment": "Very helpful analysis!"}
        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK

        # Verify feedback was updated in the database
        test_feedback.refresh_from_db()
        assert test_feedback.rating == 4
        assert test_feedback.rating_comment == "Very helpful analysis!"

    def test_rate_feedback_invalid_rating(self, authenticated_client, test_user, test_feedback):
        url = reverse("rate_feedback", args=[test_feedback.id])
        data = {"rating": 6, "comment": "Very helpful analysis!"}  # Invalid: should be 1-5
        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "rating" in response.data

    def test_rate_feedback_not_found(self, authenticated_client, test_user):
        url = reverse("rate_feedback", args=[999])  # Non-existent ID
        data = {"rating": 4, "comment": "Very helpful analysis!"}
        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_rate_feedback_unauthorized(self, authenticated_client, test_user, test_feedback):
        # Create another user and feedback
        other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="otherpassword123"
        )
        Profile.objects.create(user=other_user, email_verified=True)

        other_game = Game.objects.create(
            user=other_user, platform="chess.com", result="win", analysis_status="analyzed"
        )

        other_feedback = AiFeedback.objects.create(
            user=other_user, game=other_game, content={"summary": "Test"}, model_used="gpt-4-turbo", credits_used=25
        )

        # Try to rate the other user's feedback
        url = reverse("rate_feedback", args=[other_feedback.id])
        data = {"rating": 4, "comment": "Very helpful analysis!"}
        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
