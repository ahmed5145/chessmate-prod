#!/bin/bash

# Exit on error
set -e

# Function to wait for PostgreSQL
wait_for_postgres() {
    echo "Waiting for PostgreSQL..."
    while ! nc -z -w1 ${DB_HOST} ${DB_PORT}; do
        sleep 1
    done
    echo "PostgreSQL started"
}

# Function to wait for Redis
wait_for_redis() {
    echo "Waiting for Redis..."
    while ! nc -z -w1 redis 6379; do
        sleep 1
    done
    echo "Redis started"
}

# Wait for services
wait_for_postgres
wait_for_redis

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the appropriate service
if [ "$SERVICE_TYPE" = "celery" ]; then
    echo "Starting Celery worker..."
    celery -A chess_mate worker -l info
else
    echo "Starting Django server..."
    python manage.py runserver 0.0.0.0:8000
fi 