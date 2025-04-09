@echo off
echo Setting up ChessMate project for development...

REM Set environment variables
set DEBUG=True
set ENVIRONMENT=development
set REDIS_DISABLED=True

REM Load environment variables from .env.development if it exists
python load_env.py development

REM Install the project in development mode
pip install -e .

REM Install the required packages for logging
pip install python-json-logger>=2.0.0

REM Create necessary directories
mkdir chess_mate\logs 2>nul
mkdir chess_mate\media 2>nul

REM Change to the chess_mate directory
cd chess_mate

echo Starting the Django development server...
python manage.py makemigrations
python manage.py migrate
python manage.py runserver 0.0.0.0:8000

pause 