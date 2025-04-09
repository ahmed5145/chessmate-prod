@echo off
echo Setting up ChessMate project environment...

REM Create a virtual environment
python -m venv venv
call venv\Scripts\activate

REM Set environment variables
setx DEBUG True
setx ENVIRONMENT development
setx REDIS_DISABLED True

REM Create the default .env file if it doesn't exist
if not exist .env.development (
    echo Creating default .env.development file...
    echo # Development Environment Variables for ChessMate > .env.development
    echo. >> .env.development
    echo # General settings >> .env.development
    echo DEBUG=True >> .env.development
    echo ENVIRONMENT=development >> .env.development
    echo SECRET_KEY=django-insecure-dev-key >> .env.development
    echo. >> .env.development
    echo # Database settings >> .env.development
    echo DB_ENGINE=django.db.backends.sqlite3 >> .env.development
    echo DB_NAME=db.sqlite3 >> .env.development
    echo. >> .env.development
    echo # Redis settings >> .env.development
    echo REDIS_DISABLED=True >> .env.development
    echo. >> .env.development
    echo # API settings >> .env.development
    echo ALLOWED_HOSTS=localhost,127.0.0.1 >> .env.development
    echo CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000 >> .env.development
)

REM Install dependencies
pip install -r requirements.txt

REM Create necessary directories
mkdir chess_mate\logs 2>nul
mkdir chess_mate\media 2>nul

REM Run initial setup
cd chess_mate
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput

echo.
echo Setup complete! Run 'run_development.bat' to start the development server.
echo.

pause 