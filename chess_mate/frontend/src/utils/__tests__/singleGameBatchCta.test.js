import {
  buildBatchPatternCta,
  buildOpeningStudyDrillLink,
  countOpeningInaccuracies,
} from '../singleGameBatchCta';

describe('singleGameBatchCta', () => {
  it('builds upsell CTA without batch context', () => {
    const cta = buildBatchPatternCta(null);
    expect(cta.variant).toBe('upsell');
    expect(cta.primaryPath).toBe('/batch-analysis');
    expect(cta.headline).toMatch(/patterns across many games/i);
  });

  it('builds batch CTA with pattern counts and priority link', () => {
    const cta = buildBatchPatternCta({
      batch_id: 9,
      priority: { rank: 1, title: 'Fix opening prep' },
      priority_rank: 1,
      pattern_count: 4,
      batch_game_count: 12,
    });

    expect(cta.variant).toBe('batch');
    expect(cta.headline).toContain('4 of 12');
    expect(cta.primaryPath).toBe('/batch-report/9?priority=1');
  });

  it('counts opening inaccuracies and builds opening study label', () => {
    const moves = [
      { moveNumber: 6, classification: 'inaccuracy' },
      { moveNumber: 14, classification: 'mistake' },
    ];
    expect(countOpeningInaccuracies(moves)).toBe(1);

    const drill = buildOpeningStudyDrillLink({
      gameContext: { opening_name: 'Sicilian Defense', eco_code: 'B90' },
      moves,
    });
    expect(drill.label).toContain('B90');
    expect(drill.label).toContain('1 inaccuracy');
    expect(drill.kind).toBe('opening');
  });
});
