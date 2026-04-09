"""
ChessMate Django project initialization.
"""

# This makes Django include this directory in imports.
# You'll need to still import individual modules from the app.
# e.g. from chess_mate import settings

# Import Celery for task processing
from .celery import app as celery_app
import sys

try:
	import core as _core

	core = _core
	sys.modules.setdefault("chess_mate.core", _core)
except Exception:
	# Keep package import-safe even when app modules are unavailable.
	pass

__all__ = ["celery_app"]

# Note: For Python 3.12 compatibility, run Django with:
# python patch_celery.py
# And run Celery worker with:
# python patch_and_run_celery.py
