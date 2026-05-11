#!/bin/bash

set -e

# Map Elastic Beanstalk RDS variables to Django database variables.
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
DB_WAIT_PORT="${DB_PORT:-${DATABASE_PORT:-5432}}"
DB_WAIT_USER="${DB_USER:-postgres}"
DB_WAIT_NAME="${DB_NAME:-postgres}"

if [ -n "$DB_WAIT_HOST" ]; then
    echo "Waiting for postgres at $DB_WAIT_HOST:$DB_WAIT_PORT (max 120s)..."
    counter=0
    max_attempts=120
    while [ $counter -lt $max_attempts ]; do
        if command -v pg_isready >/dev/null 2>&1; then
            if pg_isready -h "$DB_WAIT_HOST" -p "$DB_WAIT_PORT" -U "$DB_WAIT_USER" -d "$DB_WAIT_NAME" >/dev/null 2>&1; then
                echo "PostgreSQL is ready"
                break
            fi
        else
            if nc -z "$DB_WAIT_HOST" "$DB_WAIT_PORT" >/dev/null 2>&1; then
                echo "PostgreSQL TCP port is reachable"
                break
            fi
        fi

        counter=$((counter + 1))
        if [ $((counter % 10)) -eq 0 ]; then
            echo "Still waiting for postgres... ($counter/$max_attempts)"
        fi
        sleep 1
    done

    if [ $counter -eq $max_attempts ]; then
        echo "ERROR: PostgreSQL not reachable at $DB_WAIT_HOST:$DB_WAIT_PORT after ${max_attempts}s"
        echo "Check RDS inbound rules and EB instance security groups."
        exit 1
    fi
fi

# Wait for redis
REDIS_WAIT_HOST="${REDIS_HOST:-}"
REDIS_WAIT_PORT="${REDIS_PORT:-6379}"
if [ "$REDIS_WAIT_HOST" ]; then
    echo "Waiting for redis at $REDIS_WAIT_HOST:$REDIS_WAIT_PORT (max 30s)..."
    counter=0
    max_attempts=30
    while [ $counter -lt $max_attempts ]; do
        if nc -z "$REDIS_WAIT_HOST" "$REDIS_WAIT_PORT" 2>/dev/null; then
            echo "Redis is ready!"
            break
        fi
        counter=$((counter + 1))
        sleep 1
    done
    if [ $counter -eq $max_attempts ]; then
        echo "WARNING: Redis did not respond after 30s, proceeding anyway..."
    fi
fi

cd chess_mate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

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
