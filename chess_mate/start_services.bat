@echo off
echo Starting ChessMate services...

REM Set path to virtual environment
SET VENV_PATH=..\venv311\Scripts\activate

REM Start Django server
start cmd /k "cd /d %~dp0 && call %VENV_PATH% && python manage.py runserver 8000"

REM Start Celery worker with solo pool to avoid Windows permission issues
start cmd /k "cd /d %~dp0 && call %VENV_PATH% && python -m celery -A chess_mate worker -l info --pool=solo"

echo All services started successfully!
