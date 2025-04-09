#!/usr/bin/env python
"""
Test script to verify Django models can be properly loaded.
"""

import os
import sys

import django

# Add the directory containing chess_mate to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chess_mate.test_settings")
django.setup()


def test_models():
    """Test if core models can be properly loaded."""
    try:
        from django.apps import apps

        # Print installed apps
        print("Installed apps:")
        for app in apps.get_app_configs():
            print(f" - {app.name}")

        # Try to load core models
        print("\nTrying to load core models:")
        from core.models import Game, GameAnalysis, Profile

        print(" - Successfully imported core.models")

        # Check if models are registered with Django
        print("\nChecking model registration:")
        try:
            Game._meta.app_label
            print(f" - Game app_label: {Game._meta.app_label}")
        except Exception as e:
            print(f" - Game error: {str(e)}")

        try:
            Profile._meta.app_label
            print(f" - Profile app_label: {Profile._meta.app_label}")
        except Exception as e:
            print(f" - Profile error: {str(e)}")

        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_models()
    sys.exit(0 if success else 1)
