@echo off
echo Starting ChessMate API server with optimized settings...

REM Set environment variables
set DEBUG=True
set ENVIRONMENT=development
set REDIS_DISABLED=True

REM Navigate to the chess_mate directory
cd chess_mate

REM Clear any .pyc files to avoid cached import issues
echo Clearing any .pyc files...
del /s /q *.pyc >nul 2>&1

REM Start the Django server
echo Starting Django server...
python manage.py runserver

REM If we get here, the server has stopped
echo Django server has stopped.
cd .. 