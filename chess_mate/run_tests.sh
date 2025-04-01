#!/bin/bash

# Set environment variables for testing
export DJANGO_SETTINGS_MODULE=chess_mate.test_settings
export TESTING=True

# Set paths
export PYTHONPATH="$(pwd):${PYTHONPATH}"

# Run migrations first
echo "Running migrations..."
python manage.py migrate --settings=chess_mate.test_settings

# Run tests with detailed output
echo "Running tests..."
if [ $# -eq 0 ]; then
    # No arguments, run all tests
    python -m pytest -v
else
    # Run specific tests
    python -m pytest -v "$@"
fi 