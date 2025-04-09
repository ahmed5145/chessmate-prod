#!/usr/bin/env python
"""
Test runner for ChessMate project.

This script properly configures the Python path and environment
to run tests with the correct imports and paths.
"""

import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner

# Add the project directory to the Python path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chess_mate.test_settings")


def setup_django():
    """Initialize Django for testing."""
    # Initialize Django
    django.setup()

    # Print debug info
    print(f"Using settings module: {os.environ['DJANGO_SETTINGS_MODULE']}")
    print(f"Python path: {sys.path}")


def run_tests():
    """Run tests with proper configuration."""
    setup_django()

    # Get the test runner class from settings
    TestRunner = get_runner(settings)

    # Create an instance of the test runner
    test_runner = TestRunner(verbosity=2, interactive=True)

    # Run the tests
    failures = test_runner.run_tests(["core.tests"])

    return failures


if __name__ == "__main__":
    # Run the tests and exit with appropriate status code
    failures = run_tests()
    sys.exit(bool(failures))
