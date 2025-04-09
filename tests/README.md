# ChessMate Testing Tools

This directory contains testing tools and scripts for the ChessMate application.

## Health Check Tests

The `test_health_checks.py` script tests all health check endpoints to verify they are working correctly.

### Usage:

```bash
python test_health_checks.py --url http://localhost:8000 --admin-user admin --admin-password password --output results.json
```

### Arguments:

- `--url`: Base URL of the ChessMate application (default: http://localhost:8000)
- `--admin-user`: Admin username for protected endpoints
- `--admin-password`: Admin password for protected endpoints
- `--output`: Output file for test results (JSON)

The script will test the following endpoints:
- `/health/` - Basic health check
- `/readiness/` - Readiness check
- `/api/v1/health/` - API health check
- `/api/v1/health/detailed/` - Detailed health check
- `/api/v1/system/status/` - System status (admin only)
- `/api/v1/health/run-check-task/` - Run Celery health check task (admin only)
- `/api/v1/info/` - Application info

## Cache Invalidation Tests

The `test_cache_invalidation.py` script tests the tag-based cache invalidation system.

### Usage:

```bash
python test_cache_invalidation.py --url http://localhost:8000 --redis redis://localhost:6379/0 --admin-user admin --admin-password password --output cache_results.json
```

### Arguments:

- `--url`: Base URL of the ChessMate application (default: http://localhost:8000)
- `--redis`: Redis URL (default: redis://localhost:6379/0)
- `--admin-user`: Admin username for protected endpoints
- `--admin-password`: Admin password for protected endpoints
- `--output`: Output file for test results (JSON)

The script will test the following cache invalidation methods:
- Direct invalidation through Redis
- API invalidation for specific tags
- Global cache invalidation

## Running All Tests

You can run both tests with a shell script:

```bash
#!/bin/bash

# Set your configuration
BASE_URL="http://localhost:8000"
REDIS_URL="redis://localhost:6379/0"
ADMIN_USER="admin"
ADMIN_PASSWORD="password"
OUTPUT_DIR="./test_results"

# Create output directory
mkdir -p $OUTPUT_DIR

# Run health check tests
echo "Running health check tests..."
python test_health_checks.py --url $BASE_URL --admin-user $ADMIN_USER --admin-password $ADMIN_PASSWORD --output $OUTPUT_DIR/health_check_results.json

# Run cache invalidation tests
echo "Running cache invalidation tests..."
python test_cache_invalidation.py --url $BASE_URL --redis $REDIS_URL --admin-user $ADMIN_USER --admin-password $ADMIN_PASSWORD --output $OUTPUT_DIR/cache_invalidation_results.json

echo "All tests completed. Results saved to $OUTPUT_DIR"
```

## Interpreting Results

Both test scripts will output a JSON file with the test results when the `--output` argument is provided. The JSON will contain:

- `total_tests`: Total number of tests run
- `successful_tests`: Number of tests that passed
- `failed_tests`: Number of tests that failed
- `results`: Detailed results for each test

The scripts will also display a summary of the test results on the console, with color-coded success/warning/error messages.

## Exit Codes

The test scripts will exit with code 0 if all tests pass, and code 1 if any test fails. This can be used in CI/CD pipelines to fail the build if tests fail.

## Requirements

These scripts require the following Python packages:
- `requests`
- `redis` (for cache invalidation tests)

You can install them with:

```bash
pip install requests redis
```
