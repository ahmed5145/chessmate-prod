# ChessMate Setup and Testing Guide

This document outlines how to set up the ChessMate project for development and how to run the tests.

## Project Structure

The ChessMate project consists of the following main components:

- **chess_mate/**: Core Django application
  - **core/**: Main application code
    - **tests/**: Django test cases
      - **health/**: Health check tests
      - **cache/**: Cache invalidation tests
  - **chess_mate/**: Django project settings and configuration
- **standalone_tests/**: Standalone tests (not requiring Django)
- **tests/**: External test scripts for testing a running server
- **docs/**: Documentation

## Development Setup

1. Clone the repository
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Install development dependencies:
   ```bash
   pip install -e .
   ```
5. Set up Redis:
   - On Windows: Run `install_redis.bat`
   - On Linux/Mac: Install Redis and ensure it's running

6. Set up environment variables by copying `.env.example` to `.env.local` and updating values

7. Initialize the database:
   ```bash
   cd chess_mate
   python manage.py migrate
   python manage.py createsuperuser
   ```

## Running the Application

```bash
cd chess_mate
python manage.py runserver
```

Visit http://localhost:8000/ in your browser.

## Running Tests

### Django Tests

To run all Django tests:

```bash
cd chess_mate
python manage.py test core
```

To run specific test modules:

```bash
python manage.py test core.tests.health
python manage.py test core.tests.cache
```

### Standalone Tests

To run standalone tests:

```bash
cd standalone_tests
python -m unittest discover
```

### External Tests

These tests require a running server:

```bash
cd tests
python test_health_checks.py --base-url http://localhost:8000
python test_cache_invalidation.py --base-url http://localhost:8000 --redis-url redis://localhost:6379/0
```

## Health Check Endpoints

The application provides health check endpoints for monitoring:

- `/health/`: Basic health check
- `/readiness/`: Readiness check
- `/api/health/detailed/`: Detailed health check
- `/api/system/status/`: System status (admin only)

## Cache Invalidation

Cache invalidation is implemented using Redis. Tags are used to associate cache entries with specific objects or operations.

To invalidate cache entries with a specific tag:

```python
from core.cache_invalidation import invalidate_cache

invalidate_cache("user_profile_123")
```

## Type Checking

The project uses mypy for type checking:

```bash
mypy chess_mate
```

## Pre-commit Hooks

To set up pre-commit hooks for code quality checks:

```bash
pip install pre-commit
pre-commit install
```

This will run all the checks defined in `.pre-commit-config.yaml` before each commit.
