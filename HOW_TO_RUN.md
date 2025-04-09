# How to Run ChessMate

This guide provides step-by-step instructions for running the ChessMate application. These instructions are optimized for Windows but include notes for other platforms.

## Windows Setup

### Option 1: Quick Setup (Recommended)

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

### Option 2: Manual Setup

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

6. **Start the server**:
   ```
   python manage.py runserver
   ```

## Linux/Mac Setup

1. **Install the package with dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

2. **Install additional required packages**:
   ```bash
   pip install python-json-logger>=2.0.0
   ```

3. **Create necessary directories**:
   ```bash
   mkdir -p chess_mate/logs
   mkdir -p chess_mate/media
   mkdir -p chess_mate/staticfiles
   ```

4. **Set up the Python path**:
   ```bash
   python -c "import site; import os; open(os.path.join(site.getsitepackages()[0], 'chessmate.pth'), 'w'), 'w').write(os.path.abspath('.'))"
   ```

5. **Run migrations**:
   ```bash
   cd chess_mate
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Start the server**:
   ```bash
   python manage.py runserver
   ```

## Common Issues and Solutions

### Missing Dependencies

If you see an error about a missing module:

```
ModuleNotFoundError: No module named 'some_module'
```

Install the missing dependency:

```
pip install some_module
```

### Import Issues

If you see errors like:

```
Cannot find implementation or library stub for module named "core.views"
```

Ensure your Python path is properly set by running:

```
python -c "import site; import os; open(os.path.join(site.getsitepackages()[0], 'chessmate.pth'), 'w').write(os.path.abspath('.'))"
```

Then restart your IDE or command prompt.

### Database Errors

If you encounter database-related errors and you're using PostgreSQL, you may need to:

1. Install PostgreSQL
2. Create a database named 'chessmate'
3. Update your .env file with the correct database credentials

Alternatively, use SQLite for development by setting:

```
set ENVIRONMENT=development
```

### Redis Connection Issues

The application requires Redis for full functionality. On Windows, you have two options:

1. Download and install the Windows Redis port: https://github.com/microsoftarchive/redis/releases
2. Use WSL (Windows Subsystem for Linux) to run Redis

Alternatively, you can run without Redis by setting:

```
set REDIS_DISABLED=True
```

## Production Setup

For production deployment, install the production dependencies:

```
pip install -e ".[prod]"
```

And set the appropriate environment variables in your .env file:

```
DEBUG=False
ENVIRONMENT=production
SECRET_KEY=your_secure_key
ALLOWED_HOSTS=your_domain.com
```

## Additional Scripts

- **setup_windows.bat**: Complete Windows setup
- **run_development.bat**: Runs the application in development mode
- **install_project.py**: Python script for cross-platform setup
- **install_dev.py**: Installs development dependencies 