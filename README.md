[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/ahmed5145/chessmate-prod.svg)](https://github.com/ahmed5145/chessmate-prod/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/ahmed5145/chessmate-prod.svg)](https://github.com/ahmed5145/chessmate-prod/network)
[![GitHub issues](https://img.shields.io/github/issues/ahmed5145/chessmate-prod.svg)](https://github.com/ahmed5145/chessmate-prod/issues)
![GitHub last commit](https://img.shields.io/github/last-commit/ahmed5145/chessmate-prod)
![CI Status](https://github.com/ahmed5145/chessmate-prod/workflows/ChessMate%20Tests/badge.svg)

# ChessMate: AI-Powered Chess Coaching

ChessMate analyzes your games with Stockfish and turns them into actionable coaching: single-game feedback, dashboard stats, and **batch coaching reports** that combine many games into one prioritized improvement plan.

## Features

- **Batch coaching reports** — Analyze 5–30 games at once; get executive summary, top priorities, phase breakdown, opening insights, recurring weaknesses, critical moments, and a 4-week training plan
- **Single-game analysis** — Move-level Stockfish evaluation with blunder/mistake classification and AI narrative feedback
- **Dashboard & stats** — Win rates, accuracy trends, opponent insights, and achievement tracking
- **Game import** — Fetch games from Chess.com and Lichess (credit-based)
- **Shareable batch reports** — Read-only public links for completed batch reports
- **Credits & payments** — Stripe-backed credit packages for analysis workloads
- **Modern UI** — React + Material UI batch report experience with mobile layout, print/PDF export, and saved report history
- **Production-ready backend** — JWT auth, Redis caching, Celery workers, health checks, and observability hooks

## Project structure

```
chessmate_prod/                 # Repository root
├── chess_mate/                   # Django project root (manage.py lives here)
│   ├── core/                     # Main app: models, views, analysis, batch pipeline
│   │   ├── analysis/             # Stockfish, metrics, coaching generators, ECO data
│   │   ├── tests/                # Backend pytest suite
│   │   └── migrations/
│   ├── chess_mate/               # Django settings (base, aws, test_settings)
│   └── frontend/                 # React SPA (Create React App)
├── docs/                         # API, ops, product, CI docs
├── standalone_tests/             # Lightweight non-Django tests
├── scripts/                      # Deploy and ops helpers
├── run_tests.py                  # Unified test runner (backend + coverage)
├── codecov.yml                   # Coverage upload config (backend + frontend flags)
└── .github/workflows/            # CI (Python 3.10/3.11, Node 18, lint, Codecov)
```

Auth, profiles, games, batches, credits, and dashboard APIs live under `chess_mate/core/` (for example `auth_views.py`, `game_views.py`, `views_batches.py`, `urls_batches.py`) rather than separate top-level Django apps.

## Prerequisites

| Component | Version / notes |
|-----------|-----------------|
| Python | 3.10+ (CI tests 3.10 and 3.11) |
| Node.js | 18+ (frontend build and Jest) |
| Redis | Recommended for cache and Celery (can be disabled locally via `REDIS_DISABLED=True`) |
| Stockfish | Required for engine analysis |
| PostgreSQL | Production; SQLite is fine for local development |

## Quick start

See [INSTALLATION.md](INSTALLATION.md) for full setup (Redis, Stockfish path, env files, Celery).

### Windows

```bat
git clone https://github.com/ahmed5145/chessmate-prod.git
cd chessmate-prod
setup_windows.bat
run_development.bat
```

Django runs at http://127.0.0.1:8000/ by default.

### Linux / macOS

```bash
git clone https://github.com/ahmed5145/chessmate-prod.git
cd chessmate-prod
pip install -e ".[dev]"
./setup.sh
cd chess_mate && python manage.py migrate && python manage.py runserver
```

### Frontend (separate dev server)

```bash
cd chess_mate/frontend
npm install
npm start
```

The React app typically runs at http://localhost:3000/ and talks to the Django API (configure `REACT_APP_API_URL` in `.env` if needed).

## Running tests

**Backend** (from repo root):

```bash
python run_tests.py --django --coverage
# or
python -m pytest chess_mate/core/tests -q
```

**Frontend**:

```bash
cd chess_mate/frontend
npm test -- --watchAll=false
npm run lint
```

CI runs backend tests on Python 3.10 and 3.11, frontend Jest + ESLint, and uploads coverage to Codecov (`backend` and `frontend` flags). See [TESTING.md](TESTING.md) and [docs/ci_cd.md](docs/ci_cd.md).

## Documentation

| Topic | Location |
|-------|----------|
| Installation | [INSTALLATION.md](INSTALLATION.md) |
| API reference | [docs/api.md](docs/api.md) |
| Product / batch flow | [docs/product/README.md](docs/product/README.md) |
| Security | [SECURITY.md](SECURITY.md), [API_SECURITY.md](API_SECURITY.md) |
| Testing | [TESTING.md](TESTING.md) |
| Monitoring | [docs/MONITORING.md](docs/MONITORING.md) |
| CI/CD | [docs/ci_cd.md](docs/ci_cd.md) |
| Pre-commit | [docs/PRE_COMMIT.md](docs/PRE_COMMIT.md) |
| Doc index | [docs/DOCS_STRUCTURE.md](docs/DOCS_STRUCTURE.md) |

## Technology stack

- **Backend**: Django, Django REST Framework, Celery, pytest
- **Frontend**: React 18, React Router, Material UI, Axios, Jest + Testing Library
- **Analysis**: Stockfish (depth-configurable), custom move classification and batch aggregation
- **Coaching AI**: OpenAI-backed narrative with statistical fallbacks when AI is unavailable
- **Data**: PostgreSQL (prod), SQLite (dev), Redis cache
- **Payments**: Stripe credit purchases
- **Observability**: Sentry (frontend), structured logging, health endpoints, Grafana/Prometheus assets in `grafana/`

## Contributing

1. Fork the repository and create a feature branch
2. Install dev dependencies (`pip install -e ".[dev]"`, `npm install` in `chess_mate/frontend`)
3. Run tests and lint before opening a PR
4. Follow [docs/PRE_COMMIT.md](docs/PRE_COMMIT.md) for hooks (black, isort, flake8, etc.)

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- [Stockfish](https://stockfishchess.org/) for engine analysis
- Django / DRF ecosystem
- OpenAI for coaching narrative generation
- Chess.com and Lichess APIs for game import

---

Questions, bugs, or ideas: [open an issue](https://github.com/ahmed5145/chessmate-prod/issues) or a pull request on GitHub.
