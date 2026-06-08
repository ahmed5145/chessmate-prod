import {
  isInsufficientCreditsError,
  parseAnalysisStartError,
} from '../gameAnalysisService';

describe('gameAnalysisService credit errors', () => {
  it('detects HTTP 402 insufficient credits', () => {
    expect(
      isInsufficientCreditsError({
        response: { status: 402, data: { error: 'Insufficient credits' } },
      })
    ).toBe(true);
  });

  it('parses insufficient credits into structured error', () => {
    const parsed = parseAnalysisStartError({
      response: {
        status: 402,
        data: {
          error: 'Insufficient credits',
          credits_required: 1,
          credits_available: 0,
        },
      },
    });

    expect(parsed.insufficientCredits).toBe(true);
    expect(parsed.creditsRequired).toBe(1);
    expect(parsed.creditsAvailable).toBe(0);
  });
});
