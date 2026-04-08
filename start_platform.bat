@echo off
setlocal

echo Starting ChessMate platform (backend + frontend)...

set "ROOT_DIR=%~dp0"
set "FRONTEND_DIR=%ROOT_DIR%chess_mate\frontend"

if not exist "%FRONTEND_DIR%\package.json" (
    echo Frontend package.json not found at "%FRONTEND_DIR%"
    exit /b 1
)

REM Start backend stack (Redis, Django, Celery) via centralized script.
call "%ROOT_DIR%chess_mate\start_services.bat"

REM Start frontend dev server in a separate minimized window.
start "ChessMate Frontend" /MIN cmd /k "cd /d %FRONTEND_DIR% && npm start"

echo Platform startup complete.
echo Open http://localhost:3000 for frontend.
echo Open http://127.0.0.1:8000 for backend API.
