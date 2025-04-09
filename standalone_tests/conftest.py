"""
Pytest configuration for standalone tests.

This file imports fixtures from the root conftest.py to ensure consistency
between standalone tests and Django-integrated tests where applicable.
"""

import os
import sys
from pathlib import Path

import pytest

# Ensure that the root directory is in the path
root_dir = Path(__file__).parent.parent.absolute()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Import universal fixtures from root conftest
try:
    from conftest import cache_mock, mock_game, mock_user, redis_mock
except ImportError:
    # Fallback fixtures if imports fail

    @pytest.fixture(scope="session")
    def redis_mock():
        """Fallback Redis mock."""
        pytest.skip("redis_mock fixture not available")

    @pytest.fixture
    def cache_mock():
        """Fallback cache mock."""
        pytest.skip("cache_mock fixture not available")

    @pytest.fixture
    def mock_user():
        """Fallback mock user."""
        return {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "is_active": True,
        }

    @pytest.fixture
    def mock_game():
        """Fallback mock game."""
        return {
            "id": 1,
            "user_id": 1,
            "pgn": '[Event "Test Game"]\n[White "Test User"]\n[Black "Opponent"]\n1. e4 e5',
            "result": "1-0",
        }


# Specific fixtures for standalone tests
@pytest.fixture
def sample_pgn():
    """Sample PGN data for chess tests."""
    return """
    [Event "Test Game"]
    [Site "Chess.com"]
    [Date "2023.01.01"]
    [White "TestUser"]
    [Black "Opponent"]
    [Result "1-0"]

    1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 O-O
    8. c3 d5 9. exd5 Nxd5 10. Nxe5 Nxe5 11. Rxe5 Nf6 12. d4 Bd6 13. Re1 Bg4
    14. f3 Bh5 15. g4 Bg6 16. Nd2 Qd7 17. Nf1 Rfe8 18. Rxe8+ Rxe8 19. Ne3 h5
    20. h3 hxg4 21. hxg4 Nh7 22. Kg2 Ng5 23. Kg3 Qe7 24. Bd2 Qf6 25. Rh1 Re7
    26. Qf1 Nxf3 27. Qxf3 Qxf3+ 28. Kxf3 Bxc2 29. Nd5 Bxb3 30. Nxe7+ Bxe7
    31. axb3 f6 32. Rc1 Bd6 33. Rc6 Kf7 34. Ke4 Ke7 35. d5 g6 36. Rxd6 Kxd6
    37. Kd4 f5 38. gxf5 gxf5 39. b4 a5 40. bxa5 c5+ 41. dxc6 Kxc6 42. b3 Kc7
    43. Ke5 Kd7 44. Kxf5 Ke7 45. Ke5 Kd7 46. Kd5 Kc7 47. Kc5 Kd7
    48. Kd5 Kc7 49. Kc5 Kd7 50. Kb6 1-0
    """
