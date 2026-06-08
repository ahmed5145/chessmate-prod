import { renderHook, waitFor } from '@testing-library/react';
import api from '../../services/api';
import { getPublicBatchReport } from '../../services/apiRequests';
import { getDemoBatchReport } from '../../content/demoBatchReport';
import useExampleBatchReport from '../useExampleBatchReport';

jest.mock('../../services/api', () => ({
  get: jest.fn(),
}));

jest.mock('../../services/apiRequests', () => ({
  getPublicBatchReport: jest.fn(),
}));

describe('useExampleBatchReport', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('uses live demo token when site-config provides one', async () => {
    const liveReport = { games_count: 10, status: 'completed', batch_summary: { games_analyzed: 10 } };
    api.get.mockResolvedValue({
      data: { signup_bonus_credits: 20, demo_batch_share_token: 'live-token' },
    });
    getPublicBatchReport.mockResolvedValue(liveReport);

    const { result } = renderHook(() => useExampleBatchReport());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(getPublicBatchReport).toHaveBeenCalledWith('live-token');
    expect(result.current.batchReport).toEqual(liveReport);
    expect(result.current.reportSource).toBe('live');
    expect(result.current.signupBonus).toBe(20);
  });

  it('falls back to static fixture when live demo is unavailable', async () => {
    api.get.mockResolvedValue({
      data: { signup_bonus_credits: 15, demo_batch_share_token: 'bad-token' },
    });
    getPublicBatchReport.mockRejectedValue({ detail: 'Not found' });

    const { result } = renderHook(() => useExampleBatchReport());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.reportSource).toBe('static');
    expect(result.current.batchReport).toEqual(getDemoBatchReport());
  });
});
