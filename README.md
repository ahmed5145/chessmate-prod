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

- **Game Analysis**: Detailed analysis of chess games using Stockfish engine
- **Performance Tracking**: Track your progress and identify improvement areas
- **Personalized Training**: Get custom training plans based on your weaknesses
- **Multi-Platform Support**: Import games from Chess.com and Lichess
- **Credit System**: Flexible credit packages for game analysis
- **Modern UI**: Responsive design with real-time updates
- **Secure Authentication**: JWT-based authentication system
- **Optimized Caching**: Redis-powered caching with intelligent invalidation

## Project Structure

```
chess_mate/           # Main Django application directory
├── core/             # Core application modules
│   ├── analysis/     # Chess analysis modules
│   ├── auth/         # Authentication functionality
│   ├── profiles/     # User profiles and settings
│   └── api/          # API endpoints
├── frontend/         # React frontend application
├── docs/             # Documentation files
├── tests/            # Test suites
└── scripts/          # Utility scripts
```

## Prerequisites

- Python 3.8+
- Node.js 14+
- Redis Server
- Stockfish Chess Engine
- PostgreSQL (optional, SQLite by default)

## Quick Start

For comprehensive installation instructions, see our [Installation Guide](INSTALLATION.md).

```bash
# Clone the repository
git clone https://github.com/yourusername/chessmate.git
cd chessmate

# Setup and run (Windows)
setup_windows.bat
run_development.bat

# Setup and run (Linux/Mac)
pip install -e ".[dev]"
./setup.sh
python manage.py runserver
```

## Documentation

- [Installation Guide](INSTALLATION.md) - Detailed installation instructions
- [API Documentation](docs/api.md) - Complete API reference
- [Security](SECURITY.md) - Security features and configurations
- [Testing Guide](TESTING.md) - Testing framework and guidelines
- [Monitoring](docs/MONITORING.md) - Logging and monitoring
- [CI/CD Pipeline](docs/ci_cd.md) - Continuous Integration setup
- [Pre-Commit Hooks](docs/PRE_COMMIT.md) - Development workflow
- [Documentation Structure](docs/DOCS_STRUCTURE.md) - Overview of documentation organization

## Technology Stack

- **Backend**: Django, Django REST Framework, Celery
- **Frontend**: React, Redux, Material-UI
- **Database**: PostgreSQL (production), SQLite (development)
- **Caching**: Redis
- **Analysis**: Stockfish Chess Engine
- **AI**: OpenAI GPT models for game feedback
- **Authentication**: JWT-based authentication

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

Please refer to our [Pre-Commit Hooks](docs/PRE_COMMIT.md) documentation for development workflow.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Django and Django REST Framework for the web framework
- OpenAI for the chess analysis capabilities
- PostgreSQL and Redis for data storage
- Stockfish for chess engine analysis

---

For issues, feature requests, or contributions, please open an issue or pull request on GitHub.
