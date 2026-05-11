#!/bin/bash

set -e

# Map Elastic Beanstalk RDS variables to Django database variables
if [ -z "$DB_HOST" ] && [ -n "$RDS_HOSTNAME" ]; then
    export DB_HOST="$RDS_HOSTNAME"
fi
if [ -z "$DB_PORT" ] && [ -n "$RDS_PORT" ]; then
    export DB_PORT="$RDS_PORT"
fi
if [ -z "$DB_NAME" ] && [ -n "$RDS_DB_NAME" ]; then
    export DB_NAME="$RDS_DB_NAME"
fi
if [ -z "$DB_USER" ] && [ -n "$RDS_USERNAME" ]; then
    export DB_USER="$RDS_USERNAME"
fi
if [ -z "$DB_PASSWORD" ] && [ -n "$RDS_PASSWORD" ]; then
    export DB_PASSWORD="$RDS_PASSWORD"
fi

DB_WAIT_HOST="${DB_HOST:-$DATABASE_HOST}"
DB_WAIT_PORT="${DB_PORT:-$DATABASE_PORT}"
if [ "$DB_WAIT_HOST" ]; then
    echo "Waiting for postgres at $DB_WAIT_HOST:$DB_WAIT_PORT..."
    while ! nc -z $DB_WAIT_HOST $DB_WAIT_PORT; do
        sleep 0.1
    done
    echo "PostgreSQL started"
fi

# Wait for redis
REDIS_WAIT_HOST="${REDIS_HOST:-}"
REDIS_WAIT_PORT="${REDIS_PORT:-6379}"
if [ "$REDIS_WAIT_HOST" ]; then
    echo "Waiting for redis..."
    while ! nc -z $REDIS_WAIT_HOST $REDIS_WAIT_PORT; do
        sleep 0.1
    done
    echo "Redis started"
fi

cd chess_mate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

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
