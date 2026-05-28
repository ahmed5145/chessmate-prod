# ChessMate V0.1 — Product Requirements Document

**Version**: 0.1 (MVP)
**Date**: April 27, 2026
**Status**: Pre-production → Target: Local excellence first, then deployment
**Author**: Working document

---

## 0. North Star

> A player uploads their last 10–30 games and receives a report so specific and accurate that they feel like they just had a session with a real coach — knowing exactly what to drill next and why.

Everything in V0.1 is evaluated against this sentence. If a feature doesn't serve it, it's cut.

---

## 1. The Honest Current State

The document says "324 tests passing" and "working." That's technically true and practically misleading. Here's what's actually broken:

| Thing | Claimed Status | Real Status |
|---|---|---|
| AI Feedback | ✅ Working | Generates something, but output is generic, unstructured, not actionable |
| Metrics Display | ✅ Parsed | Numbers render but convey no insight, no context, no guidance |
| Batch Analysis | ✅ Working | Runs per-game analysis separately — doesn't actually synthesize cross-game patterns |
| Feedback Page | ✅ Built | Dumps raw data, no narrative, no hierarchy of importance |
| UI | ✅ React app passing tests | Unprepared for real users |

**The conclusion:** The infrastructure layer is solid. The product layer is a prototype that doesn't deliver value. V0.1 is about building the product layer correctly.

---

## 2. What V0.1 Is — And Is Not

### V0.1 IS:
- Batch game analysis (5–30 PGN games uploaded at once)
- A single, well-designed coaching report per batch
- Clear metrics that explain *why* they matter
- Specific, prioritized training recommendations
- A UI that feels polished and professional

### V0.1 IS NOT:
- Real-time analysis
- Live game review
- Opening book preparation
- Endgame tablebase training
- Social/community features
- Mobile app
- Subscription/payments
- Monitoring/observability beyond basic logs

**Cut everything not on the IS list until post-V0.1.**

---

## 3. Core User Flow (V0.1)

```
1. User lands on homepage
        ↓
2. User registers / logs in
        ↓
3. User uploads 5–30 PGN games (or pastes PGN text)
        ↓
4. Loading state: "Analyzing your games..." (shows progress)
        ↓
5. Analysis Report page renders:
   ├── Executive Summary (2–3 sentences, what matters most)
   ├── Performance Radar / Overview metrics
   ├── Phase Breakdown (Opening / Middlegame / Endgame scores)
   ├── Critical Patterns (top 3–5 recurring weaknesses with examples)
   ├── Training Plan (prioritized, time-estimated, specific)
   └── Game-by-Game drill-down (collapsed by default)
        ↓
6. User can re-upload new batch → new report
```

No email notifications in V0.1. Results load on-page. Async is fine (polling) but user stays on the page.

---

## 4. The Analysis Pipeline — Rebuilt Correctly

This is the most important section. The current pipeline is wrong in its architecture. Here's what it should be.

### 4.1 What Stockfish Does (Objective Analysis)

For each game in the batch, Stockfish produces:

```json
{
  "game_id": "uuid",
  "total_moves": 42,
  "phase_breakdown": {
    "opening": { "moves": 12, "avg_eval_drop": 0.12, "blunders": 0, "mistakes": 1 },
    "middlegame": { "moves": 22, "avg_eval_drop": 0.41, "blunders": 2, "mistakes": 3 },
    "endgame": { "moves": 8, "avg_eval_drop": 0.89, "blunders": 1, "mistakes": 2 }
  },
  "move_quality": {
    "brilliant": 1,
    "best": 18,
    "excellent": 8,
    "good": 6,
    "inaccuracy": 5,
    "mistake": 6,
    "blunder": 3
  },
  "critical_moments": [
    {
      "move_number": 24,
      "phase": "middlegame",
      "type": "blunder",
      "eval_before": 0.8,
      "eval_after": -2.1,
      "eval_swing": 2.9,
      "fen": "...",
      "played_move": "Nxd5",
      "best_move": "Rd1",
      "tactical_theme": "loose_piece_oversight"
    }
  ],
  "tactical_patterns_missed": ["fork", "pin", "loose_piece"],
  "opening_name": "Sicilian Defense, Najdorf Variation",
  "opening_accuracy": 0.91,
  "result": "loss",
  "player_color": "white"
}
```

**This is purely objective. No AI involved at this stage.**

### 4.2 What the Aggregator Does (Cross-Game Pattern Detection)

This is a Python module (no AI, no external calls) that takes N per-game Stockfish results and produces:

```json
{
  "games_analyzed": 15,
  "date_range": "2026-01-01 to 2026-04-20",
  "overall_accuracy": 0.74,
  "win_loss_draw": { "wins": 7, "losses": 6, "draws": 2 },

  "phase_performance": {
    "opening": { "score": 0.88, "trend": "strong", "primary_openings": ["Sicilian Najdorf", "Ruy Lopez"] },
    "middlegame": { "score": 0.61, "trend": "inconsistent", "worst_aspect": "tactical_oversight" },
    "endgame": { "score": 0.44, "trend": "weak", "worst_aspect": "rook_endgames" }
  },

  "recurring_weaknesses": [
    {
      "pattern": "endgame_technique",
      "frequency": "9/15 games",
      "avg_eval_swing": 1.8,
      "impact": "critical",
      "example_game_ids": ["uuid1", "uuid3", "uuid7"]
    },
    {
      "pattern": "loose_piece_oversight",
      "frequency": "7/15 games",
      "avg_eval_swing": 2.1,
      "impact": "high",
      "example_game_ids": ["uuid2", "uuid5"]
    },
    {
      "pattern": "time_pressure_blunders",
      "frequency": "6/15 games",
      "impact": "high",
      "example_game_ids": ["uuid4", "uuid6"]
    }
  ],

  "strength_patterns": [
    { "pattern": "opening_preparation", "frequency": "13/15 games", "detail": "Consistently good through move 12" },
    { "pattern": "positional_understanding", "frequency": "10/15 games" }
  ],

  "most_common_blunder_type": "tactical_oversight",
  "worst_phase": "endgame",
  "best_phase": "opening",
  "estimated_elo_range": "1100-1250"
}
```

**Still no AI. This is deterministic Python logic from Stockfish data.**

### 4.3 The Single AI Call (Coaching Synthesis)

Only now do you call OpenAI. One call per batch. The prompt is structured:

```
System: You are a chess coach generating a detailed improvement report.
You will receive structured analysis data from Stockfish.
Your job is to synthesize this into actionable coaching.
You must respond ONLY with valid JSON matching the schema provided.
Do not add commentary outside the JSON.

User: [aggregated_metrics JSON from 4.2]

Schema to populate:
{
  "executive_summary": "string (2-3 sentences, most important insight)",
  "coaching_narrative": {
    "opening": "string (2-3 sentences)",
    "middlegame": "string (2-3 sentences)",
    "endgame": "string (2-3 sentences)"
  },
  "top_3_priorities": [
    {
      "rank": 1,
      "title": "string",
      "why_it_matters": "string",
      "how_to_fix": "string",
      "specific_drill": "string",
      "estimated_study_hours": number
    }
  ],
  "training_plan": {
    "week_1": "string",
    "week_2": "string",
    "week_3": "string",
    "week_4": "string"
  },
  "one_thing_to_do_today": "string"
}
```

**This is the ONLY AI call in the entire pipeline.** It's cheap (one call per batch, ~1000 input tokens + ~500 output), reliable (structured output with schema), and accurate because it's synthesizing real Stockfish data, not hallucinating chess analysis.

### 4.4 Why This Architecture Is Correct

| Old approach | New approach |
|---|---|
| AI analyzes chess moves | Stockfish analyzes chess moves |
| Multiple AI calls per game | One AI call per batch |
| AI produces chess evaluations | AI produces coaching language only |
| Unstructured AI output → parsing headaches | Schema-enforced JSON → zero parsing issues |
| Expensive at scale | ~$0.01–0.05 per batch |
| Hallucination risk on chess logic | AI only synthesizes, never analyzes |

### 4.5 Celery Task Design

```
Task: analyze_batch(batch_id, game_pgn_list, user_id)
  │
  ├── Step 1: Per-game Stockfish analysis (parallel subtasks, fan-out)
  │     analyze_single_game(game_id, pgn) × N
  │
  ├── Step 2: Aggregate results (single task, waits for all Step 1)
  │     aggregate_game_results(batch_id, [game_results])
  │
  ├── Step 3: Single AI coaching call
  │     generate_coaching_report(batch_id, aggregated_data)
  │
  └── Step 4: Store report, mark batch complete, notify frontend
```

Frontend polls `GET /api/batches/{batch_id}/status/` every 3 seconds.

---

## 5. Metrics — What to Show and How

The current metrics display fails because it shows numbers without meaning. Every metric needs context.

### 5.1 The Metrics That Actually Matter

**Don't show:** Raw centipawn evaluations, engine depth numbers, node counts, raw move counts.

**Do show:**

| Metric | Display Format | Context Text |
|---|---|---|
| Overall Accuracy | 74% with color (green/yellow/red) | "Average for your rating range: 71%" |
| Phase Scores | Three bars: Opening 88% / Middlegame 61% / Endgame 44% | Color-coded + brief label per phase |
| Blunder Rate | "2.1 blunders per game" | "Club players average: 3.2 — you're above average here" |
| Critical Moments | Top 3 worst moments with board preview | "Move 24: Lost 2.9 pawns of advantage in one move" |
| Improvement Potential | "+180 Elo possible by fixing top 2 weaknesses" | Calculated from eval swing data |
| Consistency | "High variance" / "Consistent" / "Streaky" | Based on std dev of move quality across games |

### 5.2 What the Feedback Page Layout Should Be

```
┌─────────────────────────────────────────────────────┐
│  COACHING REPORT — 15 games analyzed                │
│  [Executive Summary — 2-3 sentences, large text]    │
├────────────────┬────────────────────────────────────┤
│  Performance   │  Opening     ████████░░  88%       │
│  Radar         │  Middlegame  ██████░░░░  61%       │
│  (chart)       │  Endgame     ████░░░░░░  44%       │
├────────────────┴────────────────────────────────────┤
│  YOUR TOP 3 PRIORITIES                              │
│  ┌─────────────────────────────────────────────┐   │
│  │ 1. Endgame Technique  [CRITICAL]            │   │
│  │    Why: Happened in 9/15 games              │   │
│  │    Fix: [specific coaching text]            │   │
│  │    Drill: [specific drill]  ~10 hrs         │   │
│  └─────────────────────────────────────────────┘   │
│  [Same for #2 and #3]                              │
├─────────────────────────────────────────────────────┤
│  4-WEEK TRAINING PLAN                               │
│  Week 1: [text]  Week 2: [text]  ...                │
├─────────────────────────────────────────────────────┤
│  GAME-BY-GAME  [collapsed accordion]                │
│  Game 1 vs. opponent (W/L) — 74% accuracy  ▼       │
└─────────────────────────────────────────────────────┘
```

---

## 6. Technical Debt — What to Fix vs. Ignore

### Fix Before V0.1 Launch (Blocking User Value)

| Issue | Why Fix Now | Effort |
|---|---|---|
| Analysis pipeline architecture | Current approach doesn't aggregate cross-game patterns | 3–4 days |
| AI feedback schema enforcement | Current output is unstructured and unparseable reliably | 1 day |
| Metrics calculation rewrite | Current metrics don't translate to user-facing insight | 2 days |
| Feedback page UI | Current page dumps raw data | 3–4 days |
| PGN upload UX | Needs to handle multi-game PGN files cleanly | 1 day |
| Error states in UI | Upload failures, analysis failures need user-friendly messages | 1 day |

**Total: ~2 weeks of focused work**

### Ignore Until Post-V0.1

| Issue | Why Ignore Now |
|---|---|
| 371 mypy errors | Doesn't affect functionality |
| Flake8 lint debt | Doesn't affect functionality |
| Kubernetes configs | Single VPS is fine for MVP |
| Prometheus/Grafana | No users to monitor yet |
| Sentry | Add after deployment |
| Pre-commit strictness | Keep `STRICT_PRECOMMIT=0` |
| PostgreSQL migration | SQLite is fine for first 1000 users |
| Payment processing | No monetization in V0.1 |
| Email notifications | Not needed if results load on-page |

---

## 7. What Good Looks Like — Acceptance Criteria

Before V0.1 is considered ready, ALL of these must pass manual testing:

### Analysis Pipeline
- [ ] Upload 10 PGN games → receive a report that identifies at least 2 recurring patterns across games
- [ ] The AI coaching text references specific games/moves (not generic advice)
- [ ] Report generates in under 90 seconds for 15 games
- [ ] If Stockfish fails on one game, other games still complete
- [ ] Re-uploading same batch produces consistent results

### Metrics Display
- [ ] Every metric on screen has a label and a context sentence explaining it
- [ ] No raw centipawn values visible to user (translated to % accuracy or descriptive label)
- [ ] Phase breakdown scores feel accurate when manually verified against known games
- [ ] Critical moments section shows correct board position for the identified blunder

### Feedback Quality
- [ ] Show report to 3 chess players (any level) — all 3 say the priorities feel accurate
- [ ] Training plan recommendations are specific (not "study endgames" but "practice King+Rook vs King technique")
- [ ] Executive summary is 2-3 sentences and captures the single most important insight

### UI Polish
- [ ] Upload flow is intuitive without instructions
- [ ] Loading state communicates progress (not just a spinner)
- [ ] Report page hierarchy is clear — executive summary first, details later
- [ ] Works on both desktop and mobile viewport
- [ ] No raw JSON, IDs, or debug output visible anywhere

### Stability
- [ ] 50 manual test cycles (upload → analyze → view report) with zero crashes
- [ ] Handles malformed PGN gracefully (error message, not 500)
- [ ] Handles very short games (<10 moves) gracefully

---

## 8. Development Plan — Prioritized Task List

### Phase 1: Fix the Analysis Pipeline (Week 1–2)

**Day 1–2: Per-game Stockfish output schema**
- Define the exact JSON schema for per-game Stockfish output (section 4.1)
- Rewrite `stockfish_analyzer.py` to produce this exact schema
- Write 10 unit tests against known PGN games with known evaluations
- No AI, no aggregation yet — just Stockfish output quality

**Day 3–4: Aggregation module**
- Write `batch_aggregator.py` — pure Python, no external calls
- Input: list of per-game Stockfish JSON
- Output: cross-game patterns JSON (section 4.2)
- Write tests: 5 games with known patterns → aggregator detects them correctly
- Test edge cases: 1 game batch, all wins, all losses, mixed time controls

**Day 5: AI coaching call**
- Write `coaching_generator.py`
- Build the prompt template with schema enforcement
- Test with OpenAI: does it respect the schema? Does it produce specific advice?
- Iterate on prompt until output is specific and accurate
- Add fallback: if AI call fails, return a structured "we had trouble" message with the raw metrics

**Day 6–7: Celery task rewrite**
- Wire together: Stockfish → Aggregator → AI → Store
- Implement fan-out pattern for parallel per-game analysis
- Implement polling endpoint for frontend
- Test full pipeline end-to-end with 5 games, 10 games, 20 games

**Day 8: Error handling and edge cases**
- Malformed PGN: return error with line number
- Engine timeout: skip game, note in report
- OpenAI timeout: retry once, then serve report without coaching narrative
- Test all error paths

### Phase 2: Fix the Feedback Display (Week 2–3)

**Day 9–10: Metrics component rewrite**
- Strip current metrics display entirely
- Build new metrics components: RadarChart, PhaseBreakdown, BlunderRate
- Every number has a context label and comparative benchmark
- No raw engine data visible

**Day 11–12: Coaching report page**
- Executive Summary section (large, prominent)
- Top 3 Priorities (cards with rank, why, fix, drill, time estimate)
- 4-week training plan
- Game-by-game accordion (collapsed by default)
- Design reference: think Spotify Wrapped meets chess.com's post-game review

**Day 13: Critical moments viewer**
- Show top 3 worst moves from the batch
- Display board position at the moment of the blunder
- Show what they played vs what engine recommends
- Keep it simple — static board display is fine, not interactive

**Day 14: Upload flow polish**
- Drag-and-drop PGN file upload
- Multi-file support (each file = one game, or one file = multiple games with `[Event` headers)
- Paste PGN text as alternative
- File count display: "15 games loaded"
- Validation before submit: "3 games have incomplete data — continue anyway?"

### Phase 3: Integration and Polish (Week 3)

**Day 15–16: Full integration testing**
- Run 50 manual upload-to-report cycles
- Fix any crashes or data display bugs
- Verify report quality on games at different skill levels

**Day 17: Loading states and empty states**
- Progress indicator during analysis (steps: parsing → analyzing → generating)
- Empty state for new users with sample report
- Error states for all failure modes

**Day 18: UI audit**
- Mobile viewport check
- Typography and spacing consistency pass
- Ensure no raw data leaks into UI
- Performance check: report page should load in <1s after analysis completes

**Day 19–20: Buffer / catch-up**

### Phase 4: Deployment (Week 4)

Only start this after Phase 1–3 acceptance criteria are all met.

**Day 21: Local Docker prod test**
- `docker-compose -f docker-compose.prod.yml up`
- Run all acceptance criteria against Docker setup
- Fix anything that breaks

**Day 22: Server setup**
- DigitalOcean Droplet ($12/month, 2GB RAM) or AWS Lightsail
- Point domain
- Configure environment variables (SECRET_KEY, OPENAI_API_KEY, etc.)

**Day 23: Deploy**
- Push Docker image
- Run migrations
- Start services
- Verify all endpoints

**Day 24: Smoke test production**
- Upload 10 games on production
- Receive report
- Confirm quality matches local

**Day 25: Invite first 10 users**

---

## 9. The Restart Question — Final Answer

Restarting in FastAPI / Node.js / anything else would:
- Take 3–4 weeks to rebuild working infrastructure you already have
- Not solve the problem (the problem is product clarity, not tech stack)
- Lose working Stockfish integration, Celery pipeline, auth system
- Delay first real user feedback by 4–6 weeks

**The tech is not your bottleneck. An undefined product is your bottleneck.**

The analysis pipeline rebuild in this document takes 8 days. That's the real work. The rest is UI and deployment. The Django/Celery/Redis stack is actually well-suited to this exact workload — async batch processing is what Celery was built for.

**Restart only if**: after shipping V0.1 and getting user feedback, you discover the fundamental architecture needs to change. Make that decision from evidence.

---

## 10. Success Metrics for V0.1

| Metric | Target | How to Measure |
|---|---|---|
| Report accuracy | 80% of test users say priorities feel accurate | Manual survey of first 20 users |
| Report specificity | 0 reports with generic advice ("study more tactics") | Manual review |
| Pipeline reliability | <2% error rate on batch analysis | Log monitoring |
| Time to report | <90 seconds for 15 games | Timing logs |
| NPS from first users | >30 | Simple 1-question survey after first report |
| "Would you pay for this" | >50% of free users say yes | Survey at end of free trial |

---

## Appendix: Files to Write or Rewrite

| File | Action | Priority |
|---|---|---|
| `core/analysis/stockfish_analyzer.py` | Rewrite output schema | P0 |
| `core/analysis/batch_aggregator.py` | New file | P0 |
| `core/analysis/coaching_generator.py` | Rewrite (currently `feedback_generator.py`) | P0 |
| `core/tasks.py` | Rewrite Celery task structure | P0 |
| `frontend/src/components/Report/` | New component tree | P1 |
| `frontend/src/components/Upload/` | Rewrite upload flow | P1 |
| `frontend/src/components/Metrics/` | Rewrite metrics display | P1 |
| `core/analysis/metrics_calculator.py` | Update to output user-facing metrics | P1 |

---

*V0.1 goal: one user uploads their games, reads the report, and says "this is exactly what I needed to hear."*
*Everything else is secondary.*

## 12. Phase 1 Status
**Completed:** April 28, 2026
**Final test count:** 374 tests passing
**Phase 2 start state:** Backend API complete and hardened. All batch endpoints functional. Ready for frontend work.


---

## 11. Finalized Phase 1 Implementation Plan
*This section was locked after planning sessions on April 27, 2026. It is the canonical reference — do not deviate from it without updating this document.*

### Locked Decisions

**Batch size:** 5 minimum (hard reject with message: "Batch analysis requires at least 5 games to detect patterns."), 30 maximum (hard reject). No soft warning mode.

**Pipeline architecture:** Stockfish analyzes chess. AI writes coaching. Never reversed.
- Stockfish → per-game result schema
- Pure Python aggregator → cross-game patterns (no AI)
- One AI call per batch → coaching report only

**AI call:** OpenAI structured outputs with `strict: true`. Never prompt-only JSON mode. Target model: `gpt-4o-mini` or any model supporting structured outputs (not `gpt-3.5-turbo`).

**Explanation strings:** Template-generated in Python from `tactical_theme` + board context. No per-move AI calls.

**Elo estimation:** Removed entirely from all schemas.

**`worst_aspect` enum:** `tactical_oversight | time_pressure | positional | technique` only. Derived from most common tactical_theme in that phase's critical moments.

**`opening_accuracy` definition:** Percentage of opening-phase moves where the played move matched one of Stockfish's top-3 suggested moves at analysis depth. Moves not evaluated are excluded from the denominator.

**Opening detection:** Bundled offline ECO prefix dataset at `core/analysis/data/eco_openings.json`. Match first 6–10 plies. Use `eco_codes.py` for code-to-name lookup. Return `"Unknown"` if no match.

**Token efficiency:** AI prompt receives `per_game_summaries_json` (lightweight trimmed objects) not full `per_game_results`. Full Stockfish output goes to storage only.

**Partial batch success:** A batch with some failed games still produces a report if ≥5 games succeeded. Status enum: `pending | in_progress | partial | completed | failed`. `partial` = report generated despite failures. `failed` = fewer than 5 games succeeded, no report.

**Phase 1 hardening updates (April 28, 2026):**
- If OpenAI coaching generation fails, batch status must be `partial` (not `failed`) when aggregation succeeded with at least 5 valid games. Persist `batch_summary` and `per_game_results`, set `coaching_report = null`, and return normal report payload.
- Per-game analysis failure path must return a full schema-compliant envelope with safe defaults and `analysis_failed: true` so downstream aggregation can filter invalid entries deterministically.
- Batch aggregation must defensively validate required per-game fields (`game_id`, `phase_breakdown`, `move_quality`), log filtered malformed entries, and raise an aggregation validation error if fewer than 5 valid results remain.

**Known MVP limitation (accepted):** tactical theme detection is heuristic and may misclassify complex motifs; treat tactical labels as guidance, not ground truth.

**Ownership validation:** Every batch endpoint explicitly checks the requesting user owns the batch. Never implicit.

**URL convention:** All endpoints under existing `/api/v1/` namespace.

---

### File Plan

**Keep unchanged:**
- `chess_mate/core/analysis/stockfish_analyzer.py`
- `chess_mate/core/analysis/metrics_calculator.py`
- `chess_mate/core/eco_codes.py`
- `chess_mate/core/tasks.py` (existing single-game path untouched)

**Add:**
- `chess_mate/core/analysis/explanation_templates.py`
- `chess_mate/core/analysis/stockfish_game_result.py`
- `chess_mate/core/analysis/batch_aggregator.py`
- `chess_mate/core/analysis/coaching_generator.py`
- `chess_mate/core/analysis/coaching_schema.py`
- `chess_mate/core/analysis/data/eco_openings.json`
- `chess_mate/core/serializers_batches.py`
- `chess_mate/core/urls_batches.py`

**Extend:**
- `models.py:854` — add `batch_summary`, `per_game_results`, `coaching_report` JSONFields to `BatchAnalysisReport`. Do not touch `aggregate_metrics`.
- `chess_mate/core/tasks.py` — add `analyze_batch_task` and chord callback alongside existing single-game task

---

### API Endpoints

**POST `/api/v1/batches/`**
- Request: `{ "games": [{ "pgn": "..." }] }` or multipart PGN files
- Response: `{ "batch_id": 123, "status": "pending", "games_count": 15, "message": "Batch analysis started" }`
- Serializer: `BatchCreateSerializer`
- Validates batch size, PGN format, ownership by construction

**GET `/api/v1/batches/{batch_id}/status/`**
- Response: `{ "batch_id", "status", "progress", "completed_games", "total_games", "failed_games", "errors": [{ "game_id", "message", "code" }] }`
- Serializer: `BatchStatusSerializer`
- Ownership check required

**GET `/api/v1/batches/{batch_id}/report/`**
- Response: `{ "batch_id", "status", "batch_summary", "per_game_results", "coaching_report", "created_at", "updated_at" }`
- Serializer: `BatchAnalysisReportSerializer`
- Returns report for both `completed` and `partial` statuses
- Ownership check required

---

### Coaching JSON Schema (exact — do not modify without updating this doc)

```json
{
  "name": "batch_coaching_report",
  "strict": true,
  "schema": {
    "type": "object",
    "additionalProperties": false,
    "required": ["executive_summary", "coaching_narrative", "top_3_priorities", "training_plan", "one_thing_to_do_today"],
    "properties": {
      "executive_summary": { "type": "string" },
      "coaching_narrative": {
        "type": "object",
        "additionalProperties": false,
        "required": ["opening", "middlegame", "endgame"],
        "properties": {
          "opening": { "type": "string" },
          "middlegame": { "type": "string" },
          "endgame": { "type": "string" }
        }
      },
      "top_3_priorities": {
        "type": "array",
        "minItems": 3,
        "maxItems": 3,
        "items": {
          "type": "object",
          "additionalProperties": false,
          "required": ["rank", "title", "why_it_matters", "how_to_fix", "specific_drill", "estimated_study_hours"],
          "properties": {
            "rank": { "type": "integer", "enum": [1, 2, 3] },
            "title": { "type": "string" },
            "why_it_matters": { "type": "string" },
            "how_to_fix": { "type": "string" },
            "specific_drill": { "type": "string" },
            "estimated_study_hours": { "type": "number", "minimum": 0 }
          }
        }
      },
      "training_plan": {
        "type": "object",
        "additionalProperties": false,
        "required": ["week_1", "week_2", "week_3", "week_4"],
        "properties": {
          "week_1": { "type": "string" },
          "week_2": { "type": "string" },
          "week_3": { "type": "string" },
          "week_4": { "type": "string" }
        }
      },
      "one_thing_to_do_today": { "type": "string" }
    }
  }
}
```

---

### Coaching Prompt

**System:**
```
You are a chess coach generating a batch improvement report from structured analysis data.
Use only the provided aggregated metrics and per-game summaries. Do not invent openings, move numbers, tactical themes, or chess facts that are not present in the input. Be direct, specific, and practical. No generic advice. No motivational filler. No hedging. No markdown. No prose outside the JSON object.
Return only valid JSON that exactly matches the supplied schema. Every field is required. Use concise coaching language. If some games failed or data is missing, reflect that succinctly inside the JSON fields rather than outside the schema.
```

**User message template:**
```
Generate the batch coaching report from this data.

BATCH_SUMMARY_JSON:
{{ batch_summary_json }}

PER_GAME_SUMMARIES_JSON:
{{ per_game_summaries_json }}

FAILED_GAMES_JSON:
{{ failed_games_json }}

Return a JSON object that matches the coaching schema exactly.
```

---

### Per-Game Summary Shape (what goes to AI — not full Stockfish output)

```json
{
  "game_id": 123,
  "result": "loss",
  "opening_name": "Sicilian Defense, Najdorf Variation",
  "phase_breakdown": {
    "opening": { "score": 0.88 },
    "middlegame": { "score": 0.61 },
    "endgame": { "score": 0.44 }
  },
  "blunder_count": 3,
  "mistake_count": 6,
  "tactical_themes": ["fork", "hanging_piece", "pin"]
}
```

---

### Celery Task Structure

```
analyze_batch_task(batch_id, game_pgn_list, user_id)
  │
  ├── group(): analyze_single_game_subtask × N  [fan-out, parallel]
  │     Each returns: { "game_id", "status": "success|failed", "result": {...} | "error": "..." }
  │
  └── chord callback: aggregate_and_report_task(batch_id)
        ├── Filter successful results
        ├── If successful < 5: mark batch "failed", stop
        ├── batch_aggregator.aggregate(successful_results)
        ├── coaching_generator.generate(batch_summary, per_game_summaries)
        ├── Persist to BatchAnalysisReport
        └── Mark batch "completed" or "partial"
```

---

### Implementation Order (do not reorder)

1. Model migration — extend `BatchAnalysisReport`
2. `coaching_schema.py` — the JSON schema object above, nothing else
3. `explanation_templates.py` — template functions, no AI
4. `stockfish_game_result.py` — per-game Stockfish output builder
5. `batch_aggregator.py` — pure Python cross-game pattern detection
6. `coaching_generator.py` — single AI call with structured output
7. Celery tasks — `analyze_batch_task` + chord callback in `tasks.py`
8. Serializers — `BatchCreateSerializer`, `BatchStatusSerializer`, `BatchAnalysisReportSerializer`
9. Views + URL registration under `/api/v1/batches/`
10. Tests — completed, partial, and failed batch flows; single-game path regression

## Appendix: Files to Write or Rewrite

| File | Action | Priority |
|---|---|---|
| `core/analysis/stockfish_analyzer.py` | Rewrite output schema | P0 |
| `core/analysis/batch_aggregator.py` | New file | P0 |
| `core/analysis/coaching_generator.py` | Rewrite (currently `feedback_generator.py`) | P0 |
| `core/tasks.py` | Rewrite Celery task structure | P0 |
| `frontend/src/components/Report/` | New component tree | P1 |
| `frontend/src/components/Upload/` | Rewrite upload flow | P1 |
| `frontend/src/components/Metrics/` | Rewrite metrics display | P1 |
| `core/analysis/metrics_calculator.py` | Update to output user-facing metrics | P1 |

---

*V0.1 goal: one user uploads their games, reads the report, and says "this is exactly what I needed to hear."*
*Everything else is secondary.*
