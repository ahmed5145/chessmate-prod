"""ChessMate Django project initialization.

Importing the Celery app can trigger heavy imports (and in some test
collector setups can cause circular imports). Import the app lazily and
fall back to ``None`` if it cannot be imported at module import time.
"""

try:
    from .celery import app as celery_app
except Exception:
    celery_app = None

__all__ = ["celery_app"]
