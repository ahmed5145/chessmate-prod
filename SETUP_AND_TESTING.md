# Setup and testing (moved)

This guide was split and updated. Use these instead:

| Topic | Document |
|-------|----------|
| Local install, env, Stockfish, Redis, frontend | [INSTALLATION.md](INSTALLATION.md) |
| pytest, Jest, CI, coverage, writing tests | [TESTING.md](TESTING.md) |
| Project overview | [README.md](README.md) |
| Pre-commit hooks | [docs/PRE_COMMIT.md](docs/PRE_COMMIT.md) |
| Health checks (runtime) | [tests/README.md](tests/README.md) |
| Full doc index | [docs/DOCS_STRUCTURE.md](docs/DOCS_STRUCTURE.md) |

**Quick commands** (from repo root):

```bash
# Backend
python run_tests.py --django

# Frontend
cd chess_mate/frontend && npm test -- --watchAll=false
```
