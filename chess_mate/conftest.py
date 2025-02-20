import os
import sys
import django
from django.conf import settings
import pytest
from django.test import TransactionTestCase
from django.db import connection, transaction
from django.core.management import call_command
import logging
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from typing import Optional
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

# Set testing environment variable
os.environ['TESTING'] = 'True'
os.environ['DJANGO_SETTINGS_MODULE'] = 'chess_mate.test_settings'

# Initialize Django
django.setup()

def pytest_configure():
    """Configure test environment."""
    settings.DEBUG = False
    settings.TESTING = True

@pytest.fixture(scope='session')
def django_db_setup(django_db_blocker):
    """Set up the test database."""
    settings.DATABASES['default'] = {
            'ENGINE': 'django.db.backends.sqlite3',
        'NAME': settings.BASE_DIR / 'test_db.sqlite3',
    }
    with django_db_blocker.unblock():
        call_command('migrate')
        yield

@pytest.fixture(autouse=True)
def db_access_wrapper(django_db_setup, django_db_blocker):
    """Wrap each test in a transaction."""
    with django_db_blocker.unblock():
        with transaction.atomic():
            yield

@pytest.fixture
def capture_queries():
    """Capture and return all SQL queries executed during a test."""
    with CaptureQueriesContext(connection) as context:
        yield context

@pytest.fixture
def stockfish_mock(mocker):
    """Mock Stockfish engine for testing."""
    # Create a mock PovScore class
    class MockScore:
        def __init__(self, cp_score=None, mate_in=None):
            self._cp_score = cp_score
            self._mate_in = mate_in
            
        def score(self, mate_score: int = 10000) -> Optional[int]:
            if self._mate_in is not None:
                return self._mate_in * mate_score
            return self._cp_score
            
        def cp(self):
            return self._cp_score
            
        def is_mate(self):
            return self._mate_in is not None
            
        def mate(self):
            return self._mate_in

    class MockPovScore:
        def __init__(self, score: MockScore, color: bool):
            self._score = score
            self._color = color
            
        def relative(self):
            return self._score
            
        def pov(self, color: bool):
            return self._score if color == self._color else MockScore(-self._score.score())
            
        def white(self):
            return self.pov(True)
            
        def black(self):
            return self.pov(False)
            
        def is_mate(self):
            return self._score.is_mate()
            
        def mate(self):
            return self._score.mate()
            
        def cp(self):
            return self._score.cp()

    # Create the mock engine
    mock = mocker.patch('chess.engine.SimpleEngine.popen_uci')
    
    # Set up default analysis response
    def create_analysis_result(cp_score=10, depth=20, nodes=1000, time=0.5, pv=None):
        """Create a mock analysis result that matches frontend expectations."""
        move_analysis = {
            'score': MockPovScore(MockScore(cp_score), True),
            'depth': depth,
            'pv': pv or [],
            'nodes': nodes,
            'time': time
        }
        
        analysis_data = {
            'analysis_complete': True,
            'analysis_results': {
                'moves': [{
                    'move': 'e4',
                    'score': cp_score,
                    'depth': depth,
                    'nodes': nodes,
                    'time': time,
                    'analysis': move_analysis,
                    'is_critical': False,
                    'is_mistake': False,
                    'is_blunder': False,
                    'eval_change': 0.0
                }],
                'is_white': True,
                'total_moves': 1,
                'depth': depth,
                'summary': {
                    'overall': {
                        'accuracy': 85.5,
                        'mistakes': 0,
                        'blunders': 0,
                        'average_centipawn_loss': 15.2
                    },
                    'phases': {
                        'opening': {'accuracy': 90.0, 'moves': 10},
                        'middlegame': {'accuracy': 85.0, 'moves': 20},
                        'endgame': {'accuracy': 0.0, 'moves': 0}
                    },
                    'tactics': {
                        'opportunities': 1,
                        'success_rate': 100,
                        'missed': 0,
                        'found': 1
                    },
                    'time_management': {
                        'average_time': time,
                        'critical_time_usage': 0.8,
                        'time_pressure_mistakes': 0
                    },
                    'positional': {
                        'space': 60,
                        'control': 70,
                        'piece_activity': 75
                    },
                    'advantage': {
                        'max': cp_score,
                        'min': -cp_score,
                        'average': cp_score/2
                    },
                    'resourcefulness': {
                        'defensive': 80,
                        'attacking': 75,
                        'tactical_awareness': 85
                    }
                }
            },
            'feedback': {
                'analysis_results': {
                    'summary': {
                        'overall': {'accuracy': 85.5, 'evaluation': 'Strong performance'},
                        'phases': {'opening': 90.0, 'middlegame': 85.0, 'endgame': 0.0},
                        'tactics': {'opportunities': 1, 'success_rate': 100},
                        'time_management': {'average_time': time, 'efficiency': 85},
                        'positional': {'space': 60, 'control': 70},
                        'advantage': {'max': cp_score, 'average': cp_score/2},
                        'resourcefulness': {'defensive': 80, 'attacking': 75}
                    },
                    'strengths': ['Solid opening play', 'Good tactical awareness'],
                    'weaknesses': ['Could improve time management'],
                    'critical_moments': [
                        {
                            'move': 'e4',
                            'position': 1,
                            'evaluation': cp_score,
                            'description': 'Key opening move'
                        }
                    ],
                    'improvement_areas': 'Focus on time management and positional understanding'
                },
                'analysis_complete': True,
                'source': 'stockfish'
            },
            'source': 'stockfish',
            'timestamp': datetime.now().isoformat()
        }
        return analysis_data
    
    # Set up the mock to return a default analysis result
    mock.return_value.analyse.return_value = create_analysis_result()
    
    # Store the create_analysis_result function on the mock for test customization
    mock.create_analysis_result = create_analysis_result
    
    return mock

@pytest.fixture
def test_user(django_user_model):
    """Create a test user."""
    with transaction.atomic():
        user = django_user_model.objects.create_user(
            username='test_user',
            password='test_password',
            email='test@example.com'
        )
    return user

@pytest.fixture
def test_profile(test_user):
    """Create a test profile."""
    from core.models import Profile
    with transaction.atomic():
        profile, created = Profile.objects.get_or_create(
            user=test_user
        )
    return profile

@pytest.fixture
def test_game(test_profile):
    """Create a test game."""
    from core.models import Game
    with transaction.atomic():
        game = Game.objects.create(
            user=test_profile.user,
            platform='test',
            game_id='test123',
            white=test_profile.user.username,
            black=test_profile.user.username,
            pgn='1. e4 e5',
            result='*',
            date_played=timezone.now()
        )
    return game

@pytest.fixture
def mock_openai():
    """Mock OpenAI client for testing."""
    from unittest.mock import MagicMock
    mock = MagicMock()
    mock.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content="""
                    {
                        "summary": {
                            "accuracy": 85.5,
                            "evaluation": "Strong performance",
                            "personalized_comment": "Good understanding of the position"
                        },
                        "phase_analysis": {
                            "opening": {
                                "analysis": "Good opening play",
                                "suggestions": ["Consider e4 variations"]
                            },
                            "middlegame": {
                                "analysis": "Solid positional play",
                                "suggestions": ["Focus on piece coordination"]
                            },
                            "endgame": {
                                "analysis": "Efficient conversion",
                                "suggestions": ["Practice basic endgames"]
                            }
                        },
                        "study_plan": {
                            "focus_areas": ["Opening theory", "Tactical awareness"],
                            "rating_appropriate_exercises": ["Basic tactics", "Endgame studies"]
                        }
                    }
                    """
                )
            )
        ]
    )
    return mock

@pytest.fixture
def admin_user(django_user_model):
    """Create a superuser for admin access."""
    with transaction.atomic():
        admin = django_user_model.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin'
        )
    return admin

class TestCase(TransactionTestCase):
    """Base test case class with improved database handling."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self._clean_database()
        logger.info(f"Setting up test case: {self.__class__.__name__}")
    
    def tearDown(self):
        """Clean up after each test."""
        try:
            super().tearDown()
        finally:
            # Ensure connection is properly closed
            connection.close()
            logger.info(f"Tearing down test case: {self.__class__.__name__}")

    def _clean_database(self):
        """Clean the database between tests."""
        try:
            with transaction.atomic():
                cursor = connection.cursor()
                tables = connection.introspection.table_names()
                for table in tables:
                    cursor.execute(f'TRUNCATE TABLE "{table}" CASCADE')
                cursor.close()
        except Exception as e:
            logger.error(f"Error cleaning database: {str(e)}")
            if 'connection already closed' in str(e):
                connection.close()
                connection.connect() 