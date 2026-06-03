#!/bin/bash

set -e

# Enable debug output to see exactly where issues occur
echo "=== ENTRYPOINT DEBUG MODE ENABLED ==="
echo "Bash version: $(bash --version | head -1)"
echo "Python version: $(python --version 2>&1)"
echo "Current directory: $(pwd)"
echo "Python path: $(python -c 'import sys; print(sys.path)' 2>&1 || echo 'FAILED')"
echo "Django settings: $DJANGO_SETTINGS_MODULE"
echo "=== END DEBUG HEADER ==="
echo
if [ -z "$DB_HOST" ] && [ -n "$RDS_HOSTNAME" ]; then
    export DB_HOST="$RDS_HOSTNAME"
fi
if [ -z "$DB_PORT" ] && [ -n "$RDS_PORT" ]; then
    export DB_PORT="$RDS_PORT"
fi

# If a single DATABASE_URL is provided (e.g. from some platforms), parse it
# into separate DB_* env vars so the application doesn't rely on a single DSN.
# Only populate DB_* if they are not already set (respect explicit settings).
if [ -n "$DATABASE_URL" ]; then
    if [ -z "$DB_HOST" ] || [ -z "$DB_NAME" ] || [ -z "$DB_USER" ]; then
        echo "Parsing DATABASE_URL into DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD"
        python - <<'PY' > /tmp/db_env_from_url.sh
import os
import shlex
from urllib.parse import urlparse
u = os.environ.get('DATABASE_URL')
if not u:
    raise SystemExit(0)
o = urlparse(u)
host = o.hostname or ''
port = str(o.port) if o.port else ''
user = o.username or ''
passwd = o.password or ''
db = o.path[1:] if o.path and o.path.startswith('/') else (o.path or '')

# Emit shell-safe assignments only for empty target variables.
if host:
    print(f'[ -z "$DB_HOST" ] && DB_HOST={shlex.quote(host)}')
if port:
    print(f'[ -z "$DB_PORT" ] && DB_PORT={shlex.quote(port)}')
if db:
    print(f'[ -z "$DB_NAME" ] && DB_NAME={shlex.quote(db)}')
if user:
    print(f'[ -z "$DB_USER" ] && DB_USER={shlex.quote(user)}')
if passwd:
    print(f'[ -z "$DB_PASSWORD" ] && DB_PASSWORD={shlex.quote(passwd)}')
PY
        set -a
        # shellcheck source=/tmp/db_env_from_url.sh
        . /tmp/db_env_from_url.sh
        set +a
        rm -f /tmp/db_env_from_url.sh
    fi
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

echo "Resolved DB target: host=${DB_WAIT_HOST:-<empty>} port=${DB_WAIT_PORT} db=${DB_WAIT_NAME} user=${DB_WAIT_USER}"

if [ -n "$DB_WAIT_HOST" ]; then
    echo "Waiting for postgres at $DB_WAIT_HOST:$DB_WAIT_PORT (max 120s)..."
    counter=0
    max_attempts=60
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

start_bundled_redis() {
    if [ "${USE_BUNDLED_REDIS:-false}" != "true" ]; then
        return 0
    fi
    if nc -z 127.0.0.1 6379 2>/dev/null; then
        echo "Redis already listening on 127.0.0.1:6379"
        return 0
    fi
    echo "Starting bundled Redis (127.0.0.1:6379)..."
    redis-server \
        --bind 127.0.0.1 \
        --port 6379 \
        --daemonize yes \
        --maxmemory 128mb \
        --maxmemory-policy allkeys-lru \
        --save ""
    for i in $(seq 1 15); do
        if nc -z 127.0.0.1 6379 2>/dev/null; then
            echo "Bundled Redis is ready"
            return 0
        fi
        sleep 1
    done
    echo "WARNING: Bundled Redis did not start in time"
    return 1
}

start_bundled_redis

# Wait for redis (after bundled Redis may have started)
REDIS_WAIT_HOST="${REDIS_HOST:-}"
REDIS_WAIT_PORT="${REDIS_PORT:-6379}"
echo "Resolved Redis target: host=${REDIS_WAIT_HOST:-<empty>} port=${REDIS_WAIT_PORT}"
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

mkdir -p logs

# Collect static files
echo "Collecting static files..."
if ! python manage.py collectstatic --noinput 2>&1; then
    echo "ERROR: collectstatic failed"
    exit 1
fi

# Apply database migrations
echo "Applying database migrations..."
if ! python manage.py migrate --noinput 2>&1; then
    echo "ERROR: Database migration failed"
    python manage.py migrate --noinput --verbosity 3 2>&1 || true
    exit 1
fi
echo "Database migrations completed successfully"

# Create superuser if DJANGO_SUPERUSER_* env vars are set
if [[ -n "$DJANGO_SUPERUSER_USERNAME" ]] && [[ -n "$DJANGO_SUPERUSER_EMAIL" ]] && [[ -n "$DJANGO_SUPERUSER_PASSWORD" ]]; then
    echo "Creating superuser..."
    if ! python manage.py createsuperuser --noinput 2>&1; then
        echo "WARNING: Superuser creation failed (may already exist)"
    fi
fi

# Start Celery worker in background
if [ "$ENABLE_CELERY" = "true" ]; then
    echo "Starting Celery worker..."
    celery -A chess_mate worker -l info &
fi

# Start Gunicorn
echo "=== STARTING GUNICORN ON PORT 8000 ==="
exec gunicorn chess_mate.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120 --error-logfile - --access-logfile -
