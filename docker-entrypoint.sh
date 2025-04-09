#!/bin/bash

set -e

# Wait for postgres
if [ "$DATABASE_HOST" ]; then
    echo "Waiting for postgres..."
    while ! nc -z $DATABASE_HOST $DATABASE_PORT; do
        sleep 0.1
    done
    echo "PostgreSQL started"
fi

# Wait for redis
if [ "$REDIS_HOST" ]; then
    echo "Waiting for redis..."
    while ! nc -z $REDIS_HOST $REDIS_PORT; do
        sleep 0.1
    done
    echo "Redis started"
fi

cd chess_mate

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Create superuser if DJANGO_SUPERUSER_* env vars are set
if [[ -n "$DJANGO_SUPERUSER_USERNAME" ]] && [[ -n "$DJANGO_SUPERUSER_EMAIL" ]] && [[ -n "$DJANGO_SUPERUSER_PASSWORD" ]]; then
    echo "Creating superuser..."
    python manage.py createsuperuser --noinput
fi

# Start Celery worker in background
if [ "$ENABLE_CELERY" = "true" ]; then
    echo "Starting Celery worker..."
    celery -A chess_mate worker -l info &
fi

# Start Gunicorn
echo "Starting application server..."
exec gunicorn chess_mate.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120
