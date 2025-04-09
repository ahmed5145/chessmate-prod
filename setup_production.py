#!/usr/bin/env python
"""
Setup script for deploying the ChessMate application in a production environment.
This script automates various tasks required for a production deployment.
"""

import os
import sys
import subprocess
import argparse
import random
import string
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("setup_production")

# Constants
PROJECT_DIR = Path(__file__).resolve().parent
CHESS_MATE_DIR = PROJECT_DIR / "chess_mate"
ENV_FILE = PROJECT_DIR / ".env.production"


def generate_secret_key(length=50):
    """Generate a secure random string for use as a Django secret key."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"
    return "".join(random.choice(chars) for _ in range(length))


def run_command(command, check=True):
    """Run a shell command and log its output."""
    logger.info(f"Running command: {' '.join(command)}")
    try:
        result = subprocess.run(
            command, check=check, capture_output=True, text=True
        )
        if result.stdout:
            logger.info(result.stdout)
        if result.stderr:
            logger.warning(result.stderr)
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        logger.error(e.stderr)
        if check:
            sys.exit(1)
        return e


def check_dependencies():
    """Check for required dependencies."""
    logger.info("Checking dependencies...")
    try:
        import django  # noqa
        logger.info(f"Django version: {django.__version__}")
    except ImportError:
        logger.error("Django is not installed. Please install Django first.")
        sys.exit(1)
    
    try:
        import rest_framework  # noqa
        logger.info("Django REST Framework is installed.")
    except ImportError:
        logger.error("Django REST Framework is not installed.")
        sys.exit(1)
    
    try:
        import redis  # noqa
        logger.info("Redis client is installed.")
    except ImportError:
        logger.warning("Redis client is not installed. Redis features will not work.")
    
    # Check for external tools
    for tool in ["python", "pip"]:
        run_command(["which", tool], check=False)


def create_env_file():
    """Create a production .env file if it doesn't exist."""
    if ENV_FILE.exists():
        logger.info(f"{ENV_FILE} already exists. Skipping creation.")
        return
    
    logger.info(f"Creating {ENV_FILE}...")
    secret_key = generate_secret_key()
    
    with open(ENV_FILE, "w") as f:
        f.write(f"SECRET_KEY={secret_key}\n")
        f.write("DEBUG=False\n")
        f.write("ENVIRONMENT=production\n")
        f.write("ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com\n")
        f.write("\n# Database settings\n")
        f.write("DB_NAME=chessmate\n")
        f.write("DB_USER=postgres\n")
        f.write("DB_PASSWORD=\n")
        f.write("DB_HOST=localhost\n")
        f.write("DB_PORT=5432\n")
        f.write("\n# Redis settings\n")
        f.write("REDIS_HOST=localhost\n")
        f.write("REDIS_PORT=6379\n")
        f.write("REDIS_DB=0\n")
        f.write("\n# Email settings\n")
        f.write("EMAIL_HOST=smtp.example.com\n")
        f.write("EMAIL_PORT=587\n")
        f.write("EMAIL_USE_TLS=True\n")
        f.write("EMAIL_HOST_USER=your-email@example.com\n")
        f.write("EMAIL_HOST_PASSWORD=your-email-password\n")
        f.write("DEFAULT_FROM_EMAIL=ChessMate <noreply@example.com>\n")
        f.write("\n# Stripe settings\n")
        f.write("STRIPE_SECRET_KEY=\n")
        f.write("STRIPE_PUBLISHABLE_KEY=\n")
        f.write("STRIPE_WEBHOOK_SECRET=\n")
        f.write("\n# OpenAI settings\n")
        f.write("OPENAI_API_KEY=\n")
    
    logger.info(f"Created {ENV_FILE}. Please update with your production settings.")


def setup_database():
    """Set up the database."""
    logger.info("Setting up the database...")
    os.chdir(CHESS_MATE_DIR)
    
    # Run migrations
    run_command(["python", "manage.py", "makemigrations"])
    run_command(["python", "manage.py", "migrate"])
    
    # Create cache tables
    run_command(["python", "manage.py", "createcachetable"])


def collect_static():
    """Collect static files."""
    logger.info("Collecting static files...")
    os.chdir(CHESS_MATE_DIR)
    run_command(["python", "manage.py", "collectstatic", "--no-input"])


def create_superuser():
    """Create a superuser if needed."""
    logger.info("Do you want to create a superuser? (y/n)")
    choice = input().lower()
    if choice != 'y':
        return
    
    os.chdir(CHESS_MATE_DIR)
    run_command(["python", "manage.py", "createsuperuser"])


def check_security():
    """Check for security issues."""
    logger.info("Running security checks...")
    os.chdir(CHESS_MATE_DIR)
    
    # Run Django's security check
    run_command(["python", "manage.py", "check", "--deploy"])


def setup_production():
    """Main function to set up production environment."""
    logger.info("Setting up ChessMate for production...")
    
    check_dependencies()
    create_env_file()
    setup_database()
    collect_static()
    create_superuser()
    check_security()
    
    logger.info("""
Production setup complete! Next steps:
1. Update the .env.production file with your actual settings
2. Configure your web server (nginx, Apache, etc.)
3. Set up a process manager (gunicorn, uwsgi, etc.)
4. Configure SSL certificates
5. Start the application with:
   cd chess_mate && python manage.py runserver 0.0.0.0:8000 (for testing)
   or use gunicorn in production
    """)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set up ChessMate for production.")
    parser.add_argument("--skip-dependencies", action="store_true", help="Skip dependency checking")
    parser.add_argument("--skip-env", action="store_true", help="Skip .env file creation")
    parser.add_argument("--skip-database", action="store_true", help="Skip database setup")
    parser.add_argument("--skip-static", action="store_true", help="Skip static file collection")
    parser.add_argument("--skip-superuser", action="store_true", help="Skip superuser creation")
    parser.add_argument("--skip-security", action="store_true", help="Skip security checks")
    
    args = parser.parse_args()
    
    try:
        if not args.skip_dependencies:
            check_dependencies()
        if not args.skip_env:
            create_env_file()
        if not args.skip_database:
            setup_database()
        if not args.skip_static:
            collect_static()
        if not args.skip_superuser:
            create_superuser()
        if not args.skip_security:
            check_security()
        
        logger.info("Setup completed successfully!")
    except KeyboardInterrupt:
        logger.info("\nSetup interrupted by user. Exiting...")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during setup: {str(e)}")
        sys.exit(1) 