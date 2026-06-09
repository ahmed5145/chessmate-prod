# ChessMate Platform Growth & Opportunity Audit

**Status:** Active audit  
**Created:** 2026-06-09  
**Audience:** Product, engineering, marketing — post–retention-plan, during Smoke 1/2  
**Purpose:** Consolidated opportunities for user value, marketing, positioning, differentiation, UI/UX, and retention — with financial impact and launch timing.

**Related:** [DIFFERENTIATION_MATRIX.md](./DIFFERENTIATION_MATRIX.md), [PRODUCT_CONTRACT.md](./PRODUCT_CONTRACT.md), [PRICING_UNIT_ECONOMICS.md](../PRICING_UNIT_ECONOMICS.md), [SINGLE_GAME_RETENTION_PLAN.md](./SINGLE_GAME_RETENTION_PLAN.md), [BATCH_REPORT_UX_PLAN.md](./BATCH_REPORT_UX_PLAN.md)

---

## 1. Executive summary

ChessMate has crossed from “batch analyzer MVP” to a **coaching loop product**: batch diagnosis → proof games → dashboard inbox → email/notifications → second batch comparison. SRG-0…29 shipped; the platform is **launch-capable** if Smoke 1/2 pass and deploy gates in [SHIP_CONTRACT.md](../SHIP_CONTRACT.md) are met.

**Strategic position:** Win on *cross-game coaching proof*, not engine breadth. Chess.com/Lichess own free single-game analysis; ChessMate owns “here are your 2–3 patterns across 10 games, here is move 18 in *your* Sicilian, here is whether you fixed it next month.”

**Biggest gaps before marketing spend:**

| Gap | Why it matters |
|-----|----------------|
| Batch report mobile UX + story order | Paid users read reports on phone; priorities buried = churn |
| Failed-game reasons in UI (#6) | Trust break when batch is `partial` |
| Dashboard ↔ batch coach alignment | Users see stale stats; undermines “coach knows me” |
| Marketing/docs drift | Landing promises vs shipped features confuse early adopters |
| Analytics without funnel dashboard | GTM blind without conversion metrics |
| Fixed infra dominates unit economics | Need volume or leaner prod before heavy paid acquisition |

**Financial headline** (from [PRICING_UNIT_ECONOMICS.md](../PRICING_UNIT_ECONOMICS.md)):

- Revenue per credit sold: **$0.16–$0.20**
- Variable COGS per credit (import + batch): **~$0.002**
- Fixed infra at beta: **~$43–55/mo** → **$0.05–$0.50/credit** until volume grows
- **Margin lever is conversion and batch completion**, not cutting OpenAI/Stockfish costs

---

## 2. Platform snapshot (what exists today)

### 2.1 Core product

| Surface | Shipped capability |
|---------|-------------------|
| **Batch Coach** | 5–30 games, Stockfish depth-14, one OpenAI call/batch, strict coaching JSON |
| **Batch report** | Priorities, training plan, openings/endgames, critical moments, compare, share link |
| **Single-game depth-20** | Cached review free; 1 credit first run; batch citation free; coach alignment score |
| **Dashboard** | Coach inbox, one-thing-today, fix-rate, phase heatmap, streaks, notifications |
| **Retention** | 7 email types (budget-capped), referral 5+5, first-batch celebration, PWA prompt (mobile) |
| **Monetization** | Credit packs ($9.99–$39.99), Stripe, 15 signup bonus, batch included after import |

### 2.2 Acquisition & marketing

| Asset | Path |
|-------|------|
| Landing + example report | `LandingPage.js`, `ExampleBatchReportPage.js` |
| How-it-works | `BatchCoachHowItWorks.js` |
| UTM / referral tracking | `marketingLinks.js`, `marketingAnalytics.js` → GTM/gtag |
| Public site config | `GET /api/v1/public/site-config/` |

### 2.3 Explicitly out of scope (do not chase pre-PMF)

- Social feed, leaderboards, friend graphs
- Opening DB parity with Lichess
- Human coach marketplace
- Subscription billing (DB fields exist; product is credit packs)
- Kubernetes / heavy observability (deferred per overview rules)

---

## 3. How to read this audit

Each opportunity includes:

| Field | Meaning |
|-------|---------|
| **ID** | Reference for prioritization |
| **Value** | Primary user benefit |
| **Marketing / positioning** | How it helps GTM |
| **Effort** | S = days, M = 1–2 weeks, L = multi-week |
| **Financial** | Revenue ↑, COGS ↑, margin, CAC/LTV notes |
| **When** | **Launch** (before/with public beta), **Launch+** (first 30 days), **Post** (after PMF signals), **Defer** |

**Priority tiers:**

- **P0** — Ship before meaningful marketing spend
- **P1** — First month after launch
- **P2** — Growth phase (repeat users, referrals working)
- **P3** — Scale / optional bets

---

## 4. Conversion & acquisition

### G-01 · Batch report as the hero demo (P0 · Launch)

**Today:** Example report page exists; landing embeds preview.  
**Opportunity:** Every CTA should land on *one* canonical “wow” — executive summary + top priority + one proof board — above the fold. Trim example report to coach story, not full 12-section scroll.

| | |
|--|--|
| **Value** | Visitors grasp differentiator in &lt;30s |
| **Marketing** | “Not engine lines — patterns across your games” becomes visceral |
| **Effort** | S |
| **Financial** | Signup conversion ↑ → lowers effective CAC; no COGS change |
| **When** | Launch |

---

### G-02 · Sharpen landing anti-positioning (P0 · Launch)

**Today:** Copy says “not engine lines”; competitors unnamed in hero.  
**Opportunity:** One line: “Chess.com shows one game. ChessMate shows what you keep doing wrong across twenty.” Add micro-FAQ: “Do I still need Chess.com?” → “Yes — we import your games.”

| | |
|--|--|
| **Value** | Reduces “another analysis site?” confusion |
| **Marketing** | Clear category: *batch coach*, not analyzer |
| **Effort** | S |
| **Financial** | Conversion ↑; no cost |
| **When** | Launch |

---

### G-03 · Referral loop on report + celebration (P1 · Launch+)

**Today:** Referral on Credits + first-batch modal; not on share page or batch report footer.  
**Opportunity:** Secondary CTA on `FirstBatchModal` and share footer: “Know someone stuck at 1200? Gift them a coach report.” Track `referral_link_copy` from report context.

| | |
|--|--|
| **Value** | Organic growth from proud users |
| **Marketing** | Positions product as share-worthy |
| **Effort** | S |
| **Financial** | CAC ↓ (10 referrals/mo cap = max 50 credits out); LTV ↑ if referees convert |
| **When** | Launch+ |

---

### G-04 · Moment share OG image (P2 · Post)

**Today:** Text-only OG (SRG-29); DX-02b deferred.  
**Opportunity:** Server-rendered board PNG for Discord/Twitter when share volume justifies ~$5–20/mo image gen or self-hosted.

| | |
|--|--|
| **Value** | Rich previews → more clicks |
| **Marketing** | Viral coefficient on best moments |
| **Effort** | M |
| **Financial** | Small infra cost; acquisition ↑ if shares grow |
| **When** | Post — trigger when &gt;50 share opens/week |

---

### G-05 · Content SEO: “Batch coach for [opening]” (P2 · Post)

**Today:** `pageMeta.js` on key routes; no content hub.  
**Opportunity:** Static pages: “Coach report for Sicilian players,” linking to example report + how-it-works. Target long-tail search.

| | |
|--|--|
| **Value** | Inbound intent traffic |
| **Marketing** | Own “batch chess coaching” niche |
| **Effort** | M (content + 3–5 pages) |
| **Financial** | CAC ↓ over months; no marginal COGS |
| **When** | Post |

---

### G-06 · Community launch (Lichess/Chess.com forums, r/chess) (P1 · Launch+)

**Today:** No in-product community link (retention plan deferred single Discord link).  
**Opportunity:** One Discord or subreddit megathread; founder replies with example report links. **Not** product work — GTM motion.

| | |
|--|--|
| **Value** | Early adopter feedback |
| **Marketing** | Proof from real usernames |
| **Effort** | S (ops) |
| **Financial** | CAC ~$0; support time cost |
| **When** | Launch+ (after Smoke + deploy) |

---

## 5. Activation & onboarding

### A-01 · Single path: verify → import → batch (P0 · Launch)

**Today:** Welcome email + `WelcomeGuide` + dashboard next-action; multiple entry points (`/batch`, `/batch-analysis`, `/fetch-games`).  
**Opportunity:** Navbar highlights one path. Hide or de-emphasize PGN `/batch` upload until user has imported games. Dashboard empty state: only “Connect account → Import 10 games → Run Batch Coach.”

| | |
|--|--|
| **Value** | Time-to-first-aha ↓ |
| **Marketing** | Simpler story for demos |
| **Effort** | S |
| **Financial** | Batch completion rate ↑ → realizes subsidized COGS on signup bonus |
| **When** | Launch |

---

### A-02 · Email verification friction audit (P1 · Launch+)

**Today:** Verify required before full use.  
**Opportunity:** Measure drop-off verify → import. If &gt;40% loss, add “import while unverified” read-only or resend-verify banner on fetch-games.

| | |
|--|--|
| **Value** | More users reach first batch |
| **Marketing** | Fewer dead signups |
| **Effort** | M |
| **Financial** | Paid conversion ↑ |
| **When** | Launch+ (data-driven) |

---

### A-03 · Guided first batch (game count coach) (P1 · Launch+)

**Today:** User picks 5–30 games; no default recommendation.  
**Opportunity:** Pre-select “last 10 rated games” with copy: “Sweet spot for patterns without long wait.” Show ETA before submit.

| | |
|--|--|
| **Value** | Reduces paralysis and timeouts |
| **Marketing** | “10 games, ~40 minutes” sets expectations |
| **Effort** | S |
| **Financial** | Fewer abandoned `in_progress` batches (CPU waste) |
| **When** | Launch+ |

---

### A-04 · Post-batch “do this now” email + inbox seed (P0 · Shipped — verify in smoke)

**Today:** Batch complete email; inbox seeded with priorities + proof games.  
**Opportunity:** Ensure email subject = executive headline; single CTA to priority #1 proof game (`mode=review`). **Smoke 2 item.**

| | |
|--|--|
| **Value** | Bridges async batch to action |
| **Financial** | Retention ↑; email cost negligible |
| **When** | Launch (verify only) |

---

### A-05 · PGN paste single game (P3 · Defer)

**Retention plan backlog.** Onboarding for users with &lt;5 imported games.  
**Financial:** Import credits still apply if stored as games; dev cost M. **Defer** until import funnel measured.

---

## 6. Core product value (batch report & coaching)

### B-01 · Report story order + hero CTA (P0 · Launch)

**Source:** [BATCH_REPORT_UX_PLAN.md](./BATCH_REPORT_UX_PLAN.md) — priorities buried below engine sections.  
**Opportunity:** Reorder: Hero → Executive summary → Top 3 priorities → vs last batch → … → game breakdown. Sticky “Review priority #1” on desktop/mobile.

| | |
|--|--|
| **Value** | Users know what to do without reading 10 screens |
| **Marketing** | Demo report matches promise |
| **Effort** | M |
| **Financial** | Churn ↓ on first paid batch; supports word-of-mouth |
| **When** | Launch |

---

### B-02 · Mobile batch report nav (P0 · Launch)

**Today:** TOC hidden below `md`; long scroll on phone.  
**Opportunity:** `BatchReportMobileNav` — pill jump nav + sticky primary CTA (already planned in UX doc).

| | |
|--|--|
| **Value** | Mobile-readable coach session |
| **Marketing** | “Read your report anywhere” |
| **Effort** | M |
| **Financial** | Retention ↑; no COGS |
| **When** | Launch |

---

### B-03 · Failed-game reasons in UI (P0 · Launch)

**Source:** SHIP_CONTRACT P0-1, overview #6.  
**Today:** `failed_games` in API; UI list thin on *why*.  
**Opportunity:** Per-game failure reason (timeout, parse, worker) + “Retry failed” with clear credit policy.

| | |
|--|--|
| **Value** | Trust on `partial` batches |
| **Marketing** | Honest coach, not black box |
| **Effort** | S–M |
| **Financial** | Reduces refund/support; retry policy affects credits (see B-10) |
| **When** | Launch |

---

### B-04 · Metric glossary / trust layer (P1 · Launch+)

**Today:** Accuracy, eval stability, phase scores coexist.  
**Opportunity:** One collapsible “How to read this report” — Stockfish depth, what “swing” means, coach vs engine.

| | |
|--|--|
| **Value** | Reduces “is this accurate?” skepticism |
| **Marketing** | Positions as serious coaching, not vibes |
| **Effort** | S |
| **Financial** | Conversion to 2nd batch ↑ |
| **When** | Launch+ |

---

### B-05 · Batch compare as retention hook (P1 · Shipped — polish)

**Today:** `BatchCompareCard`, moment diff (SRG-20), fix-rate (SRG-17).  
**Opportunity:** Above-fold on 2nd batch report: “You fixed 2/3 patterns.” Push notification when fix-rate ready.

| | |
|--|--|
| **Value** | Proof of improvement |
| **Marketing** | Unique vs Chess.com — “progress across batches” |
| **Effort** | S |
| **Financial** | 2nd batch rate ↑ → revenue ↑ |
| **When** | Launch+ |

---

### B-06 · Opening gaps → lost games (P1 · Shipped — polish)

**Today:** SRG-21 links losses per repertoire gap.  
**Opportunity:** Surface top gap on dashboard + batch report hero: “You lost 4 Sicilians — review them.”

| | |
|--|--|
| **Value** | Actionable opening study |
| **Marketing** | Concrete, not generic “work on openings” |
| **Effort** | S |
| **Financial** | Retention; drives free `mode=review` traffic |
| **When** | Launch+ |

---

### B-07 · Coach persona (P2 · Shipped — market it)

**Today:** Direct vs encouraging toggle (SRG-26).  
**Opportunity:** Mention in onboarding: “Pick your coach tone.” A/B subject lines in completion email by persona.

| | |
|--|--|
| **Value** | Personalization without extra OpenAI calls |
| **Marketing** | “Your coach, your tone” |
| **Effort** | S |
| **Financial** | No extra COGS |
| **When** | Launch+ |

---

### B-08 · Parallel batch workers (P3 · Post)

**Today:** `SEQUENTIAL_BATCH_ANALYSIS=true`, concurrency=1.  
**Opportunity:** Second worker or parallel subtasks when queue depth &gt; N.

| | |
|--|--|
| **Value** | Faster batches at scale |
| **Financial** | EC2 ↑ ~$15–30/mo per worker; required before marketing burst |
| **When** | Post — when p95 batch wait &gt;45 min |

---

### B-09 · Depth-16/18 batch option (P3 · Defer)

**Financial:** CPU ~linear with depth; COGS ↑; marginal value for 1200–1600 band unclear. **Defer.**

---

### B-10 · Retry failed games credit policy (P0 · Launch)

**Today:** Retry creates new batch; may charge if `BATCH_CREDITS_PER_GAME &gt; 0` (prod=0).  
**Opportunity:** Document + enforce: retry/regenerate never charges (workspace invariant). UI copy: “No credits for retry.”

| | |
|--|--|
| **Value** | Fairness |
| **Financial** | Slight COGS ↑ on retries; trust ↑ |
| **When** | Launch |

---

## 7. Single-game & proof layer

### S-01 · Batch-first positioning in single-game UI (P1 · Launch+)

**Today:** Rich single-game report; risk of “ChessMate = game analyzer” perception.  
**Opportunity:** Batch context banner always prominent when linked; footer CTA “See all batch priorities” over generic analyze.

| | |
|--|--|
| **Value** | Reinforces paid differentiator |
| **Marketing** | Single-game is proof, not product |
| **Effort** | S |
| **Financial** | Protects batch credit revenue |
| **When** | Launch+ |

---

### S-02 · Drill checklist → Lichess study (P1 · Shipped — verify)

**Today:** SRG-4/6 localStorage checklist + study links.  
**Opportunity:** Batch priority card: “5-min drill” opens checklist pre-filled from priority.

| | |
|--|--|
| **Value** | Closes loop study → play |
| **Effort** | S |
| **When** | Launch+ |

---

### S-03 · Rating-band benchmarks (P1 · Shipped — market)

**Today:** SRG-5 on critical moments.  
**Opportunity:** Landing + report tooltip: “Players at ~1400 miss this fork 3× more than 1800s.”

| | |
|--|--|
| **Marketing** | Concrete social proof |
| **When** | Launch+ |

---

### S-04 · Reduce single-game OpenAI to batch-only narrative (P3 · Post)

**Today:** Single-game coach call on first depth-20 run.  
**Opportunity:** Template + batch priorities for repeat visits; OpenAI only when batch context missing.

| | |
|--|--|
| **Financial** | OpenAI COGS ↓ ~$0.01–0.02/game; quality tradeoff |
| **When** | Post — if single-game volume explodes |

---

## 8. Dashboard & retention loop

### R-01 · Dashboard as “coach home” (P1 · Launch+)

**Today:** Inbox, one-thing-today, heatmap, fix-rate shipped.  
**Opportunity:** Rename mentally in UI: “Coach home” not “Dashboard.” Order: One thing today → Inbox → Fix-rate → Heatmap → Recent games.

| | |
|--|--|
| **Value** | Daily habit surface |
| **Effort** | S |
| **When** | Launch+ |

---

### R-02 · Align dashboard stats with latest batch (P0 · Launch)

**Source:** PRODUCT_CONTRACT — dashboard may reflect legacy aggregates.  
**Opportunity:** Hero metrics from latest `completed` batch: phase weakness, top priority, games analyzed in batch.

| | |
|--|--|
| **Value** | Coherent coach story |
| **Marketing** | Demo dashboard matches report |
| **Effort** | M |
| **Financial** | 2nd batch conversion ↑ |
| **When** | Launch |

---

### R-03 · Weekly digest opt-in prompt (P1 · Launch+)

**Today:** Off by default (SRG-15).  
**Opportunity:** After 2nd batch, one-time card: “Weekly coach check-in?” with sample preview.

| | |
|--|--|
| **Value** | Re-engagement without spam |
| **Financial** | Email cost ~$0; retention ↑ |
| **When** | Launch+ |

---

### R-04 · Notification bell polish (P2 · Launch+)

**Today:** 60s poll; SRG-14 shipped.  
**Opportunity:** Mark inbox items read from bell; badge sync with coach inbox count.

| | |
|--|--|
| **Effort** | S |
| **When** | Launch+ |

---

### R-05 · Streak freeze discoverability (P2 · Launch+)

**Today:** SRG-25 shipped.  
**Opportunity:** Tooltip on first missed day: “Busy week? You have 1 freeze this month.”

| | |
|--|--|
| **Value** | Reduces guilt churn |
| **When** | Launch+ |

---

### R-06 · Training plan `.ics` export (P3 · Defer)

**DX-03 deferred.** Nice for serious players; SRG-6/12 cover habit. **Post** if users request.

---

## 9. UI/UX polish

### U-01 · Loading & error consistency (P1 · Launch+)

**Today:** `extractApiError` + toast widely; PROJECT_STATUS flags inconsistency.  
**Opportunity:** Shared `LoadingCard` / `ErrorRetry` on batch, games, dashboard fetches.

| | |
|--|--|
| **Value** | Professional feel |
| **Effort** | M |
| **When** | Launch+ |

---

### U-02 · Accessibility pass (P1 · Launch+)

**Today:** Listed as blocker in PROJECT_STATUS.  
**Opportunity:** Focus order on batch report TOC, aria labels on streak/inbox, contrast audit on dark mode.

| | |
|--|--|
| **Value** | Inclusive; reduces support |
| **Effort** | M |
| **When** | Launch+ |

---

### U-03 · Remove duplicate batch UIs (P2 · Post)

**Today:** `BatchAnalysisResults.js` legacy + `BatchReport.js` canonical.  
**Opportunity:** Migrate remaining features (charts?) or delete legacy after parity check.

| | |
|--|--|
| **Value** | Less maintenance confusion |
| **Effort** | M |
| **When** | Post |

---

### U-04 · Credits page clarity (P1 · Launch)

**Today:** Packages + how credits work + referral.  
**Opportunity:** Visual “10 games import + 1 batch = 10 credits” calculator. Show signup bonus remaining.

| | |
|--|--|
| **Value** | Purchase confidence |
| **Financial** | Conversion to paid pack ↑ |
| **When** | Launch |

---

### U-05 · Beta → GA trust signals (P1 · Launch+)

**Today:** Beta badge on landing.  
**Opportunity:** Add 2–3 testimonial quotes post-smoke; “As seen on” only when true.

| | |
|--|--|
| **Marketing** | Trust for paid conversion |
| **When** | Launch+ |

---

### U-06 · Full PWA (P3 · Post)

**Today:** Install prompt only; CRA default manifest; no service worker.  
**Opportunity:** Branded manifest, offline “read cached report,” push (Web Push phase 2).

| | |
|--|--|
| **Financial** | Dev cost M; retention ↑ on mobile |
| **When** | Post |

---

## 10. Marketing, positioning & differentiation

### M-01 · Update differentiation matrix (P0 · Launch)

**Today:** Matrix says “emailed completion” planned; shipped. Progress-over-time partially shipped (compare, fix-rate).  
**Opportunity:** Refresh `DIFFERENTIATION_MATRIX.md` + landing bullets to match SRG ship state.

| | |
|--|--|
| **Effort** | S |
| **When** | Launch |

---

### M-02 · Competitive frame beyond Chess.com/Lichess (P2 · Post)

**Today:** No Aimchess, Decode Chess, etc. in docs.  
**Opportunity:** One-pager: “vs single-game AI coaches” — we cite *your* games in batch, one price for 10 games.

| | |
|--|--|
| **Marketing** | Sales enablement for content |
| **When** | Post |

---

### M-03 · “Coach session” language (P1 · Launch+)

**Opportunity:** Replace “analysis” with “coach report” / “coach session” in user-facing strings (batch complete, emails, nav).

| | |
|--|--|
| **Marketing** | Category creation |
| **Effort** | S (copy pass) |
| **When** | Launch+ |

---

### M-04 · Case study template (P2 · Post)

**Opportunity:** “Player improved from X to Y over 3 batches” — with fix-rate screenshots (anonymized).

| | |
|--|--|
| **Marketing** | High-trust content |
| **When** | Post (need 3 willing users) |

---

### M-05 · Affiliate / streamer pack (P3 · Post)

**Opportunity:** Custom referral codes, 20% rev share on packs for chess YouTubers.

| | |
|--|--|
| **Financial** | CAC tradeoff; margin ↓ on attributed sales |
| **When** | Post |

---

## 11. Monetization & pricing

### $-01 · Keep batch at 0 marginal credits (P0 · Hold)

**Economics:** Variable batch COGS ~$0.002/credit vs $0.16+ revenue. Bundling batch is correct.  
**Do not** add per-game batch credit charge without repositioning entire pricing page.

---

### $-02 · Signup bonus abuse controls (P0 · Launch)

**Today:** 15 credits; referral + IP checks.  
**Opportunity:** Rate limit signups/IP; optional captcha; monitor “import-only never batch” accounts.

| | |
|--|--|
| **Financial** | Promo cost ~$0.03/user real; abuse could burn CPU |
| **When** | Launch |

---

### $-03 · “Second batch” pack nudge (P1 · Launch+)

**Opportunity:** When credits &lt;10 after first batch, banner: “Coach Plus — 10 more reports’ worth of games.”

| | |
|--|--|
| **Financial** | ARPU ↑ |
| **Effort** | S |
| **When** | Launch+ |

---

### $-04 · Subscription (P3 · Defer)

**Docs:** Defer until fixed cost per active user modeled with concurrency.  
**Financial:** Predictable revenue but support burden; credit packs match irregular chess players.

---

### $-05 · Annual / team / club tier (P3 · Post)

**Opportunity:** Club coach buys 2000 credits for students.  
**Financial:** High LTV; sales-led. **Post** PMF.

---

### $-06 · Refund policy clarity (P1 · Launch)

**Today:** Batch hard-fail refunds in contract.  
**Opportunity:** Credits page + FAQ: when refunds happen, 48h support email.

| | |
|--|--|
| **Value** | Purchase trust |
| **When** | Launch+ |

---

## 12. Analytics & GTM infrastructure

### AN-01 · Funnel dashboard (P0 · Launch+)

**Today:** GTM events (`landing_view`, `register_complete`, `single_game_*`, `first_batch_*`) — no internal dashboard.  
**Opportunity:** GA4 funnel: Landing → Register → Verify → Import → Batch start → Batch complete → 2nd batch within 30d.

| | |
|--|--|
| **Financial** | Informs CAC spend |
| **Effort** | S (config) |
| **When** | Launch+ |

---

### AN-02 · Backend product events (P2 · Post)

**Today:** No Mixpanel/PostHog server-side.  
**Opportunity:** Log `batch_completed`, `credits_purchased` server-side for truth.

| | |
|--|--|
| **When** | Post |

---

### AN-03 · Smoke → production metrics (P0 · Launch)

**Opportunity:** Define north-star: **% new users with completed batch within 7 days.** Target 25% for beta.

| | |
|--|--|
| **When** | Launch (after Smoke 1/2) |

---

## 13. Operations, reliability & financial efficiency

### O-01 · Staging smoke + health gate (P0 · Launch)

**Source:** SHIP_CONTRACT P0-2, P0-4.  
**Opportunity:** Fill `STAGING_SMOKE.md`; set `HEALTHCHECK_URL` in deploy.

| | |
|--|--|
| **Financial** | Prevents outage churn |
| **When** | Launch |

---

### O-02 · Admin for EmailSendLog / notifications (P2 · Post)

**Today:** No Django admin for email logs, referrals.  
**Opportunity:** Read-only admin for support debugging.

| | |
|--|--|
| **Effort** | S |
| **When** | Post |

---

### O-03 · Stuck batch janitor (P1 · Launch+)

**Today:** Cleanup task exists; monitor stuck `in_progress`.  
**Opportunity:** Alert if batch &gt;2h in_progress; auto-fail with reason.

| | |
|--|--|
| **Financial** | CPU waste ↓ |
| **When** | Launch+ |

---

### O-04 · Infra right-sizing at 100+ users (P2 · Post)

**Source:** COST_AND_SCALING — ALB dominates.  
**Opportunity:** CloudFront + single origin, or migrate to lighter compute when traffic predictable.

| | |
|--|--|
| **Financial** | Fixed $/credit ↓ |
| **When** | Post — at ~500 credits/mo |

---

### O-05 · Email bounce / complaint monitoring (P3 · Defer)

**OPS-01 in retention plan.** ESP webhooks + pause spaced job. **Post** when email volume &gt;1000/mo.

---

## 14. Launch vs post-launch roadmap (consolidated)

### Launch (before / with public beta marketing)

| ID | Item |
|----|------|
| B-01 | Batch report story order + hero CTA |
| B-02 | Mobile batch report nav |
| B-03 | Failed-game reasons in UI |
| B-10 | Retry credit policy clear |
| R-02 | Dashboard aligned to latest batch |
| A-01 | Single onboarding path |
| G-01 | Hero demo report |
| G-02 | Landing anti-positioning |
| M-01 | Docs/matrix refresh |
| O-01 | Staging smoke + health gate |
| $-02 | Signup abuse controls |
| U-04 | Credits calculator clarity |

### Launch+ (days 1–30)

| ID | Item |
|----|------|
| A-03 | Guided first batch (10 games) |
| B-04 | Metric glossary |
| B-05, B-06 | Compare + opening gaps polish |
| G-03 | Referral on report/share |
| G-06 | Community launch |
| M-03 | “Coach session” copy pass |
| R-01, R-03 | Coach home + digest opt-in |
| U-01, U-02 | Loading/errors + a11y |
| AN-01 | GA4 funnel |
| $-03, $-06 | Second-batch nudge + refund FAQ |

### Post (PMF signals: 2nd batch rate, referral working, 50+ WAU)

| ID | Item |
|----|------|
| G-04, G-05 | OG images, SEO pages |
| B-08 | Parallel workers |
| M-02, M-04, M-05 | Competitive frame, case studies, affiliates |
| O-02, O-03, O-04 | Admin, stuck batch, infra |
| AN-02 | Server-side analytics |
| U-06 | Full PWA |

### Defer (explicit no)

| Item | Reason |
|------|--------|
| Social feed / leaderboards | Out of scope |
| Opening DB parity | Commodity |
| Subscription | Economics immature |
| PGN paste onboarding | After import funnel measured |
| `.ics` training export | SRG-6/12 sufficient |
| Depth upgrade batch | COGS ↑, unclear value |
| Human coaches marketplace | Ops heavy |

---

## 15. Financial impact summary

### Revenue levers (ranked)

1. **First batch completion rate** — unlocks value from signup bonus and drives word-of-mouth  
2. **Second batch within 30 days** — true PMF; fix-rate/compare/inbox exist to support this  
3. **Paid credit conversion** — after bonus exhausted; Credits page + second-batch nudge  
4. **Referral** — capped CAC ~$0.03–0.10 per successful referral in credit cost  
5. **Organic share** — share links + future OG images  

### Cost levers (ranked)

1. **Stuck / abandoned batches** — pure CPU waste (~$0.0003/min)  
2. **Signup abuse** — 15-credit bonus × fake accounts  
3. **Fixed infra** — dominates until ~2,000 credits/mo (see unit economics)  
4. **OpenAI** — negligible vs infra at current scale (~$0.003/batch)  
5. **Email** — negligible; budget caps prevent stacking  

### Scenarios

| Scenario | Action | Expected impact |
|----------|--------|-----------------|
| **Launch lean** | P0 only, minimal ads, community GTM | Burn ~$50/mo infra; learn funnel |
| **Marketing $500/mo** | After P0 + AN-01 funnel | Need CAC &lt;$15 per paying user at $18 ARPU to break even on variable basis; fixed infra still hurts until volume |
| **1,000 credits/mo** | Post + parallel worker | Fixed ~$0.05/credit; margin healthy on Plus pack |
| **Referral 20% of signups** | G-03 + SRG-24 | CAC ↓; credit liability ↑ (capped 10/mo/referrer) |

---

## 16. North-star metrics (recommended)

| Metric | Definition | Launch target | Post target |
|--------|------------|---------------|-------------|
| **Activation** | Completed batch within 7d of signup | 25% | 40% |
| **Proof loop** | Opened ≥1 inbox proof game (`mode=review`) | 30% of activated | 50% |
| **Retention** | 2nd batch within 30d | 15% of activated | 25% |
| **Monetization** | Paid pack within 60d | 5% of signups | 12% |
| **Referral** | ≥1 successful referral per 100 activated | 2 | 8 |
| **Unit economics** | Contribution margin per credit (fully loaded) | Track | &gt;$0.10 at 2k cr/mo |

---

## 17. Risks & anti-patterns

| Risk | Mitigation |
|------|------------|
| **Positioning drift to “game analyzer”** | Batch-first copy; single-game subordinate |
| **Over-emailing** | Keep digest/spaced/reactivation opt-in; respect 2/week cap |
| **Report overwhelm** | B-01 story order; mobile nav |
| **Partial batch distrust** | B-03 failure reasons |
| **Premature scaling ads** | AN-01 funnel before spend |
| **Repo-wide black/isort** | Format only touched files |
| **Scope creep** | This doc + scope lock; use changelog for new ideas |

---

## 18. Document maintenance

- **Revisit:** After Smoke 1/2 + first 50 real users  
- **Owner:** Product  
- **Changelog:** Add dated rows when items ship or defer  

| Date | Change |
|------|--------|
| 2026-06-09 | Initial platform audit — post SRG-0…29 ship |

---

## Appendix A — Idea index (quick lookup)

| ID | One-liner | When |
|----|-----------|------|
| G-01 | Hero demo report | Launch |
| G-02 | Anti-positioning copy | Launch |
| G-03 | Referral on report | Launch+ |
| G-04 | OG board images | Post |
| G-05 | SEO content hub | Post |
| G-06 | Community launch | Launch+ |
| A-01 | Single onboarding path | Launch |
| A-02 | Verify friction audit | Launch+ |
| A-03 | Default 10-game batch | Launch+ |
| A-04 | Batch email → proof CTA | Launch (verify) |
| A-05 | PGN paste | Defer |
| B-01 | Report story order | Launch |
| B-02 | Mobile report nav | Launch |
| B-03 | Failed-game reasons | Launch |
| B-04 | Metric glossary | Launch+ |
| B-05 | Compare polish | Launch+ |
| B-06 | Opening gaps hero | Launch+ |
| B-07 | Market coach persona | Launch+ |
| B-08 | Parallel workers | Post |
| B-09 | Deeper Stockfish | Defer |
| B-10 | Retry credit policy | Launch |
| S-01 | Batch-first single-game | Launch+ |
| S-02 | Drill from priority | Launch+ |
| S-03 | Market benchmarks | Launch+ |
| S-04 | Less single-game AI | Post |
| R-01 | Coach home dashboard | Launch+ |
| R-02 | Dashboard/batch align | Launch |
| R-03 | Digest opt-in prompt | Launch+ |
| R-04 | Bell polish | Launch+ |
| R-05 | Freeze discoverability | Launch+ |
| R-06 | `.ics` export | Defer |
| U-01 | Loading/error UX | Launch+ |
| U-02 | Accessibility | Launch+ |
| U-03 | Remove legacy batch UI | Post |
| U-04 | Credits calculator | Launch |
| U-05 | Testimonials | Launch+ |
| U-06 | Full PWA | Post |
| M-01 | Refresh diff matrix | Launch |
| M-02 | vs AI coach competitors | Post |
| M-03 | Coach session language | Launch+ |
| M-04 | Case studies | Post |
| M-05 | Streamer affiliates | Post |
| $-01 | Hold 0 batch credits | Hold |
| $-02 | Signup abuse controls | Launch |
| $-03 | Second-batch pack nudge | Launch+ |
| $-04 | Subscription | Defer |
| $-05 | Club tier | Post |
| $-06 | Refund FAQ | Launch+ |
| AN-01 | GA4 funnel | Launch+ |
| AN-02 | Server analytics | Post |
| AN-03 | North-star definition | Launch |
| O-01 | Staging smoke | Launch |
| O-02 | Email admin | Post |
| O-03 | Stuck batch janitor | Launch+ |
| O-04 | Infra right-size | Post |
| O-05 | Bounce monitoring | Defer |
