@echo off
echo Starting ChessMate services...

REM Set path to virtual environment
SET VENV_PATH=..\venv311\Scripts\activate

REM Set Redis port to avoid conflicts
SET REDIS_PORT=6380
SET REDIS_DISABLED=False

REM Start Redis server with custom port
echo Starting Redis server...
start cmd /k "cd /d %~dp0 && redis-server --port %REDIS_PORT%"
timeout /t 5 /nobreak > nul
echo Redis server started.

REM Start Django server
echo Starting Django server...
start cmd /k "cd /d %~dp0 && call %VENV_PATH% && set REDIS_PORT=%REDIS_PORT% && set REDIS_DISABLED=%REDIS_DISABLED% && python manage.py runserver 8000"
timeout /t 5 /nobreak > nul
echo Django server started.

REM Start Celery worker with solo pool to avoid Windows permission issues
echo Starting Celery worker...
start cmd /k "cd /d %~dp0 && call %VENV_PATH% && set REDIS_PORT=%REDIS_PORT% && set REDIS_DISABLED=%REDIS_DISABLED% && python -m celery -A chess_mate worker -l info --pool=solo"
timeout /t 5 /nobreak > nul
echo Celery worker started.

echo All services started successfully! 