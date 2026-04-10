"""
ChessMate Django project initialization.
"""

# This makes Django include this directory in imports.
# You'll need to still import individual modules from the app.
# e.g. from chess_mate import settings

import importlib
import sys
from typing import Optional

celery_app = None  # type: Optional[object]

try:
    _core = importlib.import_module("core")

    core = _core
    sys.modules.setdefault("chess_mate.core", _core)
except ImportError:
    # Keep package import-safe even when app modules are unavailable.
    pass

__all__ = ["celery_app"]

# Note: For Python 3.12 compatibility, run Django with:
# python patch_celery.py
# And run Celery worker with:
# python patch_and_run_celery.py
