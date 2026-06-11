# Staging smoke test (pre-production)

Run on **staging** before merging to `main`. See [STAGING_SETUP.md](./STAGING_SETUP.md) for EB/RDS setup.  
Do **not** use `CELERY_TASK_ALWAYS_EAGER`.

**Environment:** `https://staging.chess-mate.online` (or `ChessMate-Staging` EB URL)  
**Date:** ___________________  
**Runner:** ___________________

## Prerequisites

- [ ] Health: `https://<staging-host>/health/` → `ok`
- [ ] Readiness: `.../readiness/` → `{"status":"ready"}`
- [ ] `ENABLE_CELERY=true` on EB + **redeploy** after adding it
- [ ] Redis: EB **`REDIS_URL=redis://127.0.0.1:6379/0`** + **`USE_BUNDLED_REDIS=true`** (free bundled Redis), or ElastiCache later
- [ ] Login hits **`/api/v1/auth/login/`** (not `/api/api/v1/...`) after latest CD deploy
- [ ] App UI loads at `/` or `/login` (not only `/admin/`)
- [ ] `/static/js/main.*.js` returns **200** (not 404) — WhiteNoise + `collectstatic` on deploy
- [ ] Test account with Lichess or Chess.com linked
- [ ] ≥30 imported games available

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

- [ ] All cases pass → OK to merge `staging` → `main` / deploy production  
- Failures logged as GitHub issues: ___________________
