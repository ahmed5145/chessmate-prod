# ChessMate Installation Guide

This guide provides comprehensive installation instructions for ChessMate across different platforms.

## Prerequisites

- Python 3.8 or higher
- Git
- Redis (optional, but recommended for full functionality)
- PostgreSQL (optional, SQLite by default)

## Quick Start

### Windows

1. **Run the Windows setup script**:
   ```
   setup_windows.bat
   ```

2. **Start the application**:
   ```
   run_development.bat
   ```

3. **Access the application**:
   Open your browser and go to http://127.0.0.1:8000/

### Linux/Mac

1. **Install the package with dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

2. **Run the setup script**:
   ```bash
   ./setup.sh
   ```

3. **Start the application**:
   ```bash
   python manage.py runserver
   ```

## Detailed Installation

### Windows Manual Setup

1. **Install the package with dependencies**:
   ```
   pip install -e ".[dev,windows]"
   ```

2. **Install additional required packages**:
   ```
   pip install python-json-logger>=2.0.0
   ```

3. **Create necessary directories**:
   ```
   mkdir chess_mate\logs
   mkdir chess_mate\media
   mkdir chess_mate\staticfiles
   ```

4. **Set up the Python path**:
   ```
   python -c "import site; import os; open(os.path.join(site.getsitepackages()[0], 'chessmate.pth'), 'w').write(os.path.abspath('.'))"
   ```

5. **Run migrations**:
   ```
   cd chess_mate
   python manage.py makemigrations
   python manage.py migrate
   ```

### Redis Setup

#### Windows Options

1. **Windows Subsystem for Linux (WSL)**:
   ```powershell
   wsl --install
   sudo apt update && sudo apt install redis-server
   sudo service redis-server start
   ```

2. **Redis Windows port**:
   - Download from https://github.com/microsoftarchive/redis/releases
   - Extract to `C:\Redis`
   - Run `redis-server.exe`

#### Linux/Mac
```bash
sudo apt update
sudo apt install redis-server
sudo service redis-server start
```

## Common Issues and Solutions

### Missing Dependencies

If you see a `ModuleNotFoundError`:
```
pip install some_module
```

### Import Issues

If you see implementation errors:
```
python -c "import site; import os; open(os.path.join(site.getsitepackages()[0], 'chessmate.pth'), 'w').write(os.path.abspath('.'))"
```
Then restart your IDE or command prompt.

### Database Errors

For PostgreSQL issues:
1. Install PostgreSQL
2. Create a database named 'chessmate'
3. Update your .env file with credentials

For SQLite development:
```
set ENVIRONMENT=development
```

### Redis Connection Issues

If Redis is not available:
```
set REDIS_DISABLED=True
```

## Production Setup

1. **Install production dependencies**:
   ```
   pip install -e ".[prod]"
   ```

2. **Configure environment variables** in `.env`:
   ```
   DEBUG=False
   ENVIRONMENT=production
   SECRET_KEY=your_secure_key
   ALLOWED_HOSTS=your_domain.com
   ```

## Additional Scripts

- `setup_windows.bat`: Complete Windows setup
- `run_development.bat`: Runs the application in development mode
- `install_project.py`: Python script for cross-platform setup
- `install_dev.py`: Installs development dependencies
