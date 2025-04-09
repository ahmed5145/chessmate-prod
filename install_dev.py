#!/usr/bin/env python
"""
Development setup script for ChessMate project.
This script installs all the required development dependencies.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path


def main():
    """Set up the development environment."""
    print("Setting up ChessMate development environment...")

    # Install the project in development mode
    subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."])

    # Install development dependencies
    subprocess.run([sys.executable, "-m", "pip", "install", "-e", ".[dev]"])

    # Install Windows-specific packages if on Windows
    if platform.system() == "Windows":
        # Install pywin32 for Windows-specific functionality
        subprocess.run([sys.executable, "-m", "pip", "install", "pywin32"])
        # Install eventlet as an alternative to gevent on Windows
        subprocess.run([sys.executable, "-m", "pip", "install", "eventlet"])

    # Set up pre-commit hooks
    subprocess.run(["pre-commit", "install"])

    print("Development environment setup complete!")
    print("You can now run the project with: python run_development.bat")


if __name__ == "__main__":
    main()
