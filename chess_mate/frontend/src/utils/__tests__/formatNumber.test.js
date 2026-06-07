import { formatNumber } from '../formatNumber';

describe('formatNumber', () => {
  it('formats numeric values with requested decimals', () => {
    expect(formatNumber(3.256, 2)).toBe('3.26');
    expect(formatNumber('1.5', 1)).toBe('1.5');
  });

  it('returns zero string for invalid input', () => {
    expect(formatNumber('not-a-number')).toBe('0');
    expect(formatNumber(undefined)).toBe('0');
  });
});
