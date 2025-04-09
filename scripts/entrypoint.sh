#!/bin/bash

# Exit on error
set -e

# Wait for PostgreSQL
while ! nc -z $DB_HOST $DB_PORT; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 1
done
echo "PostgreSQL is up - executing command"

# Wait for Redis
while ! nc -z redis 6379; do
    echo "Redis is unavailable - sleeping"
    sleep 1
done
echo "Redis is up - executing command"

# Create necessary directories if they don't exist
mkdir -p /app/chess_mate/staticfiles
mkdir -p /app/chess_mate/media
mkdir -p /app/chess_mate/logs

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Apply database migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Execute the passed command
exec "$@"
