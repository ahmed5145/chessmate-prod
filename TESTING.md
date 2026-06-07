# ChessMate Testing Guide

ChessMate uses **pytest** for the backend, **Jest + React Testing Library** for the frontend, and **GitHub Actions** (`ChessMate Tests` workflow) for CI. Coverage is uploaded to Codecov with separate `backend` and `frontend` flags (see `codecov.yml`).

## Test layout

```
chessmate_prod/
├── run_tests.py                          # Recommended backend test entrypoint
├── pytest.ini                            # Django test settings + test paths
├── .coveragerc                           # Backend coverage omits (aligned with Codecov)
├── standalone_tests/                     # Non-Django unit tests
├── chess_mate/core/tests/                # Main Django/pytest suite
├── chess_mate/core/analysis/tests/       # Analysis pipeline tests
├── chess_mate/frontend/src/**/__tests__/ # Jest tests (colocated)
└── tests/                                # Scripts against a *running* server (optional)
```

Test settings module: `chess_mate.chess_mate.test_settings` (in-memory SQLite, mocked externals where possible).

## Backend tests

### Quick start (all Django + standalone)

From the **repository root**:

```bash
python run_tests.py
```

### Django tests only

```bash
python run_tests.py --django
```

### Standalone tests only (no Django)

```bash
python run_tests.py --standalone
```

### Specific path or file

```bash
python run_tests.py --path chess_mate/core/tests/test_batch_compare.py
python run_tests.py --path standalone_tests/
```

### Direct pytest (equivalent)

```bash
python -m pytest chess_mate/core/tests chess_mate/core/analysis/tests -q
python -m pytest chess_mate/core/tests/test_game_views.py -q
python -m pytest standalone_tests/ -p no:django -q
```

### Coverage

```bash
python run_tests.py --django --coverage
python run_tests.py --coverage --html    # writes htmlcov/
```

Coverage config: `.coveragerc` at repo root. CI generates `coverage.xml` for Codecov (Python 3.11 job only).

### Useful pytest markers

Defined in `pytest.ini`:

| Marker | Use |
|--------|-----|
| `django_db` | Test needs database access |
| `standalone` | No Django required |
| `slow` | Long-running; skip with `-m "not slow"` |
| `integration` | External service integration |

Example:

```bash
python -m pytest chess_mate/core/tests -m "not slow" -q
```

### Writing backend tests

Prefer **pytest** with `@pytest.mark.django_db` when the database is required. Reuse fixtures from `chess_mate/core/tests/profile_helpers.py` and existing view test patterns.

```python
import pytest
from core.stats_helpers import _normalize_accuracy_value


def test_normalize_accuracy_scales_fractions():
    assert _normalize_accuracy_value(0.82) == 82.0


@pytest.mark.django_db
def test_user_games_endpoint(authenticated_client, test_game):
    response = authenticated_client.get("/api/v1/games/")
    assert response.status_code == 200
```

**Guidelines:**

- Mock Stockfish, OpenAI, and Stripe in unit tests; use real DB only when behavior depends on ORM queries.
- Pure helpers (`game_views._normalize_int_list`, `stats_helpers._normalize_accuracy_value`) should stay mock-free.
- Match existing naming: `test_<module>.py`, classes `Test<Feature>` optional.

## Frontend tests

From `chess_mate/frontend/`:

```bash
npm ci
npm test -- --watchAll=false
npm test -- --watchAll=false --coverage
npm run lint
npm run format:check
```

CI runs Jest with `--watchAll=false --coverage` on Node 18.

### Writing frontend tests

Tests live next to code under `src/**/__tests__/*.test.js`. Use React Testing Library; avoid `container.querySelector` (ESLint `testing-library/no-container`).

```javascript
import { render, screen } from '@testing-library/react';
import TrainingPlan from '../TrainingPlan';

it('renders week copy from coaching report', () => {
  render(
    <TrainingPlan
      coaching_report={{ training_plan: { week_1: 'Tactics daily' } }}
    />
  );
  expect(screen.getByText('Tactics daily')).toBeInTheDocument();
});
```

Mock `apiRequests`, `react-router-dom`, and heavy children (charts, FEN boards) the way existing batch report tests do.

**Note:** There is no Cypress suite in this repo today; E2E is manual or via the scripts below.

## Code quality (matches CI)

From repo root:

```bash
# Python
isort --check-only --profile black chess_mate/
black --check --line-length=120 chess_mate/
flake8 chess_mate/ --max-line-length=120

# Frontend
cd chess_mate/frontend && npm run lint
```

Pre-commit hooks: [docs/PRE_COMMIT.md](docs/PRE_COMMIT.md).

## CI pipeline

Workflow file: [.github/workflows/unified-test.yml](.github/workflows/unified-test.yml)

| Job | What it runs |
|-----|----------------|
| `backend-tests` | Python 3.10 & 3.11 — `python run_tests.py --django --coverage` |
| `frontend-tests` | Node 18 — `npm test -- --watchAll=false --coverage` |
| `linting` | flake8, isort, black, mypy, bandit, ESLint, Prettier |
| Codecov | Backend upload on 3.11; frontend when `CODECOV_TOKEN` is set |

Markdown-only changes do not trigger CI (`paths-ignore`).

## Manual / integration scripts

These are **not** part of the default pytest suite; they hit a running server or external Redis.

| Script | Purpose |
|--------|---------|
| `check_authentication.py` | JWT login/register/profile smoke tests |
| `jwt_debug.py` | Inspect or mint test JWTs |
| `test_api.py` | Broader API exercise (repo root) |
| `tests/test_health_checks.py` | Health endpoints against `--base-url` |
| `tests/test_cache_invalidation.py` | Cache behavior with live Redis |

Example:

```bash
# Terminal 1: python manage.py runserver  (from chess_mate/)
python check_authentication.py --base-url http://localhost:8000
python tests/test_health_checks.py --base-url http://localhost:8000
```

See [tests/README.md](tests/README.md) for more.

## Troubleshooting

### `Database access not allowed`

Add `@pytest.mark.django_db` to tests that touch the ORM, or use mocks for queryset code.

### Tests pass locally but fail in CI

- CI uses `chess_mate.chess_mate.test_settings` via `run_tests.py`.
- Run the same command locally: `python run_tests.py --django --coverage`.
- Frontend: use `--watchAll=false` (CI is non-interactive).

### Slow or hanging tests

- Mock Stockfish analysis and OpenAI calls.
- Use `-m "not slow"` or `pytest --durations=20` to find outliers.
- CI enables faulthandler after 120s for stuck tests.

### Frontend import / ESM errors

Jest uses `babel-jest` and `transformIgnorePatterns` in `package.json`. Run from `chess_mate/frontend` after `npm ci`.

### Coverage gaps

- Backend omits migrations, tests, scripts — see `codecov.yml` and `.coveragerc`.
- Frontend excludes `__tests__` and `*.test.js` from coverage collection (see `package.json` → `jest.collectCoverageFrom`).

## Related docs

- [README.md](README.md) — project overview
- [INSTALLATION.md](INSTALLATION.md) — local setup
- [docs/ci_cd.md](docs/ci_cd.md) — pipeline details
- [docs/PRE_COMMIT.md](docs/PRE_COMMIT.md) — hooks before commit
