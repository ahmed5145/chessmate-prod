import {
  buildHeroMetrics,
  isGenericInsight,
  resolveFocusInsight,
  resolveNextAction,
  shouldShowFocusCard,
} from '../dashboardFocus';

describe('dashboardFocus', () => {
  it('detects generic placeholder insights', () => {
    expect(isGenericInsight('Import and analyze games to unlock personalized performance insights.')).toBe(true);
    expect(isGenericInsight('Top focus area: endgames')).toBe(false);
  });

  it('suggests import when there are no games', () => {
    const action = resolveNextAction({ total_games: 0 });
    expect(action.ctaTo).toBe('/fetch-games');
  });

  it('suggests import when fewer than 5 games imported', () => {
    const action = resolveNextAction({
      total_games: 4,
      game_stats: { analyzed_games: 0 },
      recent_games: [{ id: 9, status: 'pending' }],
    });
    expect(action.ctaTo).toBe('/fetch-games');
    expect(action.secondaryLinks.some((link) => link.to === '/game/9/analysis')).toBe(true);
  });

  it('suggests batch coach when at least 5 games imported', () => {
    const action = resolveNextAction({
      total_games: 12,
      game_stats: { analyzed_games: 0 },
      latest_batch_coach: null,
    });
    expect(action.ctaTo).toBe('/batch-analysis');
  });

  it('opens latest report when batch coach exists', () => {
    const action = resolveNextAction({
      total_games: 12,
      game_stats: { analyzed_games: 8 },
      latest_batch_coach: { batch_id: 42, summary: 'Opening preparation needs work.' },
    });
    expect(action.ctaTo).toBe('/batch-report/42');
  });

  it('prefers batch priority insight for focus card', () => {
    const focus = resolveFocusInsight({
      latest_batch_coach: { batch_id: 3, summary: 'Coach summary fallback' },
      insights: [
        { type: 'warning', text: 'Top focus area: opening preparation' },
        { type: 'success', text: 'Latest batch coach: 71.0% overall accuracy across your games.' },
      ],
    });
    expect(focus.text).toMatch(/Top focus area/);
    expect(focus.href).toBe('/batch-report/3');
  });

  it('prefers server-provided next action when present', () => {
    const action = resolveNextAction({
      nextAction: {
        title: 'Server title',
        description: 'Server description',
        ctaLabel: 'Go',
        ctaTo: '/batch-analysis',
        secondaryLinks: [],
      },
    });
    expect(action.title).toBe('Server title');
    expect(action.ctaTo).toBe('/batch-analysis');
  });

  it('prefers server-provided focus insight when present', () => {
    const focus = resolveFocusInsight({
      focusInsight: {
        type: 'warning',
        text: 'Server focus',
        href: '/batch-report/1',
        actionLabel: 'Open',
      },
    });
    expect(focus.text).toBe('Server focus');
    expect(focus.href).toBe('/batch-report/1');
  });

  it('hides focus card during welcome onboarding', () => {
    expect(shouldShowFocusCard({ total_games: 0 }, { preferences: {} })).toBe(false);
  });

  it('hides focus card for import hero state', () => {
    expect(shouldShowFocusCard({
      nextAction: { type: 'import_games', ctaTo: '/fetch-games' },
      focusInsight: { text: 'Import and analyze games to unlock personalized coaching.', href: '/fetch-games' },
    })).toBe(false);
  });

  it('builds hero metrics with analyzed ratio and conditional win rate', () => {
    const metrics = buildHeroMetrics({
      total_games: 20,
      game_stats: { analyzed_games: 6 },
      average_accuracy: 74.2,
      win_rate: 52,
    });
    expect(metrics).toEqual([
      { label: 'Analyzed', value: '6 / 20' },
      { label: 'Avg accuracy', value: '74.2%' },
      { label: 'Win rate', value: '52%' },
    ]);
  });

  it('prepends batch-first hero metrics for coach-active users', () => {
    const metrics = buildHeroMetrics({
      heroMetrics: [{ label: 'Analyzed', value: '8 / 12' }],
      latest_batch_coach: {
        batch_id: 42,
        games_count: 10,
        overall_accuracy_pct: 68.4,
      },
      priority_inbox: {
        pending_items: [{ title: 'Stop hanging pieces in tactics' }],
      },
      fix_rate: { show: true, fixed_count: 2, total_count: 3 },
    });

    expect(metrics[0]).toEqual({
      label: 'Top priority',
      value: 'Stop hanging pieces in tactics',
    });
    expect(metrics.some((metric) => metric.label === 'Batch accuracy')).toBe(true);
    expect(metrics.some((metric) => metric.label === 'Patterns fixed')).toBe(true);
    expect(metrics.some((metric) => metric.label === 'Analyzed')).toBe(true);
    expect(metrics.length).toBeLessThanOrEqual(4);
  });
});
