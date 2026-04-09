"""Repository-local Python startup tweaks.

Ensure the app package root is importable when tools run from the repo root.
"""

import os
import sys


repo_root = os.path.dirname(os.path.abspath(__file__))
app_root = os.path.join(repo_root, "chess_mate")

if os.path.isdir(app_root) and app_root not in sys.path:
    sys.path.insert(0, app_root)