# Staging smoke test (pre-production)

Run on **staging** with real Celery worker, Redis, Stockfish, and OpenAI.  
Do **not** use `CELERY_TASK_ALWAYS_EAGER`.

**Environment:** ___________________  
**Date:** ___________________  
**Runner:** ___________________

## Prerequisites

- [ ] Staging URL: `https://___________________`
- [ ] Test account with Lichess or Chess.com linked
- [ ] ≥30 imported games available
- [ ] `HEALTHCHECK_URL` / `curl https://<host>/readiness/` returns `{"status":"ready"}`

## Cases

| ID | Pass | Notes / batch_id |
|----|------|------------------|
| S1 Happy path (15 games) | ☐ | |
| S2 Max batch (30 games) — record wall time: _____ min | ☐ | |
| S3 Min batch (5 games) | ☐ | |
| S4 Ownership (404 for other user) | ☐ | |
| S5 Partial coaching (no report, analysis visible) | ☐ | |
| S6 Failed games show **reason** in UI (P0-1) | ☐ | |
| S7 &lt;5 successes → `failed` | ☐ | |

## Infrastructure (P0-3)

- [ ] Celery worker running: `systemctl status chessmate-celery-worker` (or equivalent)
- [ ] Redis reachable
- [ ] Stockfish path valid (`STOCKFISH_PATH`)
- [ ] No `TimeLimitExceeded` in failed game messages for S2

## Sign-off

- [ ] All cases pass → OK to deploy production  
- Failures logged as GitHub issues: ___________________
