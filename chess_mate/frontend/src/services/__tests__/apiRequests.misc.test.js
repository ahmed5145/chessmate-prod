import axios from 'axios';
import api from '../api';
import {
  fetchDashboardData,
  fetchUserGames,
  getPublicBatchReport,
  refreshDashboardCache,
  revokeBatchShare,
} from '../apiRequests';

jest.mock('../api', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
    defaults: { headers: { common: {} } },
  },
}));

jest.mock('axios', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
  },
}));

describe('apiRequests misc API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('fetchUserGames', () => {
    it('paginates through next links and normalizes rows', async () => {
      api.get
        .mockResolvedValueOnce({
          data: {
            results: [
              {
                id: 1,
                opponent: 'Alice',
                analysis_status: 'analyzed',
                played_at: '2025-01-01',
              },
            ],
            next: 'http://localhost/api/v1/games/?page=2',
          },
        })
        .mockResolvedValueOnce({
          data: {
            results: [{ id: 2, opponent: 'Bob', status: 'pending' }],
            next: null,
          },
        });

      const data = await fetchUserGames();

      expect(api.get).toHaveBeenNthCalledWith(1, '/api/v1/games/');
      expect(api.get).toHaveBeenNthCalledWith(2, '/api/v1/games/?page=2');
      expect(data.count).toBe(2);
      expect(data.results[0]).toMatchObject({
        id: 1,
        opponent: 'Alice',
        analysis_status: 'analyzed',
      });
      expect(data.results[1].analysis_status).toBe('unanalyzed');
    });

    it('maps 401 to login message', async () => {
      api.get.mockRejectedValue({ response: { status: 401 } });

      await expect(fetchUserGames()).rejects.toThrow('Please log in to view your games');
    });
  });

  describe('fetchDashboardData', () => {
    it('normalizes nested dashboard payload', async () => {
      api.get.mockResolvedValue({
        data: {
          game_stats: { total: 12, win_rate: 55 },
          user: { credits: 7 },
          insights: [{ opponent: 'Rival', mistake_count: 3, summary: 'Missed forks' }],
        },
      });

      const data = await fetchDashboardData();

      expect(data.total_games).toBe(12);
      expect(data.win_rate).toBe(55);
      expect(data.credits).toBe(7);
      expect(data.insights[0].type).toBe('warning');
      expect(data.insights[0].text).toContain('Missed forks');
    });
  });

  describe('refreshDashboardCache', () => {
    it('swallows refresh errors', async () => {
      const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
      api.post.mockRejectedValue(new Error('offline'));

      await expect(refreshDashboardCache()).resolves.toBeUndefined();

      expect(warnSpy).toHaveBeenCalled();
      warnSpy.mockRestore();
    });
  });

  describe('revokeBatchShare', () => {
    it('deletes share endpoint', async () => {
      api.delete.mockResolvedValue({ data: { revoked: true } });

      const data = await revokeBatchShare('batch-5');

      expect(api.delete).toHaveBeenCalledWith('/api/v1/batches/batch-5/share/');
      expect(data).toEqual({ revoked: true });
    });
  });

  describe('getPublicBatchReport', () => {
    it('fetches public report via standalone axios client', async () => {
      axios.get.mockResolvedValue({ data: { id: 'shared-1', status: 'completed' } });

      const data = await getPublicBatchReport('token-abc');

      expect(axios.get).toHaveBeenCalledWith(
        expect.stringMatching(/\/api\/v1\/batches\/public\/token-abc\/report\/$/)
      );
      expect(data).toEqual({ id: 'shared-1', status: 'completed' });
    });

    it('throws shared report error payload', async () => {
      axios.get.mockRejectedValue({ response: { data: { detail: 'Not found' } } });

      await expect(getPublicBatchReport('bad-token')).rejects.toEqual({ detail: 'Not found' });
    });
  });
});
