# ChessMate Launch Contract (P0 Must-Haves)

**Status:** Draft — pre-launch  
**Goal:** Ship a trustworthy batch analysis v1 without scope creep.  
**Out of scope for this contract:** Legacy `game_views` removal, coaching-only regenerate endpoint, Sentry/K8s, framework changes.

---

## Investigation summary (current state)

| Area | What exists today | Gap |
|------|-------------------|-----|
| Failed-game reasons | Celery persists `failed_games: [{game_id, error}]` on `BatchAnalysisReport` | Report API omits field; UI loses data after final report load |
| Status API | `GET .../status/` returns `errors: [{game_id, message}]` | Tests don’t assert `errors`; in-progress poll uses this, then report overwrites state |
| Frontend | Retry buttons + count (`N failed`) | No list of reasons; `applyBatchReport` only reads `report.failed_games` (often empty) |
| Game IDs in failures | Subtasks use `game_0`…`game_N` | Batches created via `game_ids` don’t surface DB/Lichess IDs in failures (follow-up, not P0 blocker) |
| `partial` status | Two meanings in backend: (A) coaching failed, (B) some games failed | Frontend disambiguates coaching via `!coaching_report`; undocumented |
| Celery limits | Global `CELERY_TASK_TIME_LIMIT=300s` per task | Subtasks + `aggregate_and_report_task` (OpenAI) each subject to 300s; batch chord itself is short |
| CD health gate | Post-deploy `curl` loop exists | `HEALTHCHECK_URL` unset → **skips check and exits 0** |
| Staging proof | `test_batch_integration.py` (eager Celery), `tests/test_health_checks.py` (manual) | No documented staging E2E run against real worker + Stockfish |

---

## P0-1: Surface per-game failure reasons (#6)

### Target state (acceptance criteria)

**Backend**

- [ ] `GET /api/v1/batches/{id}/report/` includes failure details when `failed_games` is non-empty.
- [ ] Response shape (stable contract):

```json
{
  "status": "completed" | "partial",
  "failed_games": [
    { "game_id": "game_3", "error": "Stockfish timeout after 240s" }
  ],
  "errors": [
    { "game_id": "game_3", "message": "Stockfish timeout after 240s" }
  ]
}
```

- [ ] `errors` mirrors status endpoint (`error` → `message`) so frontend uses one normalizer.
- [ ] `failed_games` count in DB unchanged; serializer does not strip `error` keys.

**Frontend**

- [ ] Results page shows a **“Failed games”** section when `failedGames.length > 0`:
  - MUI `Alert` severity `error` or neutral `Paper` + `List`
  - Each row: **Game** label + **reason** (message/error)
  - Placed **above** retry buttons, below subtitle (`X analyzed • Y failed`)
- [ ] After report load, failure list still visible (not only during polling).
- [ ] `normalizeFailedGames(raw)` accepts: `string[]`, `{game_id}`, `{game_id, error}`, `{game_id, message}`.
- [ ] `applyBatchReport`: prefer `report.errors` ?? `report.failed_games`; never clear known failures with empty array.

**Tests**

- [ ] `test_get_batch_report_includes_failed_games_and_errors` (backend)
- [ ] `test_get_batch_status_includes_errors` (backend — extend existing status test)
- [ ] Jest: renders failure reason text from `failed_games` / `errors` in report fixture

### Implementation plan

1. **`BatchAnalysisReportSerializer`** (`serializers_batches.py`)
   - Add `failed_games` to `Meta.fields` (pass-through JSON).
   - Add `SerializerMethodField` `errors` reusing same logic as `BatchStatusSerializer.to_representation` (extract shared `_failed_games_to_errors(failed_list)` to avoid drift).

2. **`getBatchReport`** (`apiRequests.js`)
   - Map `failed_games` and `errors` through on return object (document in JSDoc).

3. **`BatchAnalysisResults.js`**
   - Add `normalizeFailedGames()` near `extractUserMessage`.
   - Update `applyBatchReport` to use it.
   - Add `FailedGamesList` inline block or `components/batch/FailedGamesList.js` (prefer small sub-component if >30 lines).

4. **Optional P0 polish:** Display `game_id` as “Game 4 (index 5)” if id matches `/^game_\d+$/`; link to saved game when `batch.game_ids` maps index → DB id (defer if >2h).

### Definition of done

Manual: Run a batch where 1–2 PGNs are invalid or force subtask failure; on completion, user sees game id + human-readable error without opening network tab.

---

## P0-2: Staging smoke test (real async path)

### Target state (acceptance criteria)

- [ ] `docs/STAGING_SMOKE.md` checklist executed once on **staging** before production deploy.
- [ ] All cases pass with **real** Celery worker, Redis, Stockfish, OpenAI (not `CELERY_TASK_ALWAYS_EAGER`).
- [ ] Results recorded (date, env, batch IDs, pass/fail) in checklist or deploy log.

### Test matrix (minimum)

| # | Scenario | Steps | Expected |
|---|----------|-------|----------|
| S1 | Happy path | Connect account → select **15** games → batch analyze → wait | `status=completed`, coaching report populated |
| S2 | Max batch | **30** games | Completes within acceptable wall time (see P0-3 budget) |
| S3 | Min batch | **5** games | `completed` |
| S4 | AuthZ | User A creates batch; User B `GET .../status/` and `.../report/` | **404** |
| S5 | Partial coaching | Force OpenAI failure (invalid key on staging **or** known bad payload in test env only) | `partial`, analysis visible, regenerate CTA, **no** coaching-only false banner when coaching exists |
| S6 | Failed games UX | Batch with ≥1 subtask failure (bad PGN in upload path) | P0-1 failure list shows reasons |
| S7 | Insufficient success | Batch where &lt;5 games succeed | `failed`, clear message |

### Implementation plan

1. Add `docs/STAGING_SMOKE.md` (copy matrix + sign-off table).
2. No automation required for v1; optional follow-up: `scripts/staging_smoke.sh` hitting API with JWT.
3. Run after staging deploy, before promoting to production.

### Definition of done

Signed checklist attached to release (PR comment or `STAGING_SMOKE.md` filled date).

---

## P0-3: Verify batch completes under production Celery limits

### Target state (acceptance criteria)

- [ ] Documented **wall-clock budget**: 30-game batch completes on staging/prod worker SKU within **45 minutes** (adjust after first real run).
- [ ] No silent mass `failed` subtasks due to 300s `time_limit` under normal games.
- [ ] `aggregate_and_report_task` does not hit 300s during normal OpenAI coaching call.

### Investigation findings

- `analyze_batch_task` only schedules chord; not long-running.
- `analyze_single_game_subtask` inherits **300s hard / 240s soft** limit per game (parallel).
- `aggregate_and_report_task` runs aggregation + **one** OpenAI call in same task → **most likely timeout risk**.
- `analyze_batch_task` / subtasks are **not** routed to `batch_analysis` queue in `celery.py` (only legacy task names) — verify workers consume default queue.

### Implementation plan

1. **Measure on staging (S2):** Log batch `task_id`, start/end, `games_count`, final `status`. Note any `failed_games` with `TimeLimitExceeded` or similar in error text.

2. **If aggregate timeouts observed:**
   - Raise limits **only** for `aggregate_and_report_task`, e.g. `soft_time_limit=600`, `time_limit=660`.
   - Keep subtask limits at 300s unless single games routinely exceed (then 420s subtask).

3. **If worker queue backlog:**
   - Add routes: `analyze_batch_task`, `analyze_single_game_subtask`, `aggregate_and_report_task` → `batch_analysis` queue.
   - Confirm EB/systemd runs worker with `-Q batch_analysis,default` (or dedicated worker).

4. **Document** limits and queue in `docs/STAGING_SMOKE.md` § Infrastructure.

### Definition of done

S2 (30 games) passes on staging; no timeout errors in `failed_games` for standard Lichess rapid games; aggregate task completes.

---

## P0-4: Post-deploy health check gate

### Target state (acceptance criteria)

- [ ] Production/staging CD **fails** if health check fails after deploy (when env is production or staging deploy path).
- [ ] `HEALTHCHECK_URL` set in GitHub **Environment** secrets/vars:
  - **Recommended:** `https://<host>/readiness/` (JSON `{"status":"ready"}`) — validates DB + cache + Redis.
  - **Minimal:** `https://<host>/health/` (body `ok`) — liveness only.
- [ ] CD does **not** skip check silently in production: if URL unset on `main`/production deploy, **fail with clear message** (or require var).

### Investigation findings

`.github/workflows/cd.yml` lines 194–196: empty `HEALTHCHECK_URL` → skip, exit 0.

Readiness lives at **`/readiness/`** (root) and **`/api/v1/health/readiness/`** (API prefix).

### Implementation plan

1. Set `HEALTHCHECK_URL` in GitHub Environment `staging` and `production`.
2. **CD change (small):**
   ```yaml
   # For production/staging deploy jobs, after deploy:
   - if HEALTHCHECK_URL empty and DEPLOY_ENV != 'skip': fail
   - curl -fsS expects 2xx; readiness returns 503 when not ready → fail deploy
   ```
3. Optional: second check `curl -fsS "$URL/api/v1/health/detailed/"` for Celery status (nice-to-have).

### Definition of done

Intentionally break Redis on staging → deploy or post-deploy step fails; fix Redis → pass.

---

## P0-5: `partial` status semantics (document + guardrails)

### Target state (acceptance criteria)

- [ ] Team doc table in this file (below) referenced from `tasks.py` and `.cursor/rules/batch-invariants.mdc`.
- [ ] Frontend never shows **Regenerate Coaching** when `coaching_report` is present (already `!hasRawCoach`).
- [ ] Frontend shows **failure list** for game-level failures regardless of coaching (P0-1).
- [ ] No backend status split required for v1.

### Status matrix (canonical)

| `status` | `coaching_report` | `failed_games` | User-facing meaning | UI |
|----------|-------------------|----------------|---------------------|-----|
| `completed` | present | empty | Full success | Full report |
| `completed` | present | non-empty | Report + some games skipped/failed | Report + **Failed games** list |
| `partial` | **null** | any | Analysis OK; coaching failed | Warning banner + **Regenerate Coaching** |
| `partial` | present | non-empty | *(legacy path)* Some games failed; coaching OK | Report + failures; **no** regenerate banner |
| `failed` | — | — | &lt;5 successes | Error + retry guidance |

**Note:** Backend currently sets `partial` when `failed_results != []` even if coaching succeeded. Frontend relies on `coaching_report` for regenerate UX — **acceptable for v1** if P0-1 ships and matrix is documented.

### Implementation plan

1. Add comment block above `final_status = ...` in `aggregate_and_report_task` linking to this matrix.
2. Add one integration test: `partial` + coaching present + failed_games → report returns both.
3. Update `batch-invariants.mdc` with matrix reference (one paragraph).

### Definition of done

Reviewer can predict UI from `status` + `coaching_report` + `failed_games` without reading component code.

---

## Quick wins bundled with P0 (same PR acceptable)

| Item | Change | File(s) |
|------|--------|---------|
| 50 vs 30 picker | Cap selection at **30** everywhere | `BatchAnalysis.js` (`toggleSelectedGame`, `selectRecentGames`) |
| Regenerate honesty | Confirm dialog: “Re-analyzes all selected games (Stockfish + coaching).” | `BatchAnalysisResults.js` confirm copy |
| Status test gaps | Assert `errors` in status test | `test_views_batches.py` |

---

## Suggested execution order

```
Day 1 AM   P0-1 backend (serializer + tests)
Day 1 PM   P0-1 frontend (list UI + normalizer + tests)
Day 1 EOD  Quick wins (50→30, regenerate copy)
Day 2 AM   P0-4 (HEALTHCHECK_URL + CD strict mode)
Day 2 PM   Deploy staging → P0-2 smoke + P0-3 timing (S2 30-game)
Day 3      Fix timeouts/queues if S2 fails; sign contract; production deploy
```

---

## Sign-off

| P0 | Owner | Staging verified | Prod verified | Date |
|----|-------|------------------|---------------|------|
| P0-1 Failure reasons | | ☐ | ☐ | |
| P0-2 Smoke test | | ☐ | ☐ | |
| P0-3 Celery limits | | ☐ | ☐ | |
| P0-4 Health gate | | ☐ | ☐ | |
| P0-5 Partial docs | | ☐ | ☐ | |

**Release is blocked until all P0 rows are checked on staging and P0-1 + P0-4 are checked on production.**
