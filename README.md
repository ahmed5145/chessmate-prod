[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Profile Views](https://visitor-badge.laobi.icu/badge?page_id=ahmed5145.ahmed5145&title=Profile%20Views)
[![GitHub stars](https://img.shields.io/github/stars/ahmed5145/chessmate.svg)](https://github.com/ahmed5145/chessmate/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/ahmed5145/chessmate.svg)](https://github.com/ahmed5145/chessmate/network)
[![GitHub issues](https://img.shields.io/github/issues/ahmed5145/chessmate.svg)](https://github.com/ahmed5145/chessmate/issues)
![GitHub last commit](https://img.shields.io/github/last-commit/ahmed5145/chessmate)
![CI Status](https://github.com/ahmed5145/chessmate/workflows/ChessMate%20CI/badge.svg)

# ChessMate: AI-Powered Chess Analysis Platform

ChessMate is a comprehensive platform that offers AI-powered chess analysis, training, and performance tracking. The application helps chess players of all levels improve their game through detailed analysis and personalized feedback.

## Features

- **Game Analysis**: Upload your chess games for AI-powered analysis
- **Performance Tracking**: Track your progress and identify improvement areas
- **Personalized Training**: Get custom training plans based on your weaknesses
- **User Profiles**: Maintain your chess profile with statistics
- **Authentication**: Secure user authentication and authorization
- **API Integration**: RESTful API for integration with other chess platforms

## Project Structure

```
chess_mate/           # Main Django application directory
├── core/             # Core application modules
│   ├── auth_views.py # Authentication views
│   ├── profile_views.py # Profile-related views
│   ├── middleware.py # Custom middleware
│   └── urls_*.py     # URL routing configurations
├── static/           # Static files
├── templates/        # HTML templates
├── settings.py       # Django settings
└── logs/             # Application logs
    ├── chessmate.log # Main application log
    ├── django.log    # Django framework log
    └── error.log     # Error log
```

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL
- Redis (for caching and Celery tasks)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/chessmate.git
cd chessmate
```

### Step 2: Create and Activate a Virtual Environment

```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Unix or MacOS
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Setup Database

```bash
cd chess_mate
python manage.py migrate
```

### Step 5: Create an Admin User

```bash
python manage.py createsuperuser
```

### Step 6: Run the Development Server

```bash
python manage.py runserver 0.0.0.0:8000
```

## Production Deployment

For production deployment, use the provided `setup_production.py` script:

```bash
python setup_production.py
```

This script automates:
- Environment setup
- Database configuration
- Static files collection
- Security checks
- Superuser creation

## Debugging and Testing

### Authentication Testing

To test API authentication:

```bash
python check_authentication.py
```

Options:
- `--base-url`: API base URL (default: http://localhost:8000)
- `--username`: Test username
- `--password`: Test password
- `--verbose`: Enable verbose output
- `--test`: Specific test to run (choices: all, register, login, basic, simple, profile, refresh)

### JWT Token Debugging

To debug JWT token issues:

```bash
python jwt_debug.py --token YOUR_JWT_TOKEN
```

Options:
- `--token`: JWT token to analyze
- `--auth-header`: Authorization header containing the token
- `--create-test`: Create a test token
- `--user-id`: User ID for test token
- `--username`: Username for test token
- `--expiry`: Expiry in days for test token

## API Endpoints

### Authentication

- `POST /api/v1/auth/register/`: Register a new user
- `POST /api/v1/auth/login/`: Login and get tokens
- `POST /api/v1/auth/logout/`: Logout (invalidate tokens)
- `POST /api/v1/auth/token/refresh/`: Refresh access token
- `GET /api/v1/auth/test-auth/`: Test authentication
- `GET /api/v1/auth/simple-auth/`: Simple authentication test

### Profile

- `GET /api/v1/profile/`: Get full user profile
- `GET /api/v1/profile/minimal/`: Get minimal user profile
- `PUT /api/v1/profile/update/`: Update user profile
- `GET /api/v1/profile/stats/`: Get user statistics

## Configuration

The application can be configured through environment variables or a `.env` file. Important configuration options include:

- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode (True/False)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`: Database configuration
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`: Redis configuration
- `EMAIL_*`: Email settings
- `STRIPE_*`: Stripe payment integration settings
- `OPENAI_API_KEY`: OpenAI API key for AI analysis

## Troubleshooting

Common issues and their solutions:

### Authentication Issues

If experiencing JWT authentication problems:
1. Check token expiration using `jwt_debug.py`
2. Verify the Authorization header format (should be `Bearer <token>`)
3. Ensure the JWT secret key is consistent across settings

### Database Connection Issues

If encountering database connection problems:
1. Verify PostgreSQL is running
2. Check database credentials in settings
3. Ensure the database exists and is accessible

### Running Tests

To run the API tests:

```bash
python test_api.py --use-basic-profile --verbose
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Django and Django REST Framework for the web framework
- OpenAI for the chess analysis capabilities
- PostgreSQL and Redis for data storage

---

For issues, feature requests, or contributions, please open an issue or pull request on GitHub.

## Navigation

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Code Organization](#code-organization)
- [Performance Features](#performance-features)
- [Usage](#usage)
- [Testing](#testing)
- [CI/CD](#cicd)
- [Deployment](#deployment)
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
- **Optimized Caching**: Redis-powered caching with intelligent invalidation

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
   # - Configure Redis connection
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
- **Task Management** (`task_manager.py`): Background task tracking, status updates, and queue management
- **Redis Configuration** (`redis_config.py`): Optimized Redis client with connection pooling and error handling
- **Cache Middleware** (`cache_middleware.py`): Automatic cache invalidation based on model changes

Each module has corresponding test files in the `/tests` directory ensuring comprehensive test coverage.

## Performance Features

ChessMate includes several performance optimizations to handle high traffic and enhance user experience:

### Caching System

- **Redis Connection Pooling**: Optimized Redis connections with configurable pool size
- **Intelligent Cache Invalidation**: Tag-based and entity-based cache invalidation strategies
- **Cache Stampede Prevention**: Distributed locks to prevent multiple processes from regenerating the same cache
- **Automatic Model-Based Invalidation**: Cache automatically invalidated when related models are updated
- **Configurable TTL**: Different time-to-live settings for different types of data
- **Cache Statistics**: Real-time monitoring of cache hit/miss rates

### Database Optimization

- **Connection Pooling**: Configured PostgreSQL connection pooling for better database performance
- **Query Optimization**: Optimized queries with proper indexing
- **Persistent Connections**: Configurable connection lifetime for better throughput

### API Performance

- **Rate Limiting**: Redis-based rate limiting to protect the API from abuse
- **Response Compression**: Automatic compression of API responses
- **Efficient Serialization**: Optimized JSON serialization for faster response times
- **Batch Processing**: Support for batch operations to reduce network overhead

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

ChessMate includes a comprehensive testing strategy with both Django-integrated and standalone tests.

### Testing Approach

Our testing strategy is documented in detail in the [TESTING.md](TESTING.md) file, which provides guidelines for running and writing tests.

### Test Categories

- **Django-Integrated Tests**: Tests that require the Django framework, database access, etc.
- **Standalone Utility Tests**: Tests for utility functions that can run independently of Django
- **Frontend Tests**: Tests for the React frontend components

### Running Tests

#### Backend Tests:

```bash
# Run standalone utility tests (no Django dependencies)
python -m pytest test_utils_standalone.py test_utils_parameterized.py test_cache_mock.py -v -p no:django

# Run Django-integrated tests
cd chess_mate
python -m pytest

# Run tests with coverage
python -m pytest --cov=chess_mate --cov-report=html
```

#### Frontend Tests:

```bash
cd frontend
npm test
```

### Test Features

- **Parameterized Testing**: Using pytest's parameterize for maintainable test cases
- **Redis Mocking**: Custom mock implementation for Redis-based tests
- **Fixtures**: Reusable test data fixtures for Django models
- **Test Coverage**: Aiming for 80%+ test coverage across all modules
- **Continuous Integration**: Automated testing via GitHub Actions

### CI/CD Integration

Our GitHub Actions workflow automatically runs all tests on every push and pull request to the main branch, ensuring code quality and preventing regressions.

For more details, see the [.github/workflows/test.yml](.github/workflows/test.yml) file.

## CI/CD

ChessMate uses GitHub Actions for automated testing, building, and deployment pipelines:

### Continuous Integration

- **Backend Tests**: All Python code is automatically tested on every pull request and push to main branches
- **Frontend Tests**: React components and integration tests are run automatically
- **Linting**: Code quality checks ensure consistent style and prevent common issues
- **Security Scanning**: Regular security scans identify potential vulnerabilities

To view the CI pipeline status, check the Actions tab in the GitHub repository.

### Continuous Deployment

- **Staging Environment**: Changes merged to the `staging` branch are automatically deployed to the staging environment
- **Production Environment**: Changes merged to the `main` branch are automatically deployed to production after approval
- **Manual Deployment**: Deployment can also be triggered manually through GitHub Actions

### Docker Support

The application is containerized using Docker, with the following components:

- **Backend Container**: Django application with Gunicorn
- **Frontend Container**: React application served through Nginx
- **Database Container**: PostgreSQL for data storage
- **Redis Container**: For caching and Celery task queue
- **Celery Container**: For background task processing

To build and run the application using Docker:

```bash
# Build and start all services
docker-compose up -d
```

## Cache System Architecture

ChessMate implements a sophisticated caching system with the following components:

### Redis Configuration (`redis_config.py`)

Provides optimized Redis client with:
- Connection pooling for better performance
- Error handling and retries
- JSON serialization
- Zlib compression for large objects
- Helper functions for common cache operations

### Cache Invalidation (`cache_middleware.py`)

Implements automatic cache invalidation with:
- Model-based invalidation system using Django signals
- Tag-based invalidation for related objects
- Entity-based invalidation for specific instances
- Hierarchical invalidation for parent-child relationships

### Cache Decorators and Utilities

- `@redis_cache` - Cache function results with configurable TTL
- `@with_redis_lock` - Execute functions with distributed locks
- Cache statistics tracking for monitoring performance

### Example Configuration

To configure the cache system, update your `.env` file:

```env
# Redis settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_SOCKET_TIMEOUT=5
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_RETRY_ON_TIMEOUT=true
REDIS_CONNECTION_POOL_SIZE=20
REDIS_MAX_CONNECTIONS=100
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


## Project Structure

The project is organized as follows:

```
chess_mate/            # Main package
├── core/              # Core functionality
│   ├── analysis/      # Chess analysis modules
│   ├── cache/         # Caching functionality
│   ├── models/        # Django models
│   ├── templates/     # HTML templates
│   ├── tests/         # Test suite
│   │   ├── standalone/  # Standalone tests (no Django)
│   │   └── ...        # Django-integrated tests
│   └── views/         # Django views
├── chess_mate/        # Django project settings
└── manage.py          # Django management script
```

## Setup

To set up the project for development:

1. Install the package in development mode:

```
python install_dev.py
```

This will install the package in development mode, allowing imports to work correctly.

## Running Tests

### Standalone Tests

To run standalone tests that don't require Django:

```
python run_standalone_tests.py
```

### Django Tests

To run Django-integrated tests:

```
python run_django_tests.py
```

### All Tests

To run all tests (both standalone and Django-integrated):

```
python run_tests.py
```

### Test Coverage

To run tests with coverage reporting:

```
python run_tests.py --coverage
```

To generate HTML coverage reports:

```
python run_tests.py --coverage --html
```

## Development Guidelines

- Use relative imports within the `chess_mate` package (e.g., `from ..models import Game`)
- Keep standalone tests independent of Django
- Add the appropriate marker to tests that require Django: `@pytest.mark.django_db`

## Common Issues

### Import Errors

If you encounter import errors, ensure you've installed the package in development mode:

```
python install_dev.py
```

### Django Settings Not Found

If Django settings are not found, ensure the `DJANGO_SETTINGS_MODULE` environment variable is set correctly:

```python
os.environ["DJANGO_SETTINGS_MODULE"] = "chess_mate.chess_mate.test_settings"
```

## Recent Improvements

### Security Enhancements
- Implemented `SecurityHeadersMiddleware` with Content-Security-Policy and other critical security headers
- Enhanced CSRF protection with proper settings and cookie security
- Added Redis-backed distributed rate limiting with endpoint-specific limits

### Performance Optimizations
- Created a comprehensive cache invalidation system with tag-based invalidation
- Implemented cache control headers for better browser caching
- Redesigned the `TaskManager` class for better reliability through caching

### Reliability Improvements
- Added fallback profile system for robust operation even with import errors
- Implemented graceful degradation for critical endpoints
- Enhanced error handling with detailed logging and user-friendly responses
- Created simplified API endpoints that don't rely on complex model relationships

### Code Quality
- Added type annotations throughout the codebase for better API contracts
- Created thorough docstrings for security-related and core functionality code
- Standardized error response formats and logging practices
- Implemented mypy type checking with custom configuration
