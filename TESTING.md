# ChessMate Testing Guide

This document outlines the testing approach for the ChessMate project, including how to run tests and how the testing infrastructure is organized.

## Testing Structure

The ChessMate testing framework uses a unified approach that includes:

1. **Standalone Tests**: Python tests that don't require Django and can run independently.
2. **Django Tests**: Tests that require the Django framework and database integration.

All tests use pytest as the test runner, with common fixtures available to both test types through a consolidated conftest.py configuration.

## Setup

Before running tests, you need to install the ChessMate package in development mode:

```bash
# Install in development mode
python install_dev.py
```

## Running Tests

### Unified Test Runner

We provide a single test runner script (`run_tests.py`) that can run all types of tests:

```bash
# Run standalone tests
python run_tests.py --standalone

# Run Django tests
python run_tests.py --django

# Run a specific test path
python run_tests.py --path chess_mate/core/tests/test_auth_views.py

# Run all tests (default)
python run_tests.py
```

### Additional Options

The test runner accepts several options to control test execution:

- `--verbose` or `-v`: Increase verbosity (can be used multiple times, e.g., `-vv`)
- `--coverage`: Generate coverage report
- `--html`: Generate HTML coverage report
- `--fail-under PERCENTAGE`: Fail if coverage is under the specified percentage (default: 80%)
- `--keep-db`: Keep the test database between runs

Example:

```bash
# Run all tests with coverage report and fail if coverage is below 90%
python run_tests.py --coverage --fail-under 90 --html
```

## Test Directory Structure

```
ChessMate/
├── conftest.py                      # Root conftest with universal fixtures
├── run_tests.py                     # Unified test runner
├── pytest.ini                       # Global pytest configuration
│
├── standalone_tests/                # Tests that run without Django
│   ├── __init__.py                  # Package marker
│   ├── conftest.py                  # Standalone-specific fixtures
│   ├── test_move_validation.py      # Tests for chess move validation
│   ├── test_move_validation_parameterized.py  # Parameterized tests
│   └── test_cache_mock.py           # Tests for Redis caching
│
└── chess_mate/
    └── core/
        └── tests/                   # Django-integrated tests
            ├── __init__.py          # Package marker
            ├── test_auth_views.py   # Tests for authentication views
            ├── test_game_views.py   # Tests for game management
            └── ...                  # Other Django test modules
```

## Writing Tests

### Standalone Tests

Place standalone tests in the `standalone_tests/` directory:

```python
# standalone_tests/test_example.py
import pytest

def test_something():
    assert 1 + 1 == 2
```

### Django Tests

Place Django-integrated tests in the `chess_mate/core/tests/` directory:

```python
# chess_mate/core/tests/test_example.py
import pytest
from django.test import TestCase

# Using pytest with django_db marker
@pytest.mark.django_db
def test_database_operation():
    # Test with database access
    pass

# Using Django's TestCase
class ExampleTestCase(TestCase):
    def test_something(self):
        # Test with Django TestCase
        pass
```

## Test Fixtures

### Universal Fixtures

These fixtures are available in both standalone and Django tests:

- `redis_mock`: A mock Redis client for testing caching
- `cache_mock`: A simple cache implementation using the Redis mock
- `mock_user`: A dictionary representing a user
- `mock_game`: A dictionary representing a game

### Django-specific Fixtures

These fixtures are only available in Django tests:

- `client`: Django test client
- `django_user_model`: The User model
- `test_user`: A test user instance
- `test_superuser`: A test superuser instance
- `authenticated_client`: Client logged in as a regular user
- `admin_client`: Client logged in as an admin user
- `test_game`: A Game model instance
- `test_profile`: A Profile model instance

### Standalone-specific Fixtures

These fixtures are only available in standalone tests:

- `sample_pgn`: Sample PGN data for chess tests

## Test Coverage

We aim for 80%+ test coverage across all modules. Check coverage with:

```bash
python run_tests.py --coverage --html
```

This will generate an HTML coverage report in the `htmlcov/` directory.

## Continuous Integration

Tests are automatically run on our CI/CD pipeline using GitHub Actions.

## Best Practices

1. **Use Descriptive Names**: Name your test functions and classes clearly to indicate what they're testing.

2. **Test One Thing at a Time**: Each test should focus on testing a single function or feature.

3. **Use Fixtures**: Use fixtures for common setup rather than duplicating code.

4. **Parameterize Common Tests**: Use `@pytest.mark.parametrize` for tests that should run with multiple inputs.

5. **Prefer pytest Assertions**: Use pytest's built-in assertions for better error messages.

6. **Mock External Dependencies**: Use mocks for external services and APIs.

7. **Test Edge Cases**: Don't just test the happy path - test error conditions and edge cases.

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure your Python path is set correctly. The test runner handles this automatically.

2. **Database Errors**: If you get database errors, use the `--keep-db` flag to prevent test database recreation.

3. **Django Settings**: Make sure the Django settings module is properly set for tests.

4. **Missing Dependencies**: Ensure all test dependencies are installed:
   ```bash
   pip install pytest pytest-django pytest-cov pytest-mock fakeredis
   ```

### Getting Help

If you encounter issues with the test suite, consult the following resources:

- [pytest Documentation](https://docs.pytest.org/)
- [Django Testing Documentation](https://docs.djangoproject.com/en/stable/topics/testing/)
- [pytest-django Documentation](https://pytest-django.readthedocs.io/)
