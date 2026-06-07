import { formatRegenerateCoachingError } from '../batchCoachingErrors';

describe('formatRegenerateCoachingError', () => {
  it('returns rate-limit copy for COACH_001', () => {
    expect(
      formatRegenerateCoachingError({
        code: 'COACH_001',
        message: 'Coaching regeneration limit reached for today. Try again tomorrow.',
      })
    ).toBe('Coaching regeneration limit reached for today. Try again tomorrow.');
  });

  it('falls back to detail string errors', () => {
    expect(formatRegenerateCoachingError({ detail: 'Batch analysis must finish first.' }))
      .toBe('Batch analysis must finish first.');
  });
});
