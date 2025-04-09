@echo off
echo Setting up ChessMate development environment...

:: Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment
call venv\Scripts\activate

:: Install dependencies
echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

:: Create .env file if it doesn't exist
if not exist chess_mate\.env (
    echo Creating .env file...
    (
        echo DEBUG=True
        echo SECRET_KEY=your-secret-key-here
        echo DB_NAME=chessmate
        echo DB_USER=your-db-user
        echo DB_PASSWORD=your-db-password
        echo DB_HOST=localhost
        echo DB_PORT=5432
        echo REDIS_URL=redis://localhost:6379/0
        echo EMAIL_HOST=smtp.gmail.com
        echo EMAIL_PORT=587
        echo EMAIL_USE_TLS=True
        echo EMAIL_HOST_USER=your-email@gmail.com
        echo EMAIL_HOST_PASSWORD=your-app-password
        echo OPENAI_API_KEY=your-openai-api-key
        echo AWS_ACCESS_KEY=your-aws-access-key
        echo AWS_SECRET_KEY=your-aws-secret-key
        echo AWS_BACKUP_BUCKET=your-bucket-name
        echo AWS_REGION=us-east-2
    ) > chess_mate\.env
)

:: Initialize database
echo Running migrations...
cd chess_mate
python manage.py makemigrations
python manage.py migrate

:: Create superuser if needed
echo.
echo Would you like to create a superuser? (Y/N)
set /p create_superuser=
if /i "%create_superuser%"=="Y" (
    python manage.py createsuperuser
)

echo.
echo Setup complete! You can now run the development server with:
echo cd chess_mate
echo python manage.py runserver
