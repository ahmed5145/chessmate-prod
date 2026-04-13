# Product Requirements Document

## Product Name

ChessMate batch coach MVP

## Problem Statement

Most chess analysis tools are good at explaining a single game, but they do not help a player understand what is repeatedly holding them back across many games. Players around 800-2000 want something more like a private coach: identify the real pattern, explain it in plain language, and give them a plan they can actually follow.

## Product Vision

Turn a batch of recently imported games into one combined coaching report that identifies the user's biggest recurring weaknesses, explains what those weaknesses look like in practice, and ends with a short training plan.

## Target User

- Players roughly in the 800-2000 range
- Users who already play enough games to have patterns worth diagnosing
- Users who want improvement guidance, not just engine lines

## Core Job To Be Done

"Show me what I keep doing wrong across my games, why it matters, and what I should work on next."

## MVP Goal

Deliver one combined report for a selected batch of games that feels like a real coach, not a template response or a raw engine dump.

## Product Principles

- Batch first, not single-game first.
- Actionable over verbose.
- Specific over generic.
- Coach voice over tool voice.
- Progress and next steps matter more than engine jargon.

## In Scope For MVP

- Let users select games from their imported games.
- Add a shortcut to select the most recent N games.
- Generate one combined report for the selected batch.
- Surface the user's main recurring weaknesses.
- Summarize openings, middlegame, endgame, and time management trends.
- Highlight a small number of critical moments across the batch.
- Produce a short training plan with next actions.
- Show progress while analysis is running.

## Out Of Scope For MVP

- Deep multi-week training calendar.
- Personalized engine tuning by rating.
- Video generation.
- Human coach marketplace.
- Social features.
- Opening explorer replacements for chess.com or Lichess.
- Perfect cost prediction or hard billing optimization.

## Functional Requirements

### Batch Selection

- Users can multi-select from imported games.
- Users can select the most recent N games with one action.
- The UI should show the number of selected games before analysis starts.

### Batch Analysis

- The system should accept a set of games and produce one combined report.
- The report should aggregate move quality, phase performance, and recurring themes.
- The report should favor repeated patterns over isolated one-off mistakes.

### Report Quality

- The report should explain the top 1-3 biggest issues in plain language.
- The report should identify what the user does well.
- The report should include a practical next-step plan.
- The report should avoid empty template phrasing such as "improve your chess" without context.

### Progress And Completion

- The user should see that analysis is running.
- The user should be able to leave the page during long analysis later if we add email delivery.
- The MVP should not require that email delivery be complete on day one.

## Non-Functional Requirements

- Desktop-first UX.
- Fast enough feedback to feel alive.
- Robust recovery from partial failures.
- Results should remain understandable even when some games have missing time data.
- The report should work with the current backend payload shape.

## Success Metrics

- Percentage of batch analyses completed successfully.
- Percentage of users who select more than one game.
- Percentage of users who open the recommendation section after viewing the report.
- Repeat usage within 7 days.
- User-reported usefulness of the report.

## Key Risks

- If the report sounds generic, the product loses its main reason to exist.
- If the batch report repeats single-game output, users will compare it to free tools and leave.
- If analysis takes too long without clear status, the experience feels broken.
- If the report overstates certainty, trust will drop.

## Assumptions

- The backend can already produce a useful combined analysis payload.
- Analysis can remain asynchronous.
- Pricing and credits can be finalized after product value is proven.

## Open Decisions

- Final credit model.
- Whether email completion is included in MVP or phase 2.
- How many games should be the default batch size.
- Whether to show one report per batch only, or also allow comparison across batches.
