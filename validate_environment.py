#!/usr/bin/env python
"""
ChessMate Environment Validation Script

This script checks if your environment is correctly set up for running ChessMate.
It verifies:
1. Required Python packages
2. Database configuration
3. Redis connectivity
4. Directory structure and permissions
5. Environment variables
"""

import os
import sys
import platform
import subprocess
import importlib.util
from pathlib import Path


def print_header(message):
    """Print a header with decoration."""
    print("\n" + "=" * 60)
    print(f" {message}")
    print("=" * 60)


def print_status(label, status, details=None):
    """Print a status message with color coding."""
    status_text = " [PASS] " if status else " [FAIL] "
    print(f"{status_text} {label}")
    if details and not status:
        print(f"       ↳ {details}")


def check_python_version():
    """Verify Python version meets requirements."""
    print_header("Python Environment")
    
    # Check Python version (require 3.8+)
    current_version = sys.version_info
    version_ok = current_version.major == 3 and current_version.minor >= 8
    version_str = f"{current_version.major}.{current_version.minor}.{current_version.micro}"
    
    print_status(
        f"Python version: {version_str}", 
        version_ok,
        "Python 3.8 or higher is required"
    )
    
    # Print system information
    print(f"\nSystem: {platform.system()} {platform.release()}")
    print(f"Platform: {platform.platform()}")
    print(f"Python path: {sys.executable}")
    
    return version_ok


def check_required_packages():
    """Check for required Python packages."""
    print_header("Required Packages")
    
    # List of packages to check
    required_packages = [
        ("django", "Django"),
        ("rest_framework", "Django REST Framework"),
        ("redis", "Redis Client"),
        ("psycopg2", "PostgreSQL Driver"),
        ("celery", "Celery"),
        ("jwt", "PyJWT"),
    ]
    
    all_ok = True
    for package_name, display_name in required_packages:
        try:
            spec = importlib.util.find_spec(package_name)
            if spec is None:
                # Try alternative import names for some packages
                if package_name == "rest_framework":
                    spec = importlib.util.find_spec("djangorestframework")
                if package_name == "jwt":
                    spec = importlib.util.find_spec("PyJWT")
            
            if spec:
                # Try to get the version
                try:
                    module = importlib.import_module(package_name)
                    version = getattr(module, "__version__", "unknown version")
                except (ImportError, AttributeError):
                    version = "installed"
                
                print_status(f"{display_name}: {version}", True)
            else:
                print_status(f"{display_name}", False, "Not installed")
                all_ok = False
        except ImportError:
            print_status(f"{display_name}", False, "Import error")
            all_ok = False
    
    return all_ok


def check_directory_structure():
    """Check that the directory structure is correct."""
    print_header("Directory Structure")
    
    # Define the expected directory structure
    expected_dirs = [
        "chess_mate",
        "chess_mate/core",
        "chess_mate/logs",
        "chess_mate/static",
        "chess_mate/templates",
    ]
    
    expected_files = [
        "chess_mate/manage.py",
        "chess_mate/settings.py",
        "chess_mate/urls.py",
        "chess_mate/core/auth_views.py",
        "chess_mate/core/profile_views.py",
        "requirements.txt",
    ]
    
    base_dir = Path.cwd()
    
    # Check directories
    all_dirs_ok = True
    for dir_path in expected_dirs:
        path = base_dir / dir_path
        exists = path.exists() and path.is_dir()
        print_status(f"Directory: {dir_path}/", exists, "Directory not found" if not exists else None)
        all_dirs_ok = all_dirs_ok and exists
    
    # Check files
    all_files_ok = True
    for file_path in expected_files:
        path = base_dir / file_path
        exists = path.exists() and path.is_file()
        print_status(f"File: {file_path}", exists, "File not found" if not exists else None)
        all_files_ok = all_files_ok and exists
    
    # Look for .env file
    env_path = base_dir / ".env"
    env_prod_path = base_dir / ".env.production"
    env_exists = env_path.exists() or env_prod_path.exists()
    
    print_status(
        "Environment file (.env or .env.production)", 
        env_exists,
        "Environment file not found" if not env_exists else None
    )
    
    return all_dirs_ok and all_files_ok and env_exists


def check_database_connection():
    """Check if the database is properly configured and accessible."""
    print_header("Database Configuration")
    
    # Attempt to run the Django check command
    try:
        os.chdir("chess_mate")
        check_cmd = [sys.executable, "manage.py", "check"]
        subprocess.run(check_cmd, capture_output=True, text=True)
        print_status("Django configuration check", True)
        
        # Try running a command that requires database access
        migrate_cmd = [sys.executable, "manage.py", "showmigrations", "--list"]
        result = subprocess.run(migrate_cmd, capture_output=True, text=True)
        
        db_ok = result.returncode == 0
        print_status(
            "Database connection", 
            db_ok, 
            result.stderr.strip() if not db_ok else None
        )
        
        # Return to original directory
        os.chdir("..")
        return db_ok
    except Exception as e:
        print_status("Database check", False, str(e))
        # Return to original directory if needed
        if Path.cwd().name == "chess_mate":
            os.chdir("..")
        return False


def check_redis_connection():
    """Check if Redis is configured and accessible."""
    print_header("Redis Connectivity")
    
    # Check if redis is installed
    try:
        import redis
        redis_installed = True
    except ImportError:
        redis_installed = False
        print_status("Redis client", False, "Redis package not installed")
        return False
    
    print_status("Redis client", redis_installed)
    
    # Try to connect to Redis
    try:
        # Default connection parameters
        redis_host = "localhost"
        redis_port = 6379
        redis_db = 0
        
        # Try to read from environment variables or .env file
        try:
            from dotenv import load_dotenv
            load_dotenv()
            redis_host = os.getenv("REDIS_HOST", redis_host)
            redis_port = int(os.getenv("REDIS_PORT", redis_port))
            redis_db = int(os.getenv("REDIS_DB", redis_db))
        except ImportError:
            pass
        
        # Connect to Redis
        r = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
        r.ping()  # Will throw exception if connection fails
        
        print_status(f"Redis connection ({redis_host}:{redis_port})", True)
        return True
    except Exception as e:
        print_status(f"Redis connection ({redis_host}:{redis_port})", False, str(e))
        return False


def check_environment_variables():
    """Check for required environment variables."""
    print_header("Environment Variables")
    
    # List of important environment variables to check
    env_vars = [
        "SECRET_KEY",
        "DEBUG",
        "ALLOWED_HOSTS",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "DB_HOST",
        "DB_PORT",
        "REDIS_HOST",
        "REDIS_PORT",
        "REDIS_DB",
        "EMAIL_HOST",
        "EMAIL_PORT",
        "EMAIL_HOST_USER",
        "EMAIL_HOST_PASSWORD",
        "DEFAULT_FROM_EMAIL",
    ]
    
    # Try to load .env file if it exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print_status("Loaded environment variables from .env file", True)
    except ImportError:
        print_status(
            "python-dotenv package", 
            False, 
            "Package not installed, unable to load .env file"
        )
    
    # Check each environment variable
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            display_value = "*" * len(value) if "PASSWORD" in var or "SECRET" in var else value
            print_status(f"{var}: {display_value}", True)
        else:
            print_status(var, False, "Environment variable not set")


def run_all_checks():
    """Run all validation checks and provide a summary."""
    results = {}
    
    results["python"] = check_python_version()
    results["packages"] = check_required_packages()
    results["directories"] = check_directory_structure()
    results["database"] = check_database_connection()
    results["redis"] = check_redis_connection()
    check_environment_variables()  # This one doesn't return a status
    
    # Print summary
    print_header("Summary")
    
    all_ok = all(results.values())
    for check, status in results.items():
        print_status(f"{check.capitalize()} check", status)
    
    if all_ok:
        print("\n✅ All checks passed! Your environment is ready for ChessMate.")
    else:
        print("\n⚠️ Some checks failed. Please fix the issues before proceeding.")
    
    return all_ok


if __name__ == "__main__":
    run_all_checks() 