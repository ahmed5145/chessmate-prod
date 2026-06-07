import { shouldShowTimeManagementInsight } from '../TimeManagementInsight';

describe('shouldShowTimeManagementInsight', () => {
  it('returns false when clock data covers every game in the batch', () => {
    expect(
      shouldShowTimeManagementInsight({
        time_management_summary: {
          games_with_clock_data: 5,
          games_analyzed: 5,
          insight: 'You often used very little time right before big eval swings.',
          pattern: 'rushed_critical_moments',
        },
      })
    ).toBe(false);
  });

  it('returns true when only some games have clock data', () => {
    expect(
      shouldShowTimeManagementInsight({
        time_management_summary: {
          games_with_clock_data: 3,
          games_analyzed: 5,
          insight: 'You often used very little time right before big eval swings.',
          pattern: 'rushed_critical_moments',
        },
      })
    ).toBe(true);
  });

  it('returns false when there is no insight', () => {
    expect(
      shouldShowTimeManagementInsight({
        time_management_summary: {
          games_with_clock_data: 2,
          games_analyzed: 5,
          insight: null,
        },
      })
    ).toBe(false);
  });
});
