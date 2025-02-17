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
    settings.DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'test_chessmate',
            'USER': 'postgres',
            'PASSWORD': 'admin',
            'HOST': 'localhost',
            'PORT': '5432',
            'ATOMIC_REQUESTS': True,
            'CONN_MAX_AGE': 0,
            'OPTIONS': {
                'client_encoding': 'UTF8',
            },
            'TEST': {
                'NAME': 'test_chessmate',
                'SERIALIZE': False,
            }
        }
    }

@pytest.fixture(scope='session')
def django_db_setup(django_db_blocker):
    """Set up the test database."""
    from django.test.utils import setup_databases, teardown_databases
    with django_db_blocker.unblock():
        db_cfg = setup_databases(verbosity=0, interactive=False)
        yield
        teardown_databases(db_cfg, verbosity=0)

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
    mock = mocker.patch('chess.engine.SimpleEngine.popen_uci')
    mock.return_value.analyse.return_value = {
        'score': mocker.Mock(relative=mocker.Mock(return_value=0)),
        'pv': []
    }
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
            user=test_user,
            defaults={
                'credits': 5,
                'platform_username': 'test_user',
                'platform': 'chess.com'
            }
        )
    return profile

@pytest.fixture
def test_game(test_profile):
    """Create a test game."""
    from core.models import Game
    with transaction.atomic():
        game = Game.objects.create(
            user=test_profile.user,
            white='test_user',
            black='opponent',
            pgn='1. e4 e5',
            result='*',
            platform='chess.com',
            date_played=timezone.now(),
            game_id='test123'
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