#!/usr/bin/env python
"""
Installation script for ChessMate project.
This script sets up the project for development or production use.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path


def main():
    """Main installation function"""
    print("Setting up ChessMate project...")

    # Get the current directory (project root)
    project_dir = Path(__file__).resolve().parent

    # Add the project directory to Python path
    sys.path.insert(0, str(project_dir))

    # Create a .pth file in the site-packages directory to make the path permanent
    try:
        import site

        site_packages = site.getsitepackages()[0]
        with open(os.path.join(site_packages, "chessmate.pth"), "w") as f:
            f.write(str(project_dir))
        print(f"Added {project_dir} to Python path permanently")
    except Exception as e:
        print(f"Warning: Could not add to site-packages: {e}")
        print("You may need to run this script with administrator/superuser privileges")

    # Create a pyproject.toml file for Python path configuration
    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.exists():
        with open(pyproject_path, "w") as f:
            f.write("""[build-system]
requires = ["setuptools>=42", "wheel"]
build-backend = "setuptools.build_meta"

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
disallow_incomplete_defs = false
check_untyped_defs = true
disallow_untyped_decorators = false
no_implicit_optional = true
strict_optional = true

[[tool.mypy.overrides]]
module = "tests.*"
ignore_errors = true

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "chess_mate.test_settings"
python_files = ["test_*.py", "*_test.py"]
testpaths = ["tests", "chess_mate/core/tests"]
""")
        print("Created pyproject.toml file for Python path configuration")

    # Install dependencies
    print("Installing dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."])

    # Install development dependencies
    print("Installing development dependencies...")
    subprocess.run([
        sys.executable, "-m", "pip", "install", "-e", ".[dev]", 
    ])

    # Create necessary directories
    os.makedirs(os.path.join(project_dir, "chess_mate", "logs"), exist_ok=True)
    os.makedirs(os.path.join(project_dir, "chess_mate", "media"), exist_ok=True)

    # Create local settings if they don't exist
    settings_file = os.path.join(project_dir, "chess_mate", "chess_mate", "settings_local.py")
    if not os.path.exists(settings_file):
        with open(settings_file, "w") as f:
            f.write('"""\nLocal settings for development\n"""\n\n')
            f.write("# This file should not be committed to version control\n\n")
            f.write("DEBUG = True\n")
            f.write('SECRET_KEY = "dev-local-key-change-me-in-production"\n')
            f.write('INSTALLED_APPS = ["debug_toolbar"]\n')
            f.write('MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"]\n')
            f.write('INTERNAL_IPS = ["127.0.0.1"]\n')

    # Fix import issues in VSCode
    vscode_dir = project_dir / ".vscode"
    if not vscode_dir.exists():
        os.makedirs(vscode_dir, exist_ok=True)
        
    settings_json = vscode_dir / "settings.json"
    if not settings_json.exists():
        with open(settings_json, "w") as f:
            f.write("""
{
    "python.analysis.extraPaths": [
        "${workspaceFolder}",
        "${workspaceFolder}/chess_mate"
    ],
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true
}
""")
        print("Created VSCode settings for proper import resolution")

    print("Setup complete! You can now run the application with:")
    print(f"cd {os.path.join(project_dir, 'chess_mate')} && python manage.py runserver")


if __name__ == "__main__":
    main()
