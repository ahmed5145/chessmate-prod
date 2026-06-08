import {
  BATCH_REPORT_SECTIONS,
  buildBatchReportTocSections,
  hasCoachingInsightsSection,
  hasStudyDrillsSection,
  hasTacticalPatternsSection,
} from '../BatchReportToc';

describe('BATCH_REPORT_SECTIONS order', () => {
  it('leads with summary and priorities before critical moments', () => {
    const ids = BATCH_REPORT_SECTIONS.map((section) => section.id);
    const summaryIdx = ids.indexOf('batch-section-summary');
    const prioritiesIdx = ids.indexOf('batch-section-priorities');
    const criticalIdx = ids.indexOf('batch-section-critical-moments');
    const trainingIdx = ids.indexOf('batch-section-training');
    const gamesIdx = ids.indexOf('batch-section-games');

    expect(summaryIdx).toBeGreaterThanOrEqual(0);
    expect(prioritiesIdx).toBeGreaterThan(summaryIdx);
    expect(criticalIdx).toBeGreaterThan(prioritiesIdx);
    expect(trainingIdx).toBeGreaterThan(criticalIdx);
    expect(gamesIdx).toBe(ids.length - 1);
  });
});

describe('buildBatchReportTocSections', () => {
  const fullReport = {
    batch_summary: {
      recurring_weaknesses: [{ pattern: 'fork' }],
      endgame_insights: [],
      rating_band_coaching: { focus: 'Practice tactics' },
      strength_patterns: [],
    },
    coaching_report: {
      coaching_narrative: { opening: 'Solid' },
    },
  };

  it('omits optional sections when empty', () => {
    const minimal = buildBatchReportTocSections(
      { batch_summary: {}, coaching_report: null },
      { showTimeManagement: false, showStudyDrills: false }
    );
    const ids = minimal.map((section) => section.id);
    expect(ids).not.toContain('batch-section-coaching-insights');
    expect(ids).not.toContain('batch-section-patterns');
    expect(ids).not.toContain('batch-section-time-management');
    expect(ids).not.toContain('batch-section-drills');
  });

  it('includes coaching insights and patterns when data exists', () => {
    const sections = buildBatchReportTocSections(fullReport, { showStudyDrills: false });
    const ids = sections.map((section) => section.id);
    expect(ids).toContain('batch-section-coaching-insights');
    expect(ids).toContain('batch-section-patterns');
  });
});

describe('hasCoachingInsightsSection', () => {
  it('is false when coaching data is empty', () => {
    expect(hasCoachingInsightsSection({ batch_summary: {}, coaching_report: null })).toBe(false);
  });

  it('is true when rating band focus exists', () => {
    expect(
      hasCoachingInsightsSection({
        batch_summary: { rating_band_coaching: { focus: 'Tactics' } },
        coaching_report: null,
      })
    ).toBe(true);
  });

  it('is true when coaching narrative has phase text', () => {
    expect(
      hasCoachingInsightsSection({
        batch_summary: {},
        coaching_report: { coaching_narrative: { opening: 'Play principled development' } },
      })
    ).toBe(true);
  });
});

describe('hasTacticalPatternsSection', () => {
  it('is false without weaknesses or endgame insights', () => {
    expect(hasTacticalPatternsSection({ batch_summary: {} })).toBe(false);
  });

  it('is true when recurring weaknesses exist', () => {
    expect(
      hasTacticalPatternsSection({
        batch_summary: { recurring_weaknesses: [{ pattern: 'fork' }] },
      })
    ).toBe(true);
  });

  it('is true when endgame insights exist', () => {
    expect(
      hasTacticalPatternsSection({
        batch_summary: { endgame_insights: [{ theme: 'rook_endgame' }] },
      })
    ).toBe(true);
  });
});

describe('hasStudyDrillsSection', () => {
  it('is false when all drill links fit in the practice strip', () => {
    expect(
      hasStudyDrillsSection({
        batch_summary: { recurring_weaknesses: [{ pattern: 'pin' }] },
      })
    ).toBe(false);
  });

  it('is true when extra drill links remain beyond the practice strip', () => {
    expect(
      hasStudyDrillsSection({
        batch_summary: {
          recurring_weaknesses: [
            { pattern: 'pin' },
            { pattern: 'fork' },
            { pattern: 'skewer' },
          ],
        },
      })
    ).toBe(true);
  });

  it('is false for empty summary', () => {
    expect(hasStudyDrillsSection({ batch_summary: {} })).toBe(false);
  });
});
