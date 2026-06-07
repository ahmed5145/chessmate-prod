# Pricing unit economics (beta)

One-page view of credit packages, revenue per credit, and rough variable cost drivers.

## Credit packages

| Package | Price | Credits | Revenue / credit |
|---------|-------|---------|------------------|
| Coach Starter | $9.99 | 50 | $0.20 |
| Coach Plus | $17.99 | 100 | $0.18 |
| Coach Pro | $39.99 | 250 | $0.16 |

Credits are consumed on **game import** (1 credit per game). Batch coach analysis is included once games are on the account.

Signup bonus: **15 credits** (`SIGNUP_BONUS_CREDITS`).

## Variable cost drivers (per credit ≈ one imported game)

| Cost component | Notes |
|----------------|-------|
| Platform import API | Chess.com / Lichess fetch + storage |
| Stockfish CPU | Batch depth-14 analysis (~3–5 min/game on EB workers) |
| OpenAI coaching | ~1 coaching call per 10-game batch (not per import credit) |

### Coaching token estimate (10-game batch)

- Input: aggregated batch summary + per-game critical moments (~8–15k tokens)
- Output: executive summary, priorities, narrative (~2–4k tokens)
- Model: configured in `coaching_generator.py` (GPT-4 class)

Rough order of magnitude for a **10-game batch**:

- Engine: dominant cost (CPU minutes × instance rate)
- Coaching: $0.05–$0.25 per batch depending on model and prompt size
- Import: negligible vs engine for typical PGN sizes

## Margin framing

At **$0.16–$0.20 revenue per credit** (import):

- A user who only imports and never runs batch still pays per game.
- Batch coach adds engine + LLM cost without extra credit charge — subsidized by import pricing and pack volume discounts (Pro at $0.16/credit vs Starter at $0.20).

**15-credit signup bonus** ≈ **$2.40–$3.00** gross revenue equivalent at list price, offset by acquisition; monitor conversion to paid packs and batch completion rate.

## Recommendations (beta)

1. Keep one-time pack positioning; avoid subscription language in UI.
2. Track cost per completed batch (engine wall time + coaching tokens) before lowering Pro price.
3. If margins tighten, prefer reducing signup bonus or raising minimum pack size before cutting Pro credits.
