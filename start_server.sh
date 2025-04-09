#!/bin/bash
echo "Starting ChessMate API server with optimized settings..."

# Navigate to the chess_mate directory
cd chess_mate

# Clear any .pyc files to avoid cached import issues
echo "Clearing any .pyc files..."
find . -name "*.pyc" -delete

# Start the Django server with environment variables
echo "Starting Django server..."
DEBUG=True ENVIRONMENT=development REDIS_DISABLED=True python manage.py runserver

# If we get here, the server has stopped
echo "Django server has stopped."
cd .. 