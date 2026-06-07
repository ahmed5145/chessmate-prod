import {
  extractExecutiveTakeaway,
  hasCoachingPriorities,
  splitSummaryBullets,
} from '../batchReportText';

describe('batchReportText', () => {
  it('splitSummaryBullets splits long executive text', () => {
    const bullets = splitSummaryBullets(
      'You hang pieces in the middlegame. Openings are generally solid. Endgames need work.'
    );
    expect(bullets.length).toBeGreaterThanOrEqual(2);
  });

  it('extractExecutiveTakeaway returns first bullet', () => {
    const takeaway = extractExecutiveTakeaway({
      executive_summary: 'You leak material in tactics. Practice forks daily.',
    });
    expect(takeaway).toMatch(/leak material/i);
  });

  it('hasCoachingPriorities requires non-empty array', () => {
    expect(hasCoachingPriorities({ top_3_priorities: [] })).toBe(false);
    expect(hasCoachingPriorities({ top_3_priorities: [{ rank: 1 }] })).toBe(true);
  });
});
