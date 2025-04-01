[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Profile Views](https://visitor-badge.laobi.icu/badge?page_id=ahmed5145.ahmed5145&title=Profile%20Views)
[![GitHub stars](https://img.shields.io/github/stars/ahmed5145/chessmate.svg)](https://github.com/ahmed5145/chessmate/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/ahmed5145/chessmate.svg)](https://github.com/ahmed5145/chessmate/network)
[![GitHub issues](https://img.shields.io/github/issues/ahmed5145/chessmate.svg)](https://github.com/ahmed5145/chessmate/issues)
![GitHub last commit](https://img.shields.io/github/last-commit/ahmed5145/chessmate)

# ChessMate - Advanced Chess Game Analysis Platform

ChessMate is a sophisticated chess analysis platform that combines the power of the Stockfish engine with modern web technologies to provide detailed game analysis and personalized feedback.

## Navigation

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Code Organization](#code-organization)
- [Usage](#usage)
- [Testing](#testing)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## Features

- **Game Analysis**: Detailed analysis of chess games using Stockfish engine
- **Personalized Feedback**: AI-powered feedback on your games
- **Credit System**: Flexible credit packages for game analysis
- **Multi-Platform Support**: Import games from Chess.com and Lichess
- **Modern UI**: Responsive design with real-time updates
- **Secure Authentication**: JWT-based authentication system

## Prerequisites

- Python 3.8+
- Node.js 14+
- Redis Server
- Stockfish Chess Engine
- PostgreSQL (optional, SQLite by default)

## Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/ahmed5145/chessmate.git
   cd chessmate
   ```

2. **Install dependencies**:
   - **Backend**:

     ```bash
     cd chessmate
     python -m venv venv
     source venv/bin/activate  # or `venv\Scripts\activate` on Windows
     pip install -r requirements.txt
     ```

   - **Frontend**:

     ```bash
     cd frontend
     npm install
     ```

3. **Set up environment variables**:

   ```bash
   cp .env.example .env
   # Edit .env with your configuration:
   # - Set up email credentials
   # - Add OpenAI API key
   # - Configure Stripe keys
   # - Set Stockfish path
   ```

4. **Initialize the database**:

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Start Redis Server**:

   ```bash
   redis-server
   ```

6. **Start Celery Worker**:

   ```bash
   celery -A chess_mate worker -l info
   ```

7. **Run development servers**:

   - **Backend**:

     ```bash
     cd chess_mate
     python manage.py runserver
     ```

   - **Frontend**:

     ```bash
     cd frontend
     npm start
     ```

## Code Organization

The ChessMate backend is organized into modular components for better maintainability:

### Core Modules

- **Authentication** (`auth_views.py`): User registration, login, logout, password reset, and token management
- **Game Management** (`game_views.py`): Game retrieval, analysis, and batch operations
- **User Profiles** (`profile_views.py`): Profile management, subscriptions, and credit system
- **Dashboard** (`dashboard_views.py`): User statistics, performance trends, and mistake analysis
- **AI Feedback** (`feedback_views.py`): AI-powered game feedback and improvement suggestions
- **Utilities** (`util_views.py`): Health checks, monitoring, and system information

Each module has corresponding test files in the `/tests` directory ensuring comprehensive test coverage.

## Usage

1. **Create an account** or sign in using your email and password
2. **Purchase analysis credits** from available packages
3. **Import games** from Chess.com or Lichess
4. **Select games** for analysis
5. **View detailed analysis** including:
   - Move accuracy
   - Critical moments
   - Improvement suggestions
   - Opening recommendations
   - Time management feedback

## Testing

- **Backend Tests**:

  ### Using provided test scripts:
  ```bash
  # On Unix/Linux/macOS
  cd chess_mate
  chmod +x run_tests.sh
  ./run_tests.sh                    # Run all tests
  ./run_tests.sh core/tests/test_auth_views.py  # Run specific test file
  
  # On Windows
  cd chess_mate
  run_tests.bat                     # Run all tests
  run_tests.bat core\tests\test_auth_views.py  # Run specific test file
  ```

  ### Manual testing setup:
  ```bash
  cd chess_mate
  python -m pytest
  ```

  The test suite includes comprehensive tests for all core modules:
  - Authentication tests
  - Game management tests
  - Profile management tests
  - Dashboard functionality tests
  - AI feedback tests
  - Utility endpoint tests

  **Setting up the test environment**:
  1. Create a test settings file at `chess_mate/test_settings.py`:
     ```python
     from .settings import *
     
     # Use in-memory SQLite for tests
     DATABASES = {
         'default': {
             'ENGINE': 'django.db.backends.sqlite3',
             'NAME': ':memory:',
         }
     }
     
     # Disable Celery tasks during testing
     CELERY_ALWAYS_EAGER = True
     
     # Mock external services
     OPENAI_API_KEY = 'test-key'
     STRIPE_SECRET_KEY = 'test-stripe-secret-key'
     STRIPE_PUBLIC_KEY = 'test-stripe-public-key'
     ```
  
  2. Run tests with the custom settings:
     ```bash
     DJANGO_SETTINGS_MODULE=chess_mate.test_settings python -m pytest
     ```
  
  3. For CI/CD environments, add environment variables:
     ```bash
     export DJANGO_SETTINGS_MODULE=chess_mate.test_settings
     export TESTING=True
     ```

- **Frontend Tests**:

  ```bash
  cd frontend
  npm test
  ```

## API Documentation

See [API Documentation](docs/api.md) for detailed endpoint information.

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Stockfish Chess Engine
- OpenAI API
- Chess.com API
- Lichess API

---
*Document last updated on April 1, 2025*  
*Copyright © 2024 ChessMate. All rights reserved.*
