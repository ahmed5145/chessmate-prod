import { sanitizeReportFloats } from '../sanitizeReportText';

describe('sanitizeReportFloats', () => {
  it('returns non-string input unchanged', () => {
    expect(sanitizeReportFloats(null)).toBeNull();
    expect(sanitizeReportFloats(undefined)).toBeUndefined();
    expect(sanitizeReportFloats(42)).toBe(42);
  });

  it('rounds long decimal literals to two places', () => {
    expect(sanitizeReportFloats('Eval dropped by 0.12345 pawns')).toBe('Eval dropped by 0.12 pawns');
  });

  it('leaves short decimals unchanged', () => {
    expect(sanitizeReportFloats('Stable at 0.12')).toBe('Stable at 0.12');
  });
});
