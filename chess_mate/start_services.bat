@echo off
setlocal
echo Starting ChessMate backend services...

set "BASE_DIR=%~dp0"
set "VENV_PY=%BASE_DIR%..\venv311\Scripts\python.exe"
set "LOG_DIR=%BASE_DIR%logs"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

if not exist "%VENV_PY%" (
	echo Python executable not found at "%VENV_PY%"
	echo Activate or create venv311 first.
	exit /b 1
)

REM Keep backend and Celery aligned: both must use Redis in this workflow.
set "REDIS_DISABLED=False"
set "DEBUG=True"
set "ENVIRONMENT=development"

where redis-server >nul 2>&1
if %errorlevel%==0 (
	start "ChessMate Redis" /MIN cmd /k "cd /d %BASE_DIR% && set REDIS_DISABLED=False && redis-server redis.windows.conf"
) else (
	echo redis-server was not found in PATH. Start Redis manually if needed.
)

start "ChessMate Django" /MIN cmd /k "cd /d %BASE_DIR% && set REDIS_DISABLED=False && set DEBUG=True && set ENVIRONMENT=development && \"%VENV_PY%\" manage.py runserver 8000"

REM Keep Celery quieter to avoid terminal noise while still showing warnings/errors.
start "ChessMate Celery" /MIN cmd /k "cd /d %BASE_DIR% && set REDIS_DISABLED=False && set DEBUG=True && set ENVIRONMENT=development && \"%VENV_PY%\" -m celery -A chess_mate worker --pool=solo --concurrency=1 --loglevel=WARNING"

echo Backend services started.
echo Redis, Django, and Celery windows were launched minimized.
echo Logs are written by processes under %LOG_DIR% when configured by each service.
