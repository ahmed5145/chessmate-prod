# ChessMate Product & Delivery Contract

**Version:** 1.1  
**Date:** 2026-06-04  
**Status:** Active — governs what we ship, how we measure it, and what “done” means  
**Audience:** Product, engineering, and anyone deciding what users pay for  

**Related docs:** [PRD.md](./PRD.md), [../PROD_OPS.md](../PROD_OPS.md)

---

## 1. Purpose of this contract

This document consolidates:

- What ChessMate **promises** users (especially paid batch coaching).
- What the **codebase actually does** today.
- Where **metrics and AI** are trustworthy vs misleading.
- A **phased product map** (depth + breadth) aligned with the sole market differentiator: **cross-game coaching grounded in engine truth, not generic advice.**

It is the reference for prioritization, acceptance testing, and pricing conversations. When PRD and implementation disagree, this contract names the gap explicitly until resolved.

---

## 2. Product vision & differentiator

### Vision

Turn a player’s recent games into one report that answers: *What do I keep doing wrong, in which openings and endgames, with which moves as proof — and what should I study next?*

### Differentiator (what users pay for)

| Competitors (free) | ChessMate (paid) |
|--------------------|------------------|
| Per-game engine lines | **Cross-game patterns** across 5–30 games |
| Generic “accuracy %” | **Named openings**, **endgame types**, **cited moments** (game + move) |
| Template tips | **Coach narrative** calibrated to rating — **must cite supplied data** |

### Non-differentiator (table stakes, not marketing)

- Import PGN / Chess.com
- Single-game Stockfish analysis
- Account, credits, password reset

---

## 3. Current system map (repository truth)

### 3.1 User-facing surfaces

| Route / surface | Backend | Primary value today |
|-----------------|---------|---------------------|
| `/batch-analysis` → `/batch-report/:id` | `analyze_batch_task`, batch API | **Core paid loop** — Stockfish batch + OpenAI coaching |
| `/batch-analysis/results/...` | Same API, richer **legacy UI** (`BatchAnalysisResults.js`) | Charts, partial coaching regen — **duplicate UX** |
| `/game/:id/analysis` | `GameAnalyzer`, tasks | Single-game engine + optional AI feedback |
| `/games`, `/fetch-games` | `chess_services`, imports | Game library |
| `/dashboard` | `dashboard_views` | Stats from **older** analysis model — may not reflect batch coach |
| `/credits`, Stripe webhooks | `profile_views` | Monetization |
| Landing | Marketing copy | Promises “AI coach” — must match batch report quality |

### 3.2 Analysis pipelines (three parallel worlds)

```
┌─────────────────────────────────────────────────────────────────┐
│ A. Batch pipeline (batch report)                                 │
│    PGN → stockfish_game_result.build_game_result(depth=14)        │
│         → aggregate_batch() → generate_coaching_report(gpt-4o-mini)│
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ B. Single-game pipeline (GameAnalyzer + StockfishAnalyzer)       │
│    Different move classification (cp thresholds, "best" label)   │
│    → MetricsCalculator → feedback / GameAnalysisResults          │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ C. Legacy / dashboard aggregates (game_views batch metrics)      │
│    Heuristic enrichment, phase accuracy from stored analyses     │
└─────────────────────────────────────────────────────────────────┘
```

**Contract rule (target state):** One classification and accuracy definition for batch; single-game may differ short-term but must be **labeled** in UI (“batch uses depth-14 coach model”).

### 3.3 AI usage today

| Call site | Model | Input | Output | User-visible |
|-----------|-------|-------|--------|--------------|
| `coaching_generator.generate_coaching_report` | `gpt-4o-mini` | `batch_summary` + trimmed per-game summaries | Strict JSON: executive summary, narratives, top 3 priorities, 4-week plan, do today | `/batch-report` |
| `ai_feedback` / `feedback_generator` | ~`gpt-3.5-turbo` | Single-game metrics + moves | Prose feedback sections | Game feedback / analysis views |
| `game_analyzer` | ~`gpt-3.5-turbo` | Analysis summary | Text feedback | Single-game path |

**Not using AI today (engine-only):** move classification in batch, `recurring_weaknesses`, `opening_insights`, `endgame_insights`, critical moments, phase scores.

### 3.4 AI expansion plan (agreed direction)

Expand AI **only where it synthesizes engine facts** — never to invent moves or stats.

| Phase | AI responsibility | Engine responsibility |
|-------|-------------------|------------------------|
| **Now** | Coach JSON from batch_summary + summaries | All numbers, moments, patterns |
| **Next** | Per-priority “why” with `game_id` + move; weekly plan tied to `opening_insights` / `endgame_insights` | Same + richer summaries in prompt |
| **Then** | Optional: per-game 2–3 sentence “coach note” on worst moment | FEN, eval, classification |
| **Then** | “Regenerate coaching only” (no Stockfish re-run) | Frozen `per_game_results` |
| **Later** | Compare two batches (“improved in X”) | Diff on structured fields only |
| **Avoid** | Classifying tactics or accuracy from LLM | — |

---

## 4. Metrics contract

### 4.1 Definitions we expose (batch report)

| Metric | Formula (current code) | User-facing label | Trust level |
|--------|------------------------|-------------------|-------------|
| `overall_accuracy` | Weighted avg of `(1 - avg_eval_drop)` per phase move | “Overall accuracy” | **Medium** — not Chess.com ACPL accuracy |
| Phase `score` | `1 - avg_eval_drop` for moves in phase | “Opening 87%” | **Medium** — drops are pawn-scale, not normalized ACPL |
| `opening_accuracy` (per game) | % opening moves in engine top-3 | Rarely shown in batch UI | **Low–medium** — depends on `best_line` quality |
| `move_quality.*` | Counts from deterioration thresholds (≥0.2 inaccuracy, ≥0.5 mistake, ≥1.5 blunder) | Blunder/mistake counts | **Medium** — consistent within batch |
| `win_loss_draw` | Raw PGN result string | Record | **Bug risk** — does not always use `player_color` |
| `recurring_weaknesses` | Tactical theme in ≥30% of games | Pattern chips | **Improving** — fork heuristic was inflated; capped at 2 themes |
| `opening_insights` / `endgame_insights` | New aggregations (deploy pending on old batches) | Opening / endgame sections | **High** when present — grounded in names + FEN |

### 4.2 Known accuracy problems (must fix — P1 engineering)

1. **Eval chain in `stockfish_game_result`:** `eval_after` for move *i* uses `position_score` of move *i+1*, not position after playing move *i*. Distorts `avg_eval_drop`, phase scores, and “accuracy %.”
2. **Three classification systems:** Batch (pawn deterioration), `StockfishAnalyzer` (centipawn + best-move match), `MetricsCalculator` (% of move labels). Same game can disagree.
3. **Phase boundaries:** `opening_length` / `middlegame_length` from metadata — games with 1-move “middlegame” skew phase trends (seen in batch 7/8).
4. **UI label “accuracy”:** Implies industry-standard accuracy; should rename to **“phase stability”** or **“eval stability score”** until ACPL-based metric exists.
5. **`_count_results` in aggregator:** Counts W/L from result string without player color — can invert record.
6. **Dashboard metrics:** Sourced from path B/C; not batch pipeline — misleading if user only runs batch coach.

### 4.3 Metrics remediation plan (contractual deliverables)

| ID | Deliverable | Acceptance | Status |
|----|-------------|------------|--------|
| M1 | Fix eval_before / eval_after per move (true after-move eval) | Unit test: critical moments carry eval_before/after; per-move post-push analysis | **Done** — `stockfish_game_result.py` |
| M2 | Unify batch classification with documented thresholds | `batch_move_classification.py` single source of truth | **Done** |
| M3 | Player-relative W/L in `batch_summary` | `test_count_results_from_player_perspective` | **Done** — `_count_results` uses `_player_outcome` |
| M4 | Rename UI labels away from “accuracy” where not ACPL | Batch report: “eval stability”, disclaimers on phase section | **Done** — batch UI components |
| M5 | Optional: ACPL or Chess.com-style accuracy as separate field | Correlates ±10% with external tool on sample set |
| M6 | Phase boundary sanity (min moves per phase or merge) | No middlegame with 1 move unless game length ≤ 12 |

---

## 5. Data contract — batch report API

### 5.1 Endpoint

`GET /api/v1/batches/{id}/report/` — auth required, owner only.

### 5.2 Required fields when `status === "completed"`

| Field | Type | Source |
|-------|------|--------|
| `batch_summary` | object | `aggregate_batch()` |
| `per_game_results` | array[5..N] | `build_game_result()` per game |
| `coaching_report` | object \| null | OpenAI; null → `partial` status |
| `failed_games` | array | Subtask failures |
| `games_count` | int | Requested count |

### 5.3 `batch_summary` schema (extended)

**Core (existing):** `games_analyzed`, `player_rating`, `date_range`, `overall_accuracy`, `win_loss_draw`, `phase_performance`, `recurring_weaknesses`, `strength_patterns`, `most_common_blunder_type`, `worst_phase`, `best_phase`.

**Intelligence layer (engine — shipping in repo):**

- `opening_insights[]`: `{ opening_name, games, record, avg_opening_score, status, recommendation, example_game_ids }`
- `endgame_insights[]`: `{ endgame_type, label, frequency, avg_eval_swing, study_focus, example_moments[] }`

**Per-game `critical_moments[]`:** `{ move_number, phase, type, fen, played_move, best_move, eval_swing, tactical_theme, endgame_material?, explanation }`

### 5.4 Coaching schema (OpenAI — locked)

See `core/analysis/coaching_schema.py`. No extra keys without schema version bump.

### 5.5 Partial failure contract

| Status | Meaning | User sees |
|--------|---------|-----------|
| `completed` | ≥5 games analyzed + coaching OK | Full report |
| `partial` | ≥5 games, coaching failed | Engine data + regen CTA (legacy UI) |
| `failed` | <5 successes | Error + retry |

---

## 6. Gaps discovered in repo (missing real value)

### 6.1 Product / UX gaps

| Gap | Impact | Priority |
|-----|--------|----------|
| Two batch report UIs | Confusion, maintenance | P1 — unify on `/batch-report` |
| Dashboard not batch-aware | Feels disconnected after paid analysis | P2 |
| No batch history / compare | No proof of improvement | P2 |
| No email when batch completes | Users leave during 2–10 min wait | P2 |
| No link from priority → game analysis | Coaching not actionable | P1 |
| No FEN board on critical moments | “Intelligent” but not visual | P2 |
| Landing promises vs thin report | Trust churn | P1 |
| Credits/DB name confusion (`postgres` vs `chessmate`) | Support nightmare | P0 ops |
| HTTPS / EB URL in emails | Unprofessional | P1 ops |
| Time management in batch summary | PRD mentions; **not in batch aggregator** | P2 |
| Compare opening to repertoire / ECO sub-lines | Only family names (e.g. “Queen’s Pawn”) | P2 |

### 6.2 Engineering / quality gaps

| Gap | Impact |
|-----|--------|
| Migrations warning on deploy | Schema drift |
| Code quality CI failing | Debt |
| `SEQUENTIAL_BATCH` + single instance | Throughput ceiling — must set expectations |
| No “regenerate coaching only” API | Wastes Stockfish on copy refresh |
| Tests don’t golden-test accuracy numbers | Regressions unnoticed |

### 6.3 Fluff to avoid (explicit non-goals)

- Social feed, leaderboards, badges without coaching tie-in
- Video generation, human coach marketplace (PRD out of scope)
- “AI accuracy” or LLM move classification
- Generic weekly calendar without game citations
- Opening explorer clone

---

## 7. Product map — phased delivery

### P0 — Trust & ship gate ✅ (largely done)

- [x] Batch completes on prod (sequential, depth 14)
- [x] SMTP password reset + styled email
- [x] Report API returns full payload
- [ ] Deploy latest: opening/endgame insights, metrics fixes (M1–M3), unified report UI

### P1 — Differentiator visible (4–6 weeks)

**Vertical (deeper report)**

- [ ] Metrics remediation M1–M4 (truthful numbers + labels)
- [ ] Deploy + validate `opening_insights` / `endgame_insights` on new batches
- [ ] Coaching prompt v2: mandatory citations (game_id, move, opening name, endgame type)
- [ ] Single report route; deprecate legacy results or redirect
- [ ] Report header: record, eval stability, rating, analysis depth/disclaimer
- [ ] Critical moments expanded by default; link to `/game/:id/analysis` where ID maps

**Horizontal (touchpoints)**

- [ ] Forgot-password / auth polish on custom domain
- [ ] Credits consistent on `chessmate` DB
- [ ] Batch run expectations copy (time, depth, credits)

### P2 — Worth paying repeatedly (6–10 weeks)

**Vertical**

- [ ] Regenerate coaching only (API + UI)
- [ ] Per-game coach blurb (AI) on worst moment — cached
- [ ] FEN mini-board or static diagram for top 3 moments
- [ ] Time management in batch (when PGN clocks exist)
- [ ] Batch history list + open past report
- [ ] Batch compare (batch N vs N-1 on same weakness fields)

**Horizontal**

- [ ] Email on batch complete
- [ ] Dashboard “latest coach insight” from last batch
- [ ] Export PDF / share read-only link
- [ ] ACPL or secondary accuracy metric (M5)

### P3 — Moat widening (10–16 weeks)

**Vertical**

- [ ] Opening repertoire gap (“you lose as Black in Sicilian Taimanov” — needs ECO/sub-line)
- [ ] Endgame module map (KRPKR, Lucena drills linked)
- [ ] Prompted study plan → Lichess puzzle/theme from `tactical_theme`
- [ ] Rating-band drill library (1200 vs 1800 text)

**Horizontal**

- [ ] Custom domain + HTTPS everywhere
- [ ] Stripe packages aligned to batch cost model
- [ ] Admin: rerun coaching, grant credits, view batch failures
- [ ] Observability: batch duration, OpenAI failures, Stockfish OOM

### P4 — Scale & optional AI

- [ ] Parallel batch workers / queue fairness
- [ ] Compare-coach AI on structured diffs only
- [ ] Optional premium model tier for coaching prose
- [ ] Mobile-responsive report

---

## 8. AI responsibilities matrix (target end state)

| Feature | Engine | AI | Notes |
|---------|--------|-----|-------|
| Move classification | ✅ | ❌ | After M2 unified |
| Phase / opening / endgame stats | ✅ | ❌ | |
| Recurring / opening / endgame insights | ✅ | ❌ | |
| Critical moment explanations (template) | ✅ | ❌ | Templates in `explanation_templates.py` |
| Critical moment explanation (prose polish) | Optional | ✅ | Only if template too dry |
| Executive summary | Facts from JSON | ✅ | Must cite insights |
| Top 3 priorities | Facts | ✅ | Must include game_id + move |
| 4-week plan | Facts | ✅ | Non-repetitive weeks |
| Per-game coach note | Facts | ✅ | 2–3 sentences max |
| Single-game feedback | Metrics | ✅ | Keep separate; consider merge later |
| Dashboard copy | Aggregates | Optional | Low priority |

---

## 9. Acceptance criteria — “ready to charge”

A release candidate must pass:

1. **New batch (5 games):** `opening_insights` and `endgame_insights` non-empty when data supports it; no longer only `fork` / `missed_tactic` in weaknesses.
2. **Coaching:** At least one priority references `game_X` and move number; opening narrative names an opening from insights.
3. **Metrics:** M1 + M3 complete; UI does not call eval-stability “Chess.com accuracy.”
4. **E2E:** Select games → batch → report loads without empty accordions for training/games sections.
5. **Ops:** Password reset works on prod; credits deduct on correct DB.
6. **CI:** Unit tests green for batch aggregator + auth; code quality triaged or waived in writing.

---

## 10. Success metrics (product)

| Metric | Target |
|--------|--------|
| Batch completion rate | >95% on prod |
| Coaching generation success | >90% when ≥5 games succeed |
| User opens game breakdown section | >60% of report views |
| Repeat batch within 14 days | >25% of users who complete one batch |
| Qualitative: “felt specific to my games” | >4/5 in user interviews |

---

## 11. Open decisions (need owner input)

| # | Decision | Options |
|---|----------|---------|
| 1 | Default batch size | 5 / 10 / 20 |
| 2 | Credit cost per game at depth 14 | Flat vs tiered |
| 3 | Canonical report URL | `/batch-report/:id` only vs keep legacy |
| 4 | Rename “accuracy” globally | Eval stability vs invest in ACPL |
| 5 | Single-game vs batch brand | One product or batch-only paid |
| 6 | Email on complete in P1 or P2 | — |
| 7 | OpenAI model for coaching | Stay mini vs upgrade for prose quality |

---

## 12. Document maintenance

- Update **version** when schema, metrics formulas, or P1 scope changes.
- Link PRs to section IDs (e.g. `M1`, `P1-vertical`).
- After each prod deploy affecting batch: run one smoke batch and attach `report_response` snapshot to release notes.

---

## Appendix A — File index (implementation)

| Concern | Primary files |
|---------|----------------|
| Batch engine | `core/analysis/stockfish_game_result.py`, `batch_move_classification.py`, `core/tasks.py` |
| Aggregation | `core/analysis/batch_aggregator.py`, `moment_insights.py` |
| Coaching AI | `core/analysis/coaching_generator.py`, `coaching_schema.py` |
| Batch UI | `frontend/src/components/batch/*`, `BatchReport.js` |
| Legacy batch UI | `frontend/src/components/BatchAnalysisResults.js` |
| Single-game AI | `core/ai_feedback.py`, `core/analysis/feedback_generator.py` |
| Metrics (other path) | `core/analysis/metrics_calculator.py`, `stockfish_analyzer.py` |
| API | `core/views_batches.py`, `serializers_batches.py` |

---

## Appendix B — Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-06-04 | Initial contract: metrics audit, AI map, P0–P4 map, gaps from repo review |
| 1.1 | 2026-06-04 | M1–M4 implemented: eval pipeline, classification module, player W/L, UI labels |
