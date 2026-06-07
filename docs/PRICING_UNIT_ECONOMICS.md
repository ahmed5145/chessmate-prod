# Pricing unit economics (beta)

How much we **earn** and **spend** per credit, after import, analysis, batch coach, and production overhead.

**Related:** [COST_AND_SCALING.md](./COST_AND_SCALING.md) (AWS inventory, formulas, capacity).

---

## Credit model (prod)

| Action | Credits charged | Notes |
|--------|-----------------|-------|
| **Import game** | **1** | Chess.com / Lichess fetch + DB storage |
| **Batch coach** | **0** | `BATCH_CREDITS_PER_GAME = 0` — included after import |
| **Single-game analysis** (on-demand) | **1** | Stockfish depth 20 via API (`game_views`) |
| **Signup bonus** | +15 | `SIGNUP_BONUS_CREDITS` |

Credits are sold in one-time packs (not subscriptions).

---

## Revenue per credit (list price)

| Package | Price | Credits | **Revenue / credit** |
|---------|-------|---------|----------------------|
| Coach Starter | $9.99 | 50 | **$0.200** |
| Coach Plus | $17.99 | 100 | **$0.180** |
| Coach Pro | $39.99 | 250 | **$0.160** |

Stripe fees (~2.9% + $0.30 per checkout) reduce net by ~3–5% on small packs; use **~$0.155–$0.194 net/credit** for conservative margin math.

---

## Variable cost per credit (what one credit “costs us”)

Prod defaults: `BATCH_ANALYSIS_DEPTH = 14`, sequential batch, **gpt-4o-mini** coaching, **1× t3.small** EB worker.

**EC2 minute rate (allocated):**  
`$15/mo ÷ 43,200 min ≈ $0.000347/min` (see COST_AND_SCALING §3)

**OpenAI:** ~**$0.003** per 10-game batch (~2 calls).

### A. Import only (marginal)

| Component | Cost / credit |
|-----------|----------------|
| Platform API + PGN storage | ~$0.00001 (negligible) |
| RDS storage | ~$0.000001/game |
| **Total** | **~$0.00001** |

Import alone is essentially free in COGS terms.

### B. Typical Batch Coach journey (primary product)

User imports **N** games (N credits), runs **one N-game batch** (no extra credits).

| N | Stockfish CPU | OpenAI | **Total variable** | **Variable / credit** |
|---|---------------|--------|--------------------|------------------------|
| 5 | ~$0.007 | ~$0.003 | ~$0.010 | **~$0.002** |
| 10 | ~$0.014 | ~$0.003 | ~$0.017 | **~$0.0017** |
| 15 | ~$0.021 | ~$0.003 | ~$0.024 | **~$0.0016** |
| 30 | ~$0.042 | ~$0.006 | ~$0.048 | **~$0.0016** |

Formula:

```
T_game ≈ 4 min (midpoint of 3–5 min ETA)
C_stockfish(N) = N × T_game × $0.000347
C_openai(N) ≈ $0.003 × ceil(N / 10)
C_per_credit(N) = (C_stockfish + C_openai) / N
```

**Takeaway:** For a 10-game batch, each import credit “carries” about **$0.0017** of engine + coaching cost on top of ~$0.00001 import COGS.

### C. Import + on-demand single-game analysis (same credit)

If the user also triggers **per-game analysis** (1 credit = import + later 1-credit analyze):

| Component | Extra cost |
|-----------|------------|
| Stockfish depth 20, one game | ~$0.004–0.008 CPU (shorter than batch depth-14 full pass, but deeper) |

Not the default Batch Coach path; included for completeness.

---

## Fixed production cost (amortized per credit)

Current prod burn: **~$43–55/mo** (~95% fixed at low traffic):

| Service | ~$/mo |
|---------|-------|
| ALB | $16–22 |
| RDS (db.t3.micro) | ~$14 |
| EC2 (t3.small) | ~$15 |
| VPC / public IPv4 | ~$7–11 |

### Allocating fixed cost to credits sold

Assume **paid credits consumed per month** (imports + analyses):

| Monthly paid credits used | Fixed $/credit (@ $50/mo infra) |
|---------------------------|----------------------------------|
| 100 | $0.50 |
| 500 | $0.10 |
| 2,000 | $0.025 |
| 10,000 | $0.005 |

At beta scale, **fixed cost dominates** per-credit economics until volume grows.

---

## Gross margin per credit (examples)

**Fully loaded cost** ≈ variable + amortized fixed.

### Scenario 1 — 10-game batch, Coach Plus ($0.18/credit), 500 credits/mo on platform

| Line | $/credit |
|------|----------|
| Revenue | $0.180 |
| Variable (batch amortized) | −$0.0017 |
| Fixed amortized | −$0.100 |
| **Contribution before Stripe** | **~$0.078** |

### Scenario 2 — Same user, Coach Pro ($0.16/credit), 2,000 credits/mo

| Line | $/credit |
|------|----------|
| Revenue | $0.160 |
| Variable | −$0.0017 |
| Fixed amortized | −$0.025 |
| **Contribution** | **~$0.133** |

### Scenario 3 — Import only, no batch (worst margin on unused inventory)

| Line | $/credit |
|------|----------|
| Revenue | $0.180 |
| Variable | −$0.00001 |
| Fixed (500 cr/mo) | −$0.100 |
| **Contribution** | **~$0.080** |

User still has latent batch cost when they eventually run a batch; model **import + one batch** as the unit of value.

---

## Signup bonus economics

**15 credits** ≈ one 15-game batch:

| | Value |
|--|-------|
| List-price equivalent | $2.40–$3.00 |
| Variable cost (15-game batch) | **~$0.02–0.03** |
| Gross promo cost (excl. fixed) | **~$0.03** |

Sustainable for hundreds of signups; cap abuse with rate limits (see COST_AND_SCALING §4).

---

## What we earn vs what we spend (summary)

| Metric | Order of magnitude |
|--------|-------------------|
| **Revenue per credit sold** | **$0.16–$0.20** (pack-dependent) |
| **Variable COGS per credit** (import + batch share) | **~$0.002** |
| **Fixed COGS per credit** (at beta volume) | **$0.05–$0.50** (volume-dependent) |
| **Fully loaded margin per credit** (500 cr/mo, Plus pack) | **~$0.08** contribution |
| **Fully loaded margin** (2k cr/mo, Pro pack) | **~$0.13** contribution |

**Engine + OpenAI are not the bottleneck on margin** at current scale — **ALB + RDS + idle EC2** are. Batch coach is correctly bundled (0 extra credits) because variable batch cost per credit is already **<1% of revenue**.

---

## Recommendations

1. **Price on import credits** — batch variable cost is low; value is cross-game coaching, not marginal CPU.
2. **Track conversion:** % of imported games that enter a completed batch (subsidized COGS only applies when batches run).
3. **Before cutting Pro price** — recompute at target MAU and credits/month; fixed $/credit must fall below ~$0.02 for healthy margins on $0.16/credit.
4. **Do not add subscription** until fixed cost per active user is modeled with real batch concurrency.
5. **Monitor** stuck `in_progress` batches — pure CPU waste with no revenue event.

---

## Quick reference formulas

```
revenue_per_credit = package_price / package_credits

variable_per_credit(N_game_batch) =
    (N × 4_min × $0.000347 + $0.003 × ceil(N/10)) / N

fixed_per_credit = monthly_infra_cost / monthly_paid_credits_used

contribution_per_credit =
    revenue_per_credit − variable_per_credit − fixed_per_credit
```
