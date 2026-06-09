import {
  isOneThingSnoozed,
  normalizeOneThingToday,
  resolveOneThingToday,
  snoozeOneThingToday,
} from '../oneThingToday';

describe('oneThingToday', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('normalizes server payload', () => {
    expect(normalizeOneThingToday({
      headline: 'Review priority',
      subline: 'Sicilian example',
      cta_label: '5 min drill',
      cta_to: '/game/1/analysis?mode=review',
      source: 'inbox',
    })).toEqual({
      headline: 'Review priority',
      subline: 'Sicilian example',
      ctaLabel: '5 min drill',
      ctaTo: '/game/1/analysis?mode=review',
      source: 'inbox',
      drillMinutes: 5,
    });
  });

  it('hides card while snoozed', () => {
    snoozeOneThingToday();
    expect(isOneThingSnoozed()).toBe(true);
    expect(resolveOneThingToday({
      one_thing_today: {
        headline: 'Test',
        cta_to: '/games',
      },
    })).toBeNull();
  });

  it('resolves active one thing from dashboard data', () => {
    const item = resolveOneThingToday({
      one_thing_today: {
        headline: 'Replay worst moment',
        cta_to: '/game/9/analysis?mode=review&move=12',
        source: 'batch',
      },
    });
    expect(item?.headline).toBe('Replay worst moment');
    expect(item?.ctaTo).toContain('mode=review');
  });
});
