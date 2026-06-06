import {
  estimateBatchDurationMinutes,
  estimateBatchDurationSeconds,
  formatBatchDurationRange,
} from './batchTimeEstimate';

describe('batchTimeEstimate', () => {
  test('formats range for 5 games', () => {
    expect(formatBatchDurationRange(5)).toBe('about 17–27 minutes');
  });

  test('typical seconds for 10 games', () => {
    expect(estimateBatchDurationSeconds(10)).toBe(42 * 60);
    expect(estimateBatchDurationMinutes(10).typicalMinutes).toBe(42);
  });
});
