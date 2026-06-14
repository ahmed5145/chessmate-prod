# ChessMate Product Analytics & User-Behavior Audit

**Status:** Launch readiness for first ~100 users  
**Last updated:** 2026-06-08  
**Related:** [LAUNCH_WEEK_PLAN.md §7](LAUNCH_WEEK_PLAN.md), [LANDING_SEO_MARKETING_AUDIT.md §6](LANDING_SEO_MARKETING_AUDIT.md), [PLATFORM_GROWTH_AUDIT.md §12](PLATFORM_GROWTH_AUDIT.md)

---

## Executive summary

ChessMate has **three partial analytics layers** that historically did not connect into one funnel:

| Layer | What it is | Strength | Gap |
|-------|------------|----------|-----|
| **Frontend events** | `marketingAnalytics.js` → `dataLayer` + `gtag` | Landing + single-game engagement | Was missing GA4 tag in HTML (**fixed in repo**) |
| **DB truth** | Django models + `launch_metrics` CLI | Signups, verification, batches, referrals, purchases | No report views, import events, D1/D7/D30 dashboard |
| **Ops logs** | `batch_observability`, `single_game_observability` | Batch/single failure debugging | Not user-funnel analytics |

**North star metric:** Second batch within 14 days (`launch_metrics`).

---

## GA4 setup — do this now

Your GA4 property shows **“No data received”** because the Google tag was not in the deployed site. The repo now includes it.

### Your stream details (keep for reference)

| Field | Value |
|-------|--------|
| Stream name | ChessMate |
| Stream URL | `https://chess-mate.online` |
| Stream ID | `15073883423` |
| Measurement ID | **`G-3NLTQ3XH2Y`** |

### What was added in code

1. **`chess_mate/frontend/public/index.html`** — Google tag immediately after `<head>` (per GA4 instructions).
2. **`marketingAnalytics.js`** — `GA_MEASUREMENT_ID` + `trackPageView()` for React Router (SPA does not fire full page loads on navigation).
3. **`App.js`** — calls `trackPageView` on every route change.

Custom product events (`register_complete`, `landing_view`, `single_game_view`, etc.) flow:

```
trackMarketingEvent() → dataLayer (chessmate_*) + CustomEvent → gtag('event', …)
```

### Exact steps for you (founder checklist)

#### Step 1 — Deploy

Deploy the frontend build that includes the updated `index.html` to production (Elastic Beanstalk / your normal pipeline). **GA4 only sees production traffic** at `chess-mate.online` — local `npm start` does not count unless you add a separate dev stream.

#### Step 2 — Verify tag is live (2 minutes)

1. Open `https://chess-mate.online` in Chrome.
2. Open DevTools → **Network** → filter `collect` or `google-analytics`.
3. You should see requests to `google-analytics.com/g/collect` after the page loads.
4. In DevTools **Console**, run: `typeof gtag` → should return `"function"`.

#### Step 3 — GA4 Realtime (5 minutes)

1. GA4 → **Reports** → **Realtime**.
2. Visit the homepage, click **Register**, navigate to **Dashboard** (if logged in).
3. You should see **1 active user** and page paths (`/`, `/register`, etc.) within ~30 seconds.

Optional: GA4 → **Admin** → **Data streams** → your stream → **Test your website** → enter `https://chess-mate.online`.

#### Step 4 — Register key custom events (10 minutes, once)

In GA4 → **Admin** → **Events**, confirm these appear after you trigger them on site (may take up to 24h for non-realtime reports):

| Event name | How to trigger |
|------------|----------------|
| `landing_view` | Open `/` |
| `register_complete` | Complete signup |
| `cta_click` | Click a landing CTA |
| `single_game_view` | Open a completed single-game report |
| `first_batch_celebration_shown` | Complete first batch |

Mark as conversions (optional, launch):

- `register_complete`
- `first_batch_celebration_shown` (proxy for first batch completed + user saw celebration)

#### Step 5 — Weekly DB metrics (every Monday)

On EB app container:

```bash
cd /app/chess_mate && python manage.py launch_metrics
cd /app/chess_mate && python manage.py launch_metrics --days 0   # all-time
```

Copy numbers into the spreadsheet in [LAUNCH_WEEK_PLAN.md §7](LAUNCH_WEEK_PLAN.md).

#### Step 6 — Google Search Console (parallel, not GA4)

Add property for `chess-mate.online` for SEO — separate from GA4.

### What you do **not** need for launch

- **Google Tag Manager** — optional later; direct gtag is enough for first 100 users.
- **Measurement Protocol API** — only if you want server-side events into GA4 (P1; DB/CLI is enough for truth).
- **Consent Mode** — required for EEA ads personalization; add before EU ad campaigns.

### SPA note

React Router only loads `index.html` once. Without `trackPageView` on route changes, GA4 would only count the first URL. `App.js` now sends `page_path` on each navigation.

---

## 1. Existing analytics audit

### 1.1 Providers

| Provider | Status | Location |
|----------|--------|----------|
| **GA4 (`G-3NLTQ3XH2Y`)** | **Wired in repo** | `frontend/public/index.html`, `marketingAnalytics.js` |
| **Cloudflare Web Analytics** | Active | `index.html` (hostname tokens) |
| **PostHog / Mixpanel / Amplitude** | None | — |
| **Custom DB event table** | None | — |
| **`launch_metrics` CLI** | Shipped | `core/management/commands/launch_metrics.py` |
| **Structured server logs** | Batch + single-game | `batch_observability.py`, `single_game_observability.py` |
| **Django Admin** | Operational | Users, games, batches, transactions |

### 1.2 Frontend events tracked today

All via `trackMarketingEvent` / `trackSingleGameEvent`:

| Event | Component | Typical properties |
|-------|-----------|-------------------|
| `landing_view` | LandingPage | `source` |
| `cta_click` | Landing, ExampleBatchReportPage | `location`, `source` |
| `full_example_open` | Landing | `source` |
| `full_example_page_view` | ExampleBatchReportPage | `source` |
| `preview_visible` | BatchReportPreview | `source` |
| `preview_tab_change` | BatchReportPreview | `tab`, `source` |
| `preview_deep_review_cta` | BatchReportPreview | `source` |
| `register_complete` | Register | `source`, `requires_verification` |
| `first_batch_celebration_*` | FirstBatchModal | batch metadata |
| `pwa_install_*` | PwaInstallPrompt | `reason`, `batches_completed` |
| `one_thing_today_*` | DashboardOneThingCard | `source` |
| `priority_inbox_open` | CoachInboxCard, SingleGameAnalysis | inbox context |
| `priority_inbox_reviewed` | useMarkPriorityReviewed | `batch_id`, `priority_index` |
| `single_game_view` / `single_game_review` | SingleGameAnalysis | `game_id`, `batch_id` |
| `single_game_from_batch` | SingleGameAnalysis | batch context |
| `single_game_drill_*` | SingleGameReport, DrillChecklistSection | drill metadata |
| `single_game_batch_cta_click` | SingleGameFooterCta | CTA variant |
| `single_game_share_copy` | SingleGameReportActions | `game_id`, `batch_id` |
| `single_game_moment_share_copy` | SingleGameReportActions | moment metadata |

**Not tracked (gaps):** `signup_started`, `login`, `email_verified`, `games_imported`, `batch_report_created`, `batch_report_completed`, `batch_report_viewed`, `single_analysis_started`, `single_analysis_completed`, `credits_purchased`, `share_link_created`, `share_link_opened`.

### 1.3 Backend signals (implicit)

| Signal | Source |
|--------|--------|
| Signup | `User.date_joined` |
| Email verified | `Profile.email_verified`, `email_verified_at` |
| Referral attached | `Profile.preferences.referred_by_user_id` |
| Referral redeemed | `ReferralRedemption` |
| Games imported | `Game.created_at` per user |
| Batch lifecycle | `BatchAnalysisReport` (status, `games_count`) |
| Single analysis done | `GameAnalysis`, `Game.analysis_status` |
| Credit purchase | `Transaction` (`purchase` / `completed`) |
| Login | `User.last_login` |
| Dashboard return | `Profile.preferences.last_dashboard_visit_at` |
| Inbox / drill streaks | `Profile.preferences` (`inbox_streak`, etc.) |
| Batch ops | `batch_event` JSON in CloudWatch/stderr |

### 1.4 Dashboards today

| View | Purpose |
|------|---------|
| **GA4** | Page views + custom events (after deploy) |
| **Cloudflare Analytics** | Aggregate page views |
| **`launch_metrics` CLI** | Weekly founder spreadsheet |
| **Django Admin** | Per-user operational lookup |
| **In-app dashboard** | Per-user stats only |

---

## 2. Funnel — can we measure it?

| Step | Measurable? | How | Missing |
|------|-------------|-----|---------|
| Homepage visitors | **Partial** | GA4 page views + CF Analytics; `landing_view` on `/` | Logged-in users hitting `/dashboard` directly |
| Create account | **Yes (complete)** | DB `User.date_joined`; GA4 `register_complete` | `signup_started`; `?from=` not persisted to DB |
| Verify email | **Yes** | DB `Profile.email_verified` | GA4 `email_verified` event |
| Import games | **Yes (outcome)** | DB first `Game` per user | Import attempts/failures; GA4 event |
| Create batch | **Yes** | DB `BatchAnalysisReport` created | GA4 `batch_report_created` |
| View completed batch | **No** | — | `batch_report_viewed` on report mount |
| Single-game analysis | **Partial** | DB `GameAnalysis`; GA4 `single_game_view` on load | `started` / `completed` events |
| Purchase credits | **Yes** | DB `Transaction` | GA4 `credits_purchased` |
| D1 / D7 / D30 return | **Partial** | `last_login`, `last_dashboard_visit_at`, second batch in CLI | Cohort script; “meaningful return” definition |

---

## 3. Dropoff detection

```
Visitor → Signup → Verification → Login → Import → First Batch → Report Viewed → Return → Purchase
```

| Transition | Conversion | Abandonment | Stuck detection |
|------------|------------|-------------|-----------------|
| Visitor → Signup | Partial (GA4 vs DB) | No | No signup_started |
| Signup → Verify | Yes (DB) | Partial | Unverified users in Admin |
| Verify → Login | Partial | No | No login event |
| Login → Import | Yes (SQL) | Partial | Users with 0 games |
| Import → Batch | Yes (SQL) | Partial | Games but no batch row |
| Batch → Report viewed | **No** | **No** | **Blind spot** |
| Report → Return | Partial | Partial | `last_dashboard_visit_at`, 2nd batch |
| Return → Purchase | Yes (SQL) | Partial | Admin / Transaction query |

---

## 4. Retention analysis

| Question | Today | Proposed |
|----------|-------|----------|
| Who comes back? | Partial (`last_login`, dashboard visit) | Extend `launch_metrics` D7 |
| How often? | Partial (batch/analysis counts) | Session frequency (P2) |
| What predicts retention? | No | Correlate 2nd batch with inbox review (P2) |
| Churn signals? | `reactivation_email` targets inactive | SQL: signup + 1 batch + no login 14d |
| Reports re-viewed? | No | `batch_report_viewed` event |
| Never returned after first use? | Partial | Admin query on `last_login` |

---

## 5. Launch-ready event plan

### Recommended architecture (first 100 users)

```
Frontend → GA4 (UX + marketing)
Backend ProductEvent or SQL (money + activation truth)
launch_metrics weekly → spreadsheet
```

### Core events — status

| Event | Status | Next action |
|-------|--------|-------------|
| `page_view` | **Partial** | SPA `trackPageView` shipped; verify in Realtime |
| `signup_started` | Missing | Register mount (P0) |
| `signup_completed` | Exists as `register_complete` | Persist `signup_source` on Profile (P0) |
| `email_verified` | Missing | Backend on verify (P0) |
| `login` | Missing | Backend on JWT success (P1) |
| `games_imported` | Missing | Backend after import API (P0) |
| `batch_report_created` | Missing | Backend POST `/api/v1/batches/` (P0) |
| `batch_report_completed` | Missing | Batch chord callback (P0) |
| `batch_report_viewed` | Missing | BatchAnalysisResults mount (P0) |
| `single_analysis_started` | Missing | Celery enqueue (P1) |
| `single_analysis_completed` | Missing | Task success (P1) |
| `single_analysis_viewed` | Partial (`single_game_view`) | Add `cached` flag |
| `credits_purchased` | Missing | Stripe webhook (P0) |
| `referral_used` | Partial (DB) | Log on `attach_referral_on_signup` |
| `share_link_created` | Missing | Share APIs (P1) |
| `share_link_opened` | Missing | Public share GET (P1) |

### User properties

| Property | Available | Store |
|----------|-----------|-------|
| Chess platform | Yes | Profile usernames + `Game.platform` |
| Rating | Yes | Profile rating fields |
| Signup source | **No** | `Profile.preferences.signup_source` (P0) |
| Referral source | Partial | `referred_by_user_id` |
| Games imported | Yes | `Game.count()` |
| Reports generated | Yes | `BatchAnalysisReport.count()` |
| Credits remaining | Yes | `Profile.credits` |
| Last active | Partial | `max(last_login, last_dashboard_visit_at)` |

---

## 6. Launch metrics definitions

| Metric | Definition |
|--------|------------|
| **Activation rate** | Verified + ≥5 games imported + first batch completed within 7d of signup |
| **First batch completion rate** | Batch started → `completed`/`partial` with ≥5 games |
| **First report view rate** | Batch completed → user opened report (needs event) |
| **D1 / D7 / D30 retention** | Login or dashboard visit N days after signup |
| **Second batch rate (14d)** | **North star** — already in `launch_metrics` |
| **Time-to-value** | Signup → first batch `created_at` |
| **Credit conversion** | Users with `Transaction` purchase / signups |

---

## 7. Founder dashboards (first 100 users)

Use **GA4 Explorations** + **weekly `launch_metrics`** + one **Google Sheet** — no PostHog required yet.

### Sheet A — Acquisition (weekly)

- Signups, verified, referral redemptions
- GA4 sessions vs signups (rough visitor → signup %)

### Sheet B — Activation funnel

```
Signups → Verified → ≥5 games → Batch started → Batch completed → (Report viewed)
```

### Sheet C — Retention

- Second batch rate (14d)
- D7 return (`last_login` — add to CLI)

### Sheet D — Monetization

- Purchases count / revenue from `Transaction`

### GA4 exploration (after deploy)

**Funnel:** `page_view` (/) → `register_complete` → custom event when `batch_report_viewed` exists.

Until `batch_report_viewed` ships, use DB for batch complete and GA4 only for top-of-funnel.

---

## 8. Implementation priority

### P0 — Before / during first 100 users

| ID | Task | Status |
|----|------|--------|
| P0-1 | GA4 tag in `index.html` | **Done in repo** — deploy required |
| P0-2 | SPA `trackPageView` | **Done in repo** |
| P0-3 | Deploy + verify Realtime | **You** — after deploy |
| P0-4 | Weekly `launch_metrics` + spreadsheet | **You** — process |
| P0-5 | Persist `signup_source` on register | Pending |
| P0-6 | `batch_report_viewed` frontend event | Pending |
| P0-7 | Extend `launch_metrics` (games, singles, purchases, D7) | Pending |
| P0-8 | Backend truth events (verify, import, batch, purchase) | Pending |

### P1 — After ~20 users

- GA4 funnels + conversions
- `single_analysis_started` / `completed` server-side
- Share link created/opened
- Google Search Console

### P2 — Post-launch

- PostHog / Mixpanel
- Automated founder dashboard
- Churn modeling

---

## Appendix — useful SQL / Admin queries

**Users stuck before import (0 games):**

```sql
SELECT u.id, u.username, u.date_joined, p.email_verified
FROM auth_user u
JOIN core_profile p ON p.user_id = u.id
LEFT JOIN games g ON g.user_id = u.id
WHERE g.id IS NULL
ORDER BY u.date_joined DESC;
```

**Users with games but no batch:**

```sql
SELECT u.username, COUNT(g.id) AS games
FROM auth_user u
JOIN games g ON g.user_id = u.id
LEFT JOIN core_batchanalysisreport b ON b.user_id = u.id
WHERE b.id IS NULL
GROUP BY u.id, u.username
HAVING COUNT(g.id) >= 5;
```

**Credit purchasers:**

```sql
SELECT u.username, t.credits, t.amount, t.created_at
FROM transactions t
JOIN auth_user u ON u.id = t.user_id
WHERE t.transaction_type = 'purchase' AND t.status = 'completed'
ORDER BY t.created_at DESC;
```

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-08 | Initial audit; GA4 `G-3NLTQ3XH2Y` wired in `index.html` + SPA page views |
