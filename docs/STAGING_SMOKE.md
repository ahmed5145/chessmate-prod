# Production smoke test (pre-launch)

Use when you have **no staging environment**. Run on **production** with your own account.  
Do **not** use `CELERY_TASK_ALWAYS_EAGER`.

**Environment:** `http://chessmate-prod.us-east-2.elasticbeanstalk.com` (or custom domain)  
**Date:** ___________________  
**Runner:** ___________________

## Prerequisites

- [x] Health: `http://chessmate-prod.us-east-2.elasticbeanstalk.com/health/` → `ok`
- [x] Readiness: `.../readiness/` → `{"status":"ready"}`
- [ ] `ENABLE_CELERY=true` on EB + **redeploy** after adding it
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

- [ ] All cases pass → OK to deploy production  
- Failures logged as GitHub issues: ___________________
