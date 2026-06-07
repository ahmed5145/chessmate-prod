import api from '../api';
import {
  createBatch,
  enableBatchShare,
  fetchBatchCompare,
  fetchBatchReportHistory,
  getBatchReport,
  getBatchStatus,
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

describe('apiRequests batch API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('createBatch', () => {
    const fiveIds = [1, 2, 3, 4, 5];

    it('rejects when neither gameIds nor pgnList is provided', async () => {
      await expect(createBatch()).rejects.toThrow('Failed to create batch');
      expect(api.post).not.toHaveBeenCalled();
    });

    it('rejects fewer than 5 games', async () => {
      await expect(createBatch({ gameIds: [1, 2, 3] })).rejects.toThrow('Failed to create batch');
    });

    it('rejects more than 30 games', async () => {
      const ids = Array.from({ length: 31 }, (_, index) => index + 1);
      await expect(createBatch({ gameIds: ids })).rejects.toThrow('Failed to create batch');
    });

    it('posts game_ids for saved games', async () => {
      api.post.mockResolvedValue({
        data: {
          batch_id: 'batch-uuid',
          task_id: 'task-1',
          status: 'pending',
          games_count: 5,
        },
      });

      const result = await createBatch({ gameIds: fiveIds });

      expect(api.post).toHaveBeenCalledWith('/api/v1/batches/', { game_ids: fiveIds });
      expect(result).toEqual({
        batch_id: 'batch-uuid',
        task_id: 'task-1',
        status: 'pending',
        games_count: 5,
      });
    });

    it('posts games payload for PGN list', async () => {
      const pgns = Array.from({ length: 5 }, () => '[Event "x"]\n1. e4');
      api.post.mockResolvedValue({
        data: { batch_id: 'pgn-batch', games_count: 5 },
      });

      await createBatch({ pgnList: pgns });

      expect(api.post).toHaveBeenCalledWith('/api/v1/batches/', { games: pgns });
    });
  });

  describe('getBatchStatus', () => {
    it('requires batch id', async () => {
      await expect(getBatchStatus()).rejects.toThrow('Failed to check batch status');
    });

    it('normalizes status response with defaults', async () => {
      api.get.mockResolvedValue({
        data: {
          batch_id: 'b1',
          status: 'partial',
          completed_games: 8,
          failed_games: 2,
          errors: [{ game_id: 'game_0', message: 'Invalid PGN' }],
        },
      });

      const result = await getBatchStatus('b1');

      expect(api.get).toHaveBeenCalledWith('/api/v1/batches/b1/status/');
      expect(result).toMatchObject({
        batch_id: 'b1',
        status: 'partial',
        completed_games: 8,
        failed_games: 2,
        games_count: 0,
        progress: '',
        errors: [{ game_id: 'game_0', message: 'Invalid PGN' }],
      });
    });
  });

  describe('getBatchReport', () => {
    it('normalizes failed_games, errors, and refund fields', async () => {
      api.get.mockResolvedValue({
        data: {
          id: 'report-1',
          status: 'partial',
          games_count: 10,
          coaching_report: null,
          failed_games: [{ game_id: 'game_2', message: 'Timeout' }],
          errors: 'not-an-array',
          credits_refunded: true,
          credits_refunded_amount: 2,
        },
      });

      const result = await getBatchReport('report-1');

      expect(result).toMatchObject({
        id: 'report-1',
        status: 'partial',
        coaching_report: null,
        failed_games: [{ game_id: 'game_2', message: 'Timeout' }],
        errors: [],
        credits_refunded: true,
        credits_refunded_amount: 2,
      });
    });
  });

  describe('fetchBatchReportHistory', () => {
    it('returns Phase 2 results when available', async () => {
      api.get.mockResolvedValueOnce({
        data: { results: [{ id: 'a' }, { id: 'b' }] },
      });

      const results = await fetchBatchReportHistory(10);

      expect(api.get).toHaveBeenCalledWith('/api/v1/batches/', { params: { limit: 10 } });
      expect(results).toEqual([{ id: 'a' }, { id: 'b' }]);
    });

    it('falls back to legacy endpoint on Phase 2 failure', async () => {
      api.get
        .mockRejectedValueOnce({ response: { status: 500 } })
        .mockResolvedValueOnce({
          data: { results: [{ id: 'legacy-1' }] },
        });

      const results = await fetchBatchReportHistory();

      expect(api.get).toHaveBeenNthCalledWith(2, '/api/v1/games/batch-reports/', {
        params: { limit: 20 },
      });
      expect(results).toEqual([{ id: 'legacy-1' }]);
    });
  });

  describe('enableBatchShare', () => {
    it('posts to share endpoint', async () => {
      api.post.mockResolvedValue({
        data: { share_token: 'tok', share_url: 'https://example.com/share/batch/tok' },
      });

      const data = await enableBatchShare('batch-9');

      expect(api.post).toHaveBeenCalledWith('/api/v1/batches/batch-9/share/');
      expect(data.share_token).toBe('tok');
    });
  });

  describe('fetchBatchCompare', () => {
    it('passes other query param and returns payload', async () => {
      api.get.mockResolvedValue({ data: { narrative: 'Improved' } });

      const data = await fetchBatchCompare('batch-1', 'previous');

      expect(api.get).toHaveBeenCalledWith('/api/v1/batches/batch-1/compare/', {
        params: { other: 'previous' },
      });
      expect(data).toEqual({ narrative: 'Improved' });
    });

    it('wraps API errors with detail message', async () => {
      api.get.mockRejectedValue({
        response: { status: 404, data: { detail: 'No previous batch' } },
      });

      await expect(fetchBatchCompare('batch-1')).rejects.toMatchObject({
        message: 'No previous batch',
        status: 404,
      });
    });
  });
});
