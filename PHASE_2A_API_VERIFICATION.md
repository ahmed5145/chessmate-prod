# Phase 2A: API Rewiring - Verification Guide

## Summary

**Status**: Phase 2A (API Layer) implementation complete. Three new batch endpoints added to `src/services/apiRequests.js`. Four old batch functions marked deprecated.

**Files Modified**:
- `src/services/apiRequests.js` — Added 3 new functions, deprecated 4 old ones

## New API Functions (Phase 2)

### 1. `createBatch(pgnList)`
**Endpoint**: `POST /api/v1/batches/`

**Input**:
```javascript
pgnList: [
  "[Event \"Game 1\"]\n[Site \"...\"]\n...1.e4 e5...",
  "[Event \"Game 2\"]\n[Site \"...\"]\n...1.d4 d5...",
  ...
]
```

**Expected Response (202 Accepted)**:
```json
{
  "batch_id": "123e4567-e89b-12d3-a456-426614174000",
  "task_id": "celery-task-abc-xyz",
  "status": "pending",
  "games_count": 10
}
```

**Validation**: 5–30 games required; PGN format validated server-side.

---

### 2. `getBatchStatus(batchId)`
**Endpoint**: `GET /api/v1/batches/{batchId}/status/`

**Input**:
```javascript
batchId: "123e4567-e89b-12d3-a456-426614174000"
```

**Expected Response (200 OK)**:
```json
{
  "batch_id": "123e4567-e89b-12d3-a456-426614174000",
  "task_id": "celery-task-abc-xyz",
  "status": "in_progress",
  "games_count": 10,
  "completed_games": 5,
  "failed_games": 0,
  "progress": "5/10 games analyzed",
  "errors": []
}
```

**Status Values**:
- `"pending"` — Queued, not yet started
- `"in_progress"` — Actively analyzing
- `"completed"` — All games analyzed successfully
- `"partial"` — Some games analyzed; coaching may be unavailable
- `"failed"` — Analysis failed; insufficient successful games

---

### 3. `getBatchReport(batchId)`
**Endpoint**: `GET /api/v1/batches/{batchId}/report/`

**Input**:
```javascript
batchId: "123e4567-e89b-12d3-a456-426614174000"
```

**Expected Response (200 OK) — Completed**:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "task_id": "celery-task-abc-xyz",
  "status": "completed",
  "games_count": 10,
  "batch_summary": {
    "games_analyzed": 10,
    "overall_accuracy": 0.845,
    "date_range": "2025-01-01 to 2025-01-10",
    "win_loss_draw": {"wins": 6, "losses": 2, "draws": 2},
    "phase_performance": {
      "opening": 0.88,
      "middlegame": 0.82,
      "endgame": 0.80
    },
    "recurring_weaknesses": [...]
  },
  "per_game_results": [
    {
      "game_id": "game_0",
      "total_moves": 40,
      "result": "1-0",
      "player_color": "white",
      "opening_name": "Italian Game",
      "opening_accuracy": 0.92,
      "phase_breakdown": {...},
      "move_quality": {"blunder": 0, "mistake": 1, "inaccuracy": 4},
      "critical_moments": [...]
    },
    ...
  ],
  "coaching_report": {
    "executive_summary": "You demonstrated solid fundamental understanding...",
    "coaching_narrative": {
      "opening": "Your opening repertoire is well-prepared...",
      "middlegame": "You played competent middlegames overall...",
      "endgame": "Endgame execution was solid but conservative..."
    },
    "top_3_priorities": [
      {
        "rank": 1,
        "title": "Tactical Vision",
        "why_it_matters": "Missed 15% of tactical opportunities...",
        "how_to_fix": "Complete 5 tactical puzzles daily...",
        "specific_drill": "Lichess Puzzle Rush: 10 min daily...",
        "estimated_study_hours": 10
      },
      {...},
      {...}
    ],
    "training_plan": {
      "week_1": "Days 1-7: Daily tactical puzzles...",
      "week_2": "Days 8-14: Increase puzzle complexity...",
      "week_3": "Days 15-21: Full routine...",
      "week_4": "Days 22-28: Consolidate gains..."
    },
    "one_thing_to_do_today": "Play one serious game..."
  },
  "created_at": "2025-01-20T10:00:00Z",
  "updated_at": "2025-01-20T10:15:00Z"
}
```

**Expected Response (202 Accepted) — Still In Progress**:
```json
{
  "status": "in_progress",
  "message": "Analysis in progress"
}
```

**Expected Response (200 OK) — Partial (Coaching Failed)**:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "task_id": "celery-task-abc-xyz",
  "status": "partial",
  "games_count": 10,
  "batch_summary": {...},
  "per_game_results": [...],
  "coaching_report": null,
  "created_at": "2025-01-20T10:00:00Z",
  "updated_at": "2025-01-20T10:15:00Z"
}
```

**Key**: `coaching_report` is `null` when status = `partial` (coaching generation failed but analysis succeeded).

---

## Deprecated Functions (Phase 1 — Keep for Backward Compatibility)

All four functions still exist in apiRequests.js but are marked with `// DEPRECATED:` comments:

1. **`analyzeBatchGames(numGames, timeControl, includeAnalyzed, selectedGameIds)`**
   - Old endpoint: `POST /api/v1/games/batch-analyze/`
   - Use new: `createBatch()` instead

2. **`checkBatchAnalysisStatus(taskId)`**
   - Old endpoint: `GET /api/v1/games/batch-status/{taskId}/`
   - Use new: `getBatchStatus()` instead

3. **`fetchBatchReportHistory(limit)`**
   - Old endpoint: `GET /api/v1/games/batch-reports/`
   - Legacy query; not needed for Phase 2

4. **`fetchBatchReportById(reportId)`**
   - Old endpoint: `GET /api/v1/games/batch-reports/{reportId}/`
   - Use new: `getBatchReport()` instead

---

## Manual Verification Steps (Before Phase 2B)

### Prerequisites
- Backend running on `localhost:8000` or configured API_BASE_URL
- User authenticated with valid JWT token
- At least 5 test PGN files available

### Test 1: Create Batch
```bash
curl -X POST http://localhost:8000/api/v1/batches/ \
  -H "Authorization: Bearer {ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "games": [
      "[Event \"Test 1\"]\n...",
      "[Event \"Test 2\"]\n...",
      "[Event \"Test 3\"]\n...",
      "[Event \"Test 4\"]\n...",
      "[Event \"Test 5\"]\n..."
    ]
  }'
```

**Expected**: 202 response with `batch_id`, `status: "pending"`, `games_count: 5`

**Store**: `BATCH_ID` from response for next tests.

---

### Test 2: Poll Batch Status
```bash
curl -X GET http://localhost:8000/api/v1/batches/{BATCH_ID}/status/ \
  -H "Authorization: Bearer {ACCESS_TOKEN}"
```

**Expected**: 200 response with:
- `status: "in_progress"` or `"completed"` (depending on timing)
- `games_count: 5`
- `completed_games: N` (0-5)
- `progress: "N/5 games analyzed"`

**Polling**: Repeat every 3 seconds until `status` != `"in_progress"`.

---

### Test 3: Fetch Batch Report
```bash
curl -X GET http://localhost:8000/api/v1/batches/{BATCH_ID}/report/ \
  -H "Authorization: Bearer {ACCESS_TOKEN}"
```

**Expected (while in progress)**: 202 response with `{"status": "in_progress", "message": "..."}`

**Expected (when completed)**: 200 response with:
- `batch_summary` (all fields present)
- `per_game_results` array (length = games_count)
- `coaching_report` object OR `null` if partial
- `created_at`, `updated_at` timestamps

**Verify Structure**:
- `batch_summary.phase_performance` has `opening`, `middlegame`, `endgame` scores
- `coaching_report.top_3_priorities` is array of 3 objects with `rank`, `title`, `why_it_matters`, `how_to_fix`, `specific_drill`, `estimated_study_hours`
- `coaching_report.training_plan` has `week_1`, `week_2`, `week_3`, `week_4` strings
- All `per_game_results` items have `phase_breakdown`, `move_quality`, `critical_moments`

---

## Response Shape Differences from Backend

### createBatch (POST)
- Response status: **202 Accepted**
- Returns: `batch_id`, `task_id`, `status`, `games_count`
- **No** metadata dict; all fields at top level

### getBatchStatus (GET)
- Response status: **200 OK**
- Returns: `batch_id`, `task_id`, `status`, `games_count`, `completed_games` (count, not array), `failed_games` (count), `progress` (string), `errors` (array)
- **Note**: `completed_games` and `failed_games` are **counts**, not arrays

### getBatchReport (GET)
- Response status: **200 OK** (if completed/partial/failed) or **202 Accepted** (if pending/in_progress)
- Returns: `id`, `task_id`, `status`, `games_count`, `batch_summary`, `per_game_results`, `coaching_report` (may be null), `created_at`, `updated_at`
- **Note**: `coaching_report` is **null** when status = `partial`

---

## Success Criteria (Phase 2A Complete)

✅ All three endpoints return expected responses
✅ Status transitions work: pending → in_progress → completed/partial/failed
✅ Polling interval: 3 seconds (matches backend task update frequency)
✅ Error handling: 4xx, 5xx errors propagated correctly
✅ Ownership check: User can only see their own batches
✅ Coaching report is null when status = partial (graceful fallback)

---

## Frontend Implementation Dependency

**Phase 2B (Components) must wait until**:
- ✅ createBatch() tested and working
- ✅ getBatchStatus() polling confirmed reliable
- ✅ getBatchReport() returns full report structure
- ✅ null coaching_report handled (for partial status)

Once verified, proceed to Phase 2B: Create 8 new components.

---

## Notes for Implementation

1. **Error handling**: All three functions already include try-catch with descriptive error messages.
2. **Backward compatibility**: Old functions remain callable; no breaking changes.
3. **Polling strategy**: Use 3-second interval; stop when status ≠ pending/in_progress.
4. **Null coaching**: ExecutiveSummary, TopPriorities, TrainingPlan must show fallback UI when coaching_report is null.
5. **Phase breakdown**: batch_summary.phase_performance contains opening/middlegame/endgame (0–100 scale, user-facing).

---

**Next Step**: Verify all three endpoints manually against running backend, then proceed to Phase 2B component creation.
