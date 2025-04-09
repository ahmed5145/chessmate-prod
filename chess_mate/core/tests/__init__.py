"""
Test package for the ChessMate core app.

This package contains both Django-integrated tests and standalone tests.
"""

import os
import sys

# Add project root to the Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
