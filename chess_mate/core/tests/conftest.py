import os
import sys
import django
from django.conf import settings
import pytest
from unittest.mock import MagicMock, patch
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
import json
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from django.utils import timezone
from datetime import timedelta
from django.core.management import call_command

from ..models import Profile, Game

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chess_mate.test_settings')
os.environ['TESTING'] = 'True'
django.setup()

# Database setup (before all tests)
@pytest.fixture(scope="session")
def django_db_setup(django_db_blocker):
    with django_db_blocker.unblock():
        # Apply migrations
        call_command('migrate')

# Common fixtures for all test modules
@pytest.fixture
def api_client():
    """Return a Django REST Framework API client."""
    return APIClient()

@pytest.fixture
def test_user(db):
    """Create and return a test user with a profile."""
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpassword123'
    )
    Profile.objects.create(
        user=user,
        email_verified=True,
        credits=100,
        chess_com_username='testuser',
        lichess_username='testuser_lichess',
        elo_rating=1500,
        analysis_count=5,
        preferences={
            'theme': 'light',
            'notifications_enabled': True,
            'analysis_depth': 'balanced'
        }
    )
    return user

@pytest.fixture
def unverified_user(db):
    """Create and return an unverified test user."""
    user = User.objects.create_user(
        username='unverified',
        email='unverified@example.com',
        password='testpassword123'
    )
    Profile.objects.create(
        user=user,
        email_verified=False,
        email_verification_token='test-token-123',
        credits=10
    )
    return user

@pytest.fixture
def authenticated_client(db, api_client, test_user):
    """Return an authenticated API client."""
    url = reverse('login')
    data = {
        'email': 'test@example.com',
        'password': 'testpassword123'
    }
    response = api_client.post(url, data, format='json')
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return api_client

@pytest.fixture
def test_game(db, test_user):
    """Create and return a test game for the test user."""
    game = Game.objects.create(
        user=test_user,
        platform='chess.com',
        white='testuser',
        black='opponent',
        result='win',
        pgn='[Event "Test Game"]\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6',
        opening_name='Ruy Lopez',
        date_played=timezone.now() - timedelta(days=1),
        analysis_status='analyzed',
        analysis={
            'analysis_results': {
                'summary': {
                    'user_accuracy': 85.5,
                    'key_moments': [
                        {'move': 10, 'type': 'missed_tactic', 'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'},
                        {'move': 15, 'type': 'blunder', 'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'}
                    ]
                },
                'moves': [
                    {'move_number': 1, 'move': 'e4', 'eval': 0.3},
                    {'move_number': 2, 'move': 'e5', 'eval': 0.2}
                ]
            }
        }
    )
    
    return game

# Create a mock OpenAI response
@pytest.fixture
def mock_openai_response():
    valid_json_content = {
        "feedback": {
            "summary": {
                "accuracy": "85.5",
                "evaluation": "Strong game with minor inaccuracies",
                "comment": "Good tactical awareness with solid time management"
            },
            "phases": {
                "opening": {
                    "analysis": "Solid opening play with good development",
                    "suggestions": ["Control center earlier", "Develop minor pieces faster"]
                },
                "middlegame": {
                    "analysis": "Active piece play with good tactical awareness",
                    "suggestions": ["Look for combinations", "Improve piece coordination"]
                },
                "endgame": {
                    "analysis": "Technical conversion needs improvement",
                    "suggestions": ["Practice basic endgames", "Activate king earlier"]
                }
            },
            "tactics": {
                "analysis": "Good tactical awareness",
                "opportunities": 5,
                "successful": 3,
                "success_rate": 60.0,
                "suggestions": ["Practice tactical patterns", "Calculate variations deeper"]
            },
            "time_management": {
                "score": 85,
                "avg_time_per_move": 15.5,
                "time_pressure_moves": 3,
                "time_pressure_percentage": 10.0,
                "suggestion": "Good time management overall"
            },
            "key_moments": [
                "Strong tactical shot on move 15",
                "Good defensive resource on move 23",
                "Missed opportunity in time pressure on move 35"
            ],
            "improvement_areas": [
                "Opening preparation",
                "Endgame technique",
                "Time management in critical positions"
            ],
            "study_plan": {
                "focus_areas": [
                    "Tactical pattern recognition",
                    "Endgame fundamentals",
                    "Opening principles"
                ],
                "exercises": [
                    "Solve tactical puzzles daily",
                    "Study basic endgame positions",
                    "Review master games in your openings"
                ]
            }
        }
    }
    
    message = ChatCompletionMessage(
        content=json.dumps(valid_json_content),
        role="assistant",
        function_call=None,
        tool_calls=None
    )
    choice = Choice(
        finish_reason="stop",
        index=0,
        message=message,
        logprobs=None
    )
    return ChatCompletion(
        id="test_id",
        choices=[choice],
        created=1234567890,
        model="gpt-3.5-turbo",
        object="chat.completion",
        system_fingerprint=None,
        usage=None
    )

# Mock the OpenAI client
@pytest.fixture(autouse=True)
def mock_openai(mock_openai_response):
    with patch("openai.OpenAI") as mock_client:
        # Create a mock instance
        mock_instance = MagicMock()
        
        # Mock the chat.completions.create method
        mock_instance.chat.completions.create.return_value = mock_openai_response
        
        # Make the mock client return our mock instance
        mock_client.return_value = mock_instance
        
        yield mock_client 