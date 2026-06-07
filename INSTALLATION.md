# ChessMate Installation Guide

This guide covers local development setup on Windows, Linux, and macOS. For production deployment, see [docs/PROD_OPS.md](docs/PROD_OPS.md).

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **Python** | 3.10+ (CI tests 3.10 and 3.11) |
| **Node.js** | 18+ for the React frontend |
| **Git** | Clone and branch workflow |
| **Stockfish** | Required for game and batch analysis |
| **Redis** | Recommended for cache and Celery; can be disabled locally |
| **PostgreSQL** | Optional locally (SQLite default); used in production |

## 1. Clone and environment file

```bash
git clone https://github.com/ahmed5145/chessmate-prod.git
cd chessmate-prod
```

Copy the example env file and edit secrets:

```bash
cp .env.example .env
```

Important variables (see `.env.example` for the full list):

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Django secret |
| `REACT_APP_API_URL` | Frontend → API origin (e.g. `http://localhost:8000`) |
| `REDIS_DISABLED` | Set `True` if Redis is not running (in-memory cache; no Celery) |
| `STOCKFISH_PATH` | Path to the Stockfish binary |
| `OPENAI_API_KEY` | Batch coaching narrative (optional; statistical fallback without it) |
| `STRIPE_*` | Credit purchases (optional for local dev) |

Restart Django and any Celery workers after changing env values.

## 2. Python backend

### Windows (recommended)

From the repo root:

```bat
setup_windows.bat
```

This creates a venv, installs `requirements.txt`, runs migrations, and collects static files.

Start the API server:

```bat
run_development.bat
```

Django listens on http://127.0.0.1:8000/ by default.

### Windows / Linux / macOS (manual)

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
pip install -e .

mkdir -p chess_mate/logs chess_mate/media
cd chess_mate
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Optional: create an admin user:

```bash
python manage.py createsuperuser
```

## 3. React frontend

The SPA runs as a separate dev server:

```bash
cd chess_mate/frontend
npm install
npm start
```

Open http://localhost:3000/. Ensure `REACT_APP_API_URL` in `.env` points at your Django origin (no `/api` suffix).

Production builds:

```bash
npm run build
```

## 4. Stockfish

Install Stockfish and set `STOCKFISH_PATH` in `.env`.

**Linux (Debian/Ubuntu):**

```bash
sudo apt install stockfish
# Often: /usr/games/stockfish
```

**macOS (Homebrew):**

```bash
brew install stockfish
```

**Windows:** Download a build from [stockfishchess.org](https://stockfishchess.org/download/) or use WSL, then set `STOCKFISH_PATH` to the `.exe` path.

Verify:

```bash
# Linux/macOS example
"$STOCKFISH_PATH" --version
```

## 5. Redis and Celery (optional)

Batch analysis and background tasks use Celery with Redis as the broker.

**Quick local workaround** (no Redis):

```env
REDIS_DISABLED=True
ENABLE_CELERY=false
```

**Linux:**

```bash
sudo apt install redis-server
sudo service redis-server start
```

**Windows:** WSL + `redis-server`, or a native Windows port. See [Redis docs](https://redis.io/docs/install/).

With Redis running, start a worker from `chess_mate/`:

```bat
# Windows
start_celery.bat

# Linux/macOS (typical)
celery -A chess_mate worker -l info
```

## 6. OpenAI (batch coaching)

1. Create an API key in the [OpenAI dashboard](https://platform.openai.com/api-keys).
2. Add to `.env`:

   ```env
   OPENAI_API_KEY=sk-...
   ```

3. Restart Django and Celery.

Without a key, batch reports still complete using Stockfish metrics and statistical coaching text; AI narrative sections may be limited.

## 7. Stripe credits (optional)

For local payment flows, set test keys from the Stripe dashboard:

```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
PAYMENT_SUCCESS_URL=http://localhost:3000/payment/success
PAYMENT_CANCEL_URL=http://localhost:3000/payment/cancel
```

## Common issues

### `ModuleNotFoundError`

```bash
pip install -r requirements.txt
pip install -e .
```

Run commands from the repo root with the virtualenv activated.

### Database errors

**SQLite (default dev):** ensure `ENVIRONMENT=development` and run `python manage.py migrate` from `chess_mate/`.

**PostgreSQL:** create database `chessmate`, set `DB_*` in `.env`, then migrate.

### Redis connection errors

```env
REDIS_DISABLED=True
```

Or start Redis and set `REDIS_URL=redis://localhost:6379/0`.

### CORS / frontend cannot reach API

Check `.env`:

```env
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
REACT_APP_API_URL=http://localhost:8000
```

### Stockfish not found

Confirm `STOCKFISH_PATH` and that the binary is executable. Analysis endpoints will fail without a valid engine.

## Production (summary)

1. Install dependencies: `pip install -r requirements.txt` (see `requirements.txt` / deploy docs for prod extras).
2. Set `DEBUG=False`, strong `SECRET_KEY`, `ALLOWED_HOSTS`, database, Redis, and secrets via the host environment (never commit `.env`).
3. Run migrations, collect static files, and serve via your platform (Docker/EB — see `docs/PROD_OPS.md` and `chess_mate/deploy/`).

## Helper scripts (repo root)

| Script | Purpose |
|--------|---------|
| `setup_windows.bat` | Windows venv + deps + migrations |
| `setup.bat` | Lighter Windows venv setup |
| `run_development.bat` | Dev server with SQLite-friendly defaults |
| `run_tests.py` | Unified pytest runner (see [TESTING.md](TESTING.md)) |
| `load_env.py` | Load `.env.development` for local scripts |

## Next steps

- [TESTING.md](TESTING.md) — run backend and frontend tests
- [docs/api.md](docs/api.md) — API reference
- [docs/product/BATCH_ANALYSIS_FLOW.md](docs/product/BATCH_ANALYSIS_FLOW.md) — batch coaching user flow
