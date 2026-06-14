# Launch Week Plan — ChessMate

**Status:** Active — post-smoke, pre-marketing blast  
**Site:** https://www.chess-mate.online  
**Last updated:** 2026-06-13

Prod sanity and CI/CD are green. This doc is the operator playbook: ops, support, growth, and what to measure in the first 30 days.

---

## 1. Launch readiness (you)

| Check | Status | Notes |
|-------|--------|-------|
| `/health/` returns OK | Done | EB + CD gate |
| Signup → verify → import → batch → report | Done | Smoke Parts 0–5 |
| Referral +5 / +5 after first batch | Done | Account B path |
| Share OG (trailing `/` on moment URL) | Done | Discord/iMessage preview |
| PWA icon | Done | ChessMate, not React |
| CI + CD green | Done | |

**Optional before loud marketing:** [SHIP_CONTRACT P0-1](../SHIP_CONTRACT.md) — show per-game failure reasons on batch report (helps when batches are `partial`).

**Defer until volume:** Part 6 emails, Sentry, dynamic board OG image, Lichess OAuth.

---

## 2. EB environment variables

Your production env already has the essentials. Use this as a sanity reference.

### Must be correct (batch + auth + mail)

| Variable | Purpose |
|----------|---------|
| `ENVIRONMENT` | `production` |
| `DJANGO_SETTINGS_MODULE` | `chess_mate.settings` (or prod override) |
| `ENABLE_CELERY` | `true` — **required** or batches stick at `0/N` |
| `USE_BUNDLED_REDIS` | `true` — Redis in-container for Celery |
| `REDIS_URL` / `REDIS_HOST` / `REDIS_PORT` | Worker broker |
| `OPENAI_API_KEY` | Coaching (one call per batch) |
| `FRONTEND_URL` | `https://www.chess-mate.online` |
| `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` | Include `www.chess-mate.online` |
| `EMAIL_*` + `DEFAULT_FROM_EMAIL` | Verification + transactional mail |
| `GOOGLE_OAUTH_*` | Google sign-in |
| `STRIPE_*` | Credits checkout |
| `DB_*` | RDS connection |

### Support contact (see §4)

| Variable | Purpose |
|----------|---------|
| `SUPPORT_EMAIL` | Shown in product emails / support surfaces (default in code: `support@chess-mate.online`) |

### Optional tuning (defaults usually fine)

| Variable | Default | When to change |
|----------|---------|----------------|
| `SIGNUP_BONUS_CREDITS` | `15` | Marketing experiments |
| `BATCH_ANALYSIS_DEPTH` | `14` | Speed vs quality on EB |
| `SEQUENTIAL_BATCH_ANALYSIS` | `true` | Keep `true` on single small instance |

You do **not** need every possible key documented in AWS — if batches complete and mail sends, you are configured.

---

## 3. Logs — batch stuck or Celery dead

ChessMate runs **Gunicorn + Celery in one Docker container**. There is no separate `celery.log` file on EB.

### How to download logs

1. AWS Console → **Elastic Beanstalk** → **Chessmate-env-2**
2. **Logs** → **Request logs** → **Full logs** (zip)
3. Unzip → open:

```
var/log/eb-docker/containers/eb-current-app/*-stdouterr.log   ← main app + Celery
var/log/eb-engine.log                                        ← deploy, worker startup
var/log/nginx/access.log                                     ← HTTP 4xx/5xx
```

Your bundle path: `BundleLogs-…/var/log/eb-docker/containers/eb-current-app/eb-*-stdouterr.log`

### On container startup (healthy)

Search `eb-engine.log` or top of `stdouterr.log` for:

```text
Starting Celery worker (queues: default, analysis, batch_analysis; ...)
Celery worker pid=32
Celery worker is running.
```

If you see `ERROR: Celery worker exited immediately` or never see `Celery worker is running` → batches will not progress. Fix: `ENABLE_CELERY=true`, redeploy.

### Batch in progress (normal)

In `stdouterr.log`, search:

| Search term | Meaning |
|-------------|---------|
| `analyze_batch_task` | Batch chord scheduled |
| `[batch=` or `game=game_` | Per-game Stockfish subtasks |
| `aggregate_and_report` | OpenAI coaching step (one call per batch) |
| `single_game_analysis COMPLETE` | Single-game depth-20 finished |

**Normal behavior:** `SEQUENTIAL_BATCH_ANALYSIS=true` runs games **one at a time**. UI may sit at `1/5` for several minutes while game 2 runs — not necessarily stuck.

### Batch actually stuck

| Symptom | Search | Likely cause |
|---------|--------|--------------|
| `0/5` for 30+ min, no `game=game_` lines | `Celery worker` | Worker not running |
| Stuck mid-batch after deploy | `exit 137` / worker restart | Deploy killed worker — **cancel batch, start new** |
| OpenAI hang | `aggregate`, `coaching`, timeout | API error — check OpenAI dashboard |
| Import empty | `Import returned 0 games` | Username/platform issue |

**Stuck batch recovery:** [PROD_OPS.md](../PROD_OPS.md) — `python manage.py cancel_batch` inside EB container, then user starts a new batch.

More detail: [DEPLOY_EB_ECR.md § Logs](../DEPLOY_EB_ECR.md#logs-no-ssh-required), [PROD_OPS.md § Batch analysis stuck](../PROD_OPS.md#batch-analysis-stuck-at-15).

---

## 4. Support email — personal vs product address

### What “one line for users” meant

A **single sentence** you reuse everywhere (welcome mail footer, Reddit post, FAQ, Discord pin) so people instantly understand the product:

> **Batch Coach analyzes 5–30 of your Chess.com or Lichess games together** — recurring patterns, priorities, and a training plan. **15 free credits on signup**; your **first depth-20 single-game review** from a batch proof link is **free**.

You do not need a new UI feature — paste it where humans read about the product.

### Personal email for soft launch

**OK for now:** `DEFAULT_FROM_EMAIL` / `SUPPORT_EMAIL` = your Gmail + app password.

| Phase | Recommendation |
|-------|----------------|
| **Soft launch (≤30 users)** | Personal email is fine. Reply within 24h. |
| **Community post (100+ visitors)** | Use `support@chess-mate.online` or `hello@…` forwarding to you — looks more legit, separates life inbox. |
| **Later** | Google Workspace / Zoho on `chess-mate.online`, same `SUPPORT_EMAIL` in EB. |

Set on EB: `SUPPORT_EMAIL=you@whatever.com` so templates, footer, Privacy/Terms, and outbound mail all use the same inbox (served via `GET /api/v1/public/site-config/`).

---

## 4b. Stripe — test keys vs live

| Mode | When to use |
|------|-------------|
| **Test keys** (`sk_test_…`, `pk_test_…`) | Soft launch with friends — no real charges. Checkout works with [Stripe test cards](https://docs.stripe.com/testing). |
| **Live keys** (`sk_live_…`, `pk_live_…`) | When you want real credit purchases. |

**Cost:** Stripe has **no monthly fee** for standard Checkout on pay-as-you-go pricing. You pay **per successful charge** — typically **2.9% + $0.30** per card payment (US; varies by country/card). Failed or refunded charges do not incur the processing fee on the original success in the same way; see Stripe’s dashboard for your exact pricing.

**To switch to live:**

1. Stripe Dashboard → toggle **Test mode** off → copy **live** `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, and create a **live** webhook endpoint for `https://www.chess-mate.online/api/v1/webhooks/stripe/`.
2. Update EB env vars: `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET` (live `whsec_…`).
3. Redeploy. Smoke one small real purchase yourself before announcing paid credits.

Keep test keys until you are ready for real money — friends can still use signup credits without Stripe.

---

## 5. OpenAI spend guardrails

| Action | Detail |
|--------|--------|
| Account balance | You have ~$5; add $15; set **monthly budget cap $5–10** in OpenAI dashboard |
| Cost model | ~**one gpt-4o-mini call per batch** + Stockfish on your server (see [PRICING_UNIT_ECONOMICS.md](../PRICING_UNIT_ECONOMICS.md)) |
| Watch first 10 real user batches | Note credits used vs OpenAI usage dashboard |
| If spend spikes | Lower `BATCH_ANALYSIS_DEPTH`, cap signups, or pause Reddit post |

Rule of thumb: full use of **15 signup credits** ≈ **$0.02–0.03** OpenAI per user (not including your EB instance).

---

## 6. Launch week calendar

### Phase A — Soft launch (Days 1–7)

**Goal:** 10–30 people finish batch #1; learn if priority #1 feels true.

| Day | Action | Done |
|-----|--------|------|
| 1 | Message **5 chess friends** personally with referral link | ☐ |
| 1 | Ask each: “Run 5–10 games, tell me if priority #1 is accurate” | ☐ |
| 2–3 | Fix only **blockers** (signup, import, batch stuck, report unreadable) | ☐ |
| 4–7 | Message **5 more** (club, Lichess friends, coworkers who play) | ☐ |
| 7 | Log metrics (§7) — any second batch within 14 days? | ☐ |

**Do not:** paid ads, Product Hunt, mass email.

### Phase B — Community (Days 8–21)

**Goal:** First 100–500 signups with **insight-led** posts, not link spam.

| Day | Action | Done |
|-----|--------|------|
| 8 | Prepare **screenshot**: batch report priorities + fix-rate or opening gap | ☐ |
| 9 | Post **r/chess** or **r/chessbeginners** (template §8) | ☐ |
| 10–14 | Reply to every comment; invite 3 people to DM feedback | ☐ |
| 14 | Lichess forum / one Discord server (same screenshot + story) | ☐ |
| 14 | Remind happy users: **referral link on /credits** (+5 both sides) | ☐ |
| 21 | Second community touch only if batch #2 rate is encouraging | ☐ |

### Phase C — Harden (Days 22–30)

| Priority | Action |
|----------|--------|
| Product | Ship [P0-1 failure reasons](../SHIP_CONTRACT.md) if testers hit partial batches |
| Growth | 60s screen recording: import → batch → open priority #1 |
| Auth | Lichess OAuth when signup friction shows up in feedback |
| Email | One opt-in stream only (digest **or** spaced) for `/profile` toggles |

---

## 7. Metrics (spreadsheet + `launch_metrics` + GA4)

**Full audit:** [PRODUCT_ANALYTICS_AUDIT.md](PRODUCT_ANALYTICS_AUDIT.md) — GA4 stream `G-3NLTQ3XH2Y`, funnel gaps, weekly process.

Track weekly — DB via CLI; marketing via GA4 after deploy.

| Metric | Week 1 | Week 2 | Week 3 | Week 4 |
|--------|--------|--------|--------|--------|
| Signups | | | | |
| Email verified | | | | |
| First batch **completed** | | | | |
| Second batch within 14 days | | | | |
| Referrals redeemed | | | | |
| Support emails received | | | | |
| OpenAI $ spent | | | | |

**North star:** *Second batch rate* — proves coaching value, not just curiosity.

### CLI on production (EB)

From an app container (see [PROD_OPS.md](../PROD_OPS.md)):

```bash
cd /app/chess_mate && python manage.py launch_metrics
```

Options:

| Flag | Default | Meaning |
|------|---------|---------|
| `--days 30` | 30 | Only users who signed up in the last N days (`0` = all time) |
| `--second-batch-window 14` | 14 | Count a second completed batch if it falls within N days after the user’s **first** completed batch |

Example output:

```
ChessMate launch metrics
  Window: last 30 days (since 2026-05-09)
  Signups: 12
  Email verified: 10
  First batch completed (≥5 games): 7
  Second batch within 14 days of first: 2
  Second-batch rate: 28.6%
  Referral redemptions: 1
```

**What counts as “completed batch”:** `BatchAnalysisReport` with status `completed` or `partial` and at least 5 games — same bar as the product minimum.

Copy numbers into the spreadsheet above each week. There is no in-app analytics dashboard yet.

---

## 8. Copy-paste templates

### DM to a friend

> Hey — I built ChessMate to find patterns across your last 10 online games (not just one engine line). Connect Lichess or Chess.com, pick 5–10 games, get a Batch Coach report with priorities and proof games. 15 free credits on signup. Would you try it and tell me if priority #1 feels right?  
> https://www.chess-mate.online/register?ref=YOUR_CODE

### Reddit (show insight, not logo)

**Title:** I analyzed 10 of my games together — recurring mistake was obvious in hindsight

**Body:**

> I got tired of single-game engine lines not answering “what keeps happening across my games?”
>
> I built a small tool: pick 5–30 Chess.com/Lichess games → one report: top 3 priorities, opening gaps, critical moments, week-by-week plan. Stockfish for moves, one coaching pass for the narrative.
>
> [Screenshot: priorities card or “You fixed 2/3 patterns…”]
>
> 15 free credits on signup. Looking for 3–5 people to run a batch and tell me if the #1 priority matches what you’d tell a student. Link in profile / DM if you want — happy to take feedback here too.

*(Adjust per subreddit rules — some require no link in body; use profile link.)*

### When something breaks

> Thanks for reporting — can you send your username (not password) and batch #? I’ll check logs and credit you if we lost a run.

---

## 9. What success looks like

| Milestone | Target |
|-----------|--------|
| Soft launch | ≥10 completed first batches, ≥3 honest “priority #1 felt true” |
| Community | ≥50 signups, ≥15 completed batches, <5% stuck batches |
| Retention signal | Any user runs batch #2 without you nagging |
| Ready to scale marketing | P0-1 shipped, support inbox manageable, OpenAI spend predictable |

You do **not** need viral growth on day one. You need **believable coaching** and **repeat usage**.

---

## 10. Related docs

| Doc | Use |
|-----|-----|
| [SINGLE_GAME_RETENTION_PLAN.md §7](SINGLE_GAME_RETENTION_PLAN.md) | Smoke log (complete) |
| [SHIP_CONTRACT.md](../SHIP_CONTRACT.md) | P0-1 failure reasons |
| [PROD_OPS.md](../PROD_OPS.md) | `grant_credits`, `cancel_batch`, RDS commands |
| [DEPLOY_EB_ECR.md](../DEPLOY_EB_ECR.md) | Deploy + logs |
| [PRICING_UNIT_ECONOMICS.md](../PRICING_UNIT_ECONOMICS.md) | Cost per batch |
| [PLATFORM_GROWTH_AUDIT.md](PLATFORM_GROWTH_AUDIT.md) | Post-launch feature priorities |
| [LANDING_SEO_MARKETING_AUDIT.md](LANDING_SEO_MARKETING_AUDIT.md) | Landing backlog, SEO, organic marketing |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-13 | Initial launch week plan — post-smoke, EB logs guide, support + growth templates |
| 2026-06-08 | SUPPORT_EMAIL wiring, `launch_metrics` command, Stripe live-key guidance |
