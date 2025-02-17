@echo off
echo Starting Celery worker...

:: Set environment variables
set PYTHONPATH=%~dp0
set DJANGO_SETTINGS_MODULE=chess_mate.settings
set FORKED_BY_MULTIPROCESSING=1

:: Echo configuration for debugging
echo PYTHONPATH: %PYTHONPATH%
echo DJANGO_SETTINGS_MODULE: %DJANGO_SETTINGS_MODULE%

:: Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

:: Start Celery worker with optimized Windows settings
celery -A chess_mate worker ^
    --pool=solo ^
    --loglevel=info ^
    -Q default,analysis,batch_analysis ^
    --concurrency=1 ^
    --task-events ^
    --without-gossip ^
    --without-mingle ^
    --without-heartbeat ^
    -Ofair ^
    --logfile=logs/celery.log ^
    >> logs/celery_output.log 2>&1

:: If Celery exits with an error, pause to see the error message
if errorlevel 1 (
    echo Celery worker failed to start. Check logs/celery_output.log for details.
    pause
)