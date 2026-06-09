# Dashboard UX Plan — Coach Home Reorganization

**Status:** Implemented (2026-06-09)  
**Scope:** Frontend layout only — no API changes

## Problem (audit)

The dashboard felt scattered because:

1. **Primary CTA buried** — Hero with main action appeared *after* 6 other cards (inbox, fix-rate, heatmap, one-thing, notifications).
2. **No information architecture** — Flat stack of equal-weight cards; no story for first visit vs returning coach user.
3. **Competing messages** — Welcome line, one-thing, inbox, hero, and focus card all pushed different CTAs.
4. **Wrong widgets for lifecycle stage** — Empty coach inbox and progress widgets shown to users who cannot use them yet (<5 games, no batch).
5. **Generic framing** — "Dashboard" / "Welcome back" instead of coach-product positioning.

## Design: Coach home by lifecycle stage

| Stage | Trigger | What user sees |
|-------|---------|----------------|
| **New** | 0 games | Coach home header → Hero (import) → Games (empty) |
| **Onboarding** | 1–4 games, no batch | Header → Hero (import N more) → Games |
| **Coach ready** | 5+ games, no batch | Header → Hero (start batch) → **Next step** (inbox empty) → Games + stats |
| **Coach active** | Has batch report | Header (welcome back) → Hero → Since last visit → Notifications → **Today's coaching** → **Progress** → **Insight** → Games |

Logic lives in `frontend/src/utils/dashboardLayout.js`.

## Implemented layout (top → bottom)

```
Coach home (eyebrow + stage-aware subtitle)
├── Hero — single primary CTA (always first)
├── Since your last visit (returning active users)
├── Notifications (only when unread exist)
├── Today's coaching / Next step
│   ├── One thing today (active + not snoozed)
│   └── Coach inbox
├── Your progress (active users with fix-rate or heatmap)
│   ├── Fix rate | Phase heatmap (2-col on lg)
├── Coach insight (non-redundant focus card)
└── Your games
    ├── Recent games
    └── More stats (collapsed)
```

## Files changed

| File | Role |
|------|------|
| `utils/dashboardLayout.js` | Stage detection + section visibility |
| `components/dashboard/DashboardPageHeader.js` | Coach home eyebrow + subtitle |
| `components/dashboard/DashboardSection.js` | Grouped section wrapper |
| `components/Dashboard.js` | Reordered render tree |
| `utils/__tests__/dashboardLayout.test.js` | Stage/section tests |
| `components/__tests__/Dashboard.test.js` | Updated assertions |

## Deferred (post-launch polish)

- Merge hero + one-thing when they point to the same CTA
- Tailwind-wrap `FixRateCard` (MUI) for visual consistency
- Batch-first hero metrics (top priority chip from latest batch)
- Nav label rename: "Dashboard" → "Coach home" in navbar

## Success signals

- Time-to-first-click on hero CTA ↓
- Inbox open rate ↑ among coach-active users
- Bounce from dashboard on first session ↓
