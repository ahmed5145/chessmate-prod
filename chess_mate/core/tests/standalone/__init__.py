"""
Standalone tests package.

This package contains tests that can run without Django dependencies.
All tests in this directory are automatically marked with the 'standalone' marker.
"""

import pytest

# Apply the 'standalone' marker to all tests in this directory
pytestmark = pytest.mark.standalone
