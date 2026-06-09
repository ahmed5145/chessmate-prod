import {
  DASHBOARD_STAGES,
  isOneThingRedundantWithHero,
  resolveDashboardPageCopy,
  resolveDashboardSections,
  resolveDashboardStage,
} from '../dashboardLayout';

describe('dashboardLayout', () => {
  const coachActiveData = {
    total_games: 12,
    batches_completed: 2,
    latest_batch_coach: { batch_id: 9, summary: 'Focus on hanging pieces.' },
    fix_rate: { show: true },
    priority_inbox: { pending_count: 1, pending_items: [{ id: '9:1' }] },
  };

  it('classifies new users with zero games', () => {
    expect(resolveDashboardStage({ total_games: 0 })).toBe(DASHBOARD_STAGES.NEW);
  });

  it('classifies onboarding users below five games', () => {
    expect(resolveDashboardStage({ total_games: 3 })).toBe(DASHBOARD_STAGES.ONBOARDING);
  });

  it('classifies coach-ready users with five games and no batch', () => {
    expect(resolveDashboardStage({ total_games: 8, batches_completed: 0 })).toBe(
      DASHBOARD_STAGES.COACH_READY
    );
  });

  it('classifies coach-active users with a batch report', () => {
    expect(resolveDashboardStage(coachActiveData)).toBe(DASHBOARD_STAGES.COACH_ACTIVE);
  });

  it('shows coach section only for ready or active stages', () => {
    const active = resolveDashboardSections(coachActiveData, {
      preferences: { welcome_guide_seen: true },
    });
    expect(active.showCoachSection).toBe(true);
    expect(active.coachSection.title).toBe("Today's coaching");

    const onboarding = resolveDashboardSections(
      { total_games: 2 },
      { preferences: { welcome_guide_seen: true } }
    );
    expect(onboarding.showCoachSection).toBe(false);

    const ready = resolveDashboardSections(
      { total_games: 8, batches_completed: 0 },
      { preferences: { welcome_guide_seen: true } }
    );
    expect(ready.showCoachSection).toBe(true);
    expect(ready.coachSection.title).toBe('Next step');
  });

  it('hides coach widgets while welcome guide is pending', () => {
    const sections = resolveDashboardSections(coachActiveData, {
      preferences: { welcome_guide_seen: false },
    });
    expect(sections.showCoachSection).toBe(false);
  });

  it('personalizes page copy for returning coach-active users', () => {
    const copy = resolveDashboardPageCopy(DASHBOARD_STAGES.COACH_ACTIVE, 'alice');
    expect(copy.eyebrow).toBe('Coach home');
    expect(copy.subtitle).toContain('Welcome back, alice');
  });

  it('shows progress section only for coach-active users with data', () => {
    const active = resolveDashboardSections(
      {
        ...coachActiveData,
        fix_rate: { show: true },
        phase_heatmap: { show: false },
      },
      { preferences: { welcome_guide_seen: true } },
    );
    expect(active.showProgressSection).toBe(true);

    const ready = resolveDashboardSections(
      { total_games: 8, batches_completed: 0, fix_rate: { show: true } },
      { preferences: { welcome_guide_seen: true } },
    );
    expect(ready.showProgressSection).toBe(false);
  });

  it('hides one-thing when CTA matches hero', () => {
    expect(isOneThingRedundantWithHero({
      oneThingToday: { ctaTo: '/batch-report/42', headline: 'Open report' },
      nextAction: { ctaTo: '/batch-report/42' },
    })).toBe(true);

    const sections = resolveDashboardSections(
      {
        ...coachActiveData,
        one_thing_today: {
          headline: 'Drill',
          cta_to: '/batch-report/42',
        },
        nextAction: { ctaTo: '/batch-report/42' },
      },
      { preferences: { welcome_guide_seen: true } },
    );
    expect(sections.showOneThingToday).toBe(false);
  });
});
