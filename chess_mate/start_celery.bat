@echo off
setlocal enabledelayedexpansion

echo Starting Celery worker...

:: Set environment variables for Windows
set DJANGO_SETTINGS_MODULE=chess_mate.settings
set PYTHONPATH=%CD%
set FORKED_BY_MULTIPROCESSING=1

:: Create logs directory if it doesn't exist
if not exist logs mkdir logs

:: Start Celery worker with Windows-specific settings
python -m celery -A chess_mate worker ^
    --pool=solo ^
    --loglevel=INFO ^
    --concurrency=1 ^
    --max-tasks-per-child=1 ^
    --max-memory-per-child=200000 ^
    --events ^
    --logfile=logs/celery.log ^
    --pidfile=celery.pid

if errorlevel 1 (
    echo Failed to start Celery worker
    exit /b 1
)

echo Celery worker started successfully
