@echo off
echo Stopping any existing Redis and Celery processes...
taskkill /F /IM "redis-server.exe" > nul 2>&1
taskkill /F /IM "celery.exe" > nul 2>&1

timeout /t 2 /nobreak > nul
start "Redis Server" /B redis-server redis.windows.conf
if errorlevel 1 (
    echo Failed to start Redis server
    exit /b 1
)

echo Waiting for Redis to start...
timeout /t 5 /nobreak > nul
redis-cli ping > nul 2>&1
if errorlevel 1 (
    echo Failed to connect to Redis
    exit /b 1
)
echo Redis is running!

echo Starting Celery worker...
set FORKED_BY_MULTIPROCESSING=1
set PYTHONPATH=%cd%
set CELERY_LOADER=default
set C_FORCE_ROOT=true
set CELERY_BROKER_URL=redis://localhost:6379/0
set CELERY_RESULT_BACKEND=redis://localhost:6379/0

REM Kill any existing Celery workers
taskkill /F /IM "celery.exe" > nul 2>&1

REM Start Celery with specific Windows configuration
start "Celery Worker" cmd /k "celery -A chess_mate worker --pool=solo --concurrency=1 --loglevel=INFO --without-heartbeat --without-mingle --task-events"

echo All services started successfully!
echo The services are running in separate windows. Close this window to stop the services.