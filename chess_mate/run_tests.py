#!/usr/bin/env python
"""
Test runner for ChessMate project.

This script properly configures the Python path and environment
to run tests with the correct imports and paths.
"""

import os
import sys
import inspect

# Add the project directory to the Python path FIRST
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Patch inspect.formatargspec BEFORE any Django/Celery imports
# This is needed for Python 3.12 compatibility with older packages like vine
if not hasattr(inspect, 'formatargspec'):
    def formatargspec(args, varargs=None, varkw=None, defaults=None,
                      kwonlyargs=(), kwonlydefaults={}, annotations={}):
        """Replacement for inspect.formatargspec removed in Python 3.12"""
        args = [str(arg) for arg in args]
        parts = []
        if args:
            parts.append(", ".join(args))
        if varargs:
            parts.append(f"*{varargs}")
        if kwonlyargs:
            if not varargs:
                parts.append("*")
            parts.extend([f"{arg}={kwonlydefaults.get(arg, 'None')}" for arg in kwonlyargs])
        if varkw:
            parts.append(f"**{varkw}")
        sig = "(" + ", ".join(parts) + ")"
        if annotations and 'return' in annotations:
            sig += f" -> {annotations['return']}"
        return sig
    
    inspect.formatargspec = formatargspec

if not hasattr(inspect, 'getargspec'):
    def getargspec(func):
        """Replacement for inspect.getargspec removed in Python 3.12"""
        args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations = \
            inspect.getfullargspec(func)
        return inspect.ArgSpec(args, varargs, varkw, defaults)
    
    inspect.getargspec = getargspec

import django
from django.conf import settings
from django.test.utils import get_runner

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chess_mate.chess_mate.test_settings")


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
