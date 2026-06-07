import api from '../api';
import {
  analyzeBatchGames,
  checkBatchAnalysisStatus,
  retryFailedGames,
} from '../apiRequests';

jest.mock('../api', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    post: jest.fn(),
    defaults: { headers: { common: {} } },
  },
}));

describe('apiRequests legacy batch API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('checkBatchAnalysisStatus', () => {
    it('returns FAILURE payload when task id is missing', async () => {
      const result = await checkBatchAnalysisStatus();

      expect(api.get).not.toHaveBeenCalled();
      expect(result).toMatchObject({
        state: 'FAILURE',
        meta: { error: 'No task ID provided', message: 'No task ID provided' },
      });
    });

    it('normalizes SUCCESS responses', async () => {
      api.get.mockResolvedValue({
        data: {
          state: 'SUCCESS',
          meta: { current: 5, total: 5, progress: 99 },
          completed_games: [{ id: 1 }],
          failed_games: [],
          aggregate_metrics: { accuracy: 0.7 },
          report_id: 'report-1',
        },
      });

      const result = await checkBatchAnalysisStatus('task-1');

      expect(api.get).toHaveBeenCalledWith('/api/v1/games/batch-status/task-1/');
      expect(result).toMatchObject({
        state: 'SUCCESS',
        meta: { message: 'Analysis complete', progress: 100 },
        report_id: 'report-1',
        aggregate_metrics: { accuracy: 0.7 },
      });
    });

    it('keeps PROGRESS state messaging and defaults', async () => {
      api.get.mockResolvedValue({
        data: {
          state: 'PROGRESS',
          meta: { current: 2, total: 5, progress: 40, message: 'Game 2 of 5' },
        },
      });

      const result = await checkBatchAnalysisStatus('task-2');

      expect(result.state).toBe('PROGRESS');
      expect(result.meta.message).toBe('Game 2 of 5');
      expect(result.meta.progress).toBe(40);
    });

    it('maps FAILURE state to error metadata', async () => {
      api.get.mockResolvedValue({
        data: {
          state: 'FAILURE',
          meta: { error: 'Engine crashed', message: 'Batch aborted' },
        },
      });

      const result = await checkBatchAnalysisStatus('task-3');

      expect(result).toMatchObject({
        state: 'FAILURE',
        meta: { error: 'Engine crashed', message: 'Batch aborted' },
      });
    });

    it('treats unknown states as FAILURE', async () => {
      api.get.mockResolvedValue({
        data: { state: 'WEIRD', meta: {} },
      });

      const result = await checkBatchAnalysisStatus('task-4');

      expect(result.state).toBe('FAILURE');
      expect(result.meta.error).toContain('Unknown state');
    });

    it('returns FAILURE payload when the request fails', async () => {
      api.get.mockRejectedValue(new Error('Network down'));

      const result = await checkBatchAnalysisStatus('task-5');

      expect(result.state).toBe('FAILURE');
      expect(result.meta.message).toBe('Network down');
      expect(result.completed_games).toEqual([]);
    });
  });

  describe('analyzeBatchGames', () => {
    it('posts batch analyze payload with defaults', async () => {
      api.post.mockResolvedValue({
        data: {
          task_id: 'task-abc',
          total_games: 10,
          status: 'pending',
          estimated_time: 120,
          message: 'Queued',
        },
      });

      const result = await analyzeBatchGames(10, 'blitz', false, []);

      expect(api.post).toHaveBeenCalledWith('/api/v1/games/batch-analyze/', {
        num_games: 10,
        time_control: 'blitz',
        include_analyzed: false,
        depth: 20,
        use_ai: true,
      });
      expect(result.task_id).toBe('task-abc');
    });

    it('overrides num_games when explicit game ids are provided', async () => {
      api.post.mockResolvedValue({
        data: { task_id: 'task-ids', total_games: 3 },
      });

      await analyzeBatchGames(10, 'all', true, [1, 2, 'bad', 3.9, 4]);

      expect(api.post).toHaveBeenCalledWith('/api/v1/games/batch-analyze/', {
        num_games: 3,
        time_control: 'all',
        include_analyzed: true,
        depth: 20,
        use_ai: true,
        game_ids: [1, 2, 4],
      });
    });

    it('throws when server omits task id', async () => {
      api.post.mockResolvedValue({ data: { total_games: 5 } });

      await expect(analyzeBatchGames(5)).rejects.toThrow('Failed to start batch analysis');
    });
  });

  describe('retryFailedGames', () => {
    it('delegates to createBatch with game ids', async () => {
      api.post.mockResolvedValue({
        data: { batch_id: 'retry-batch', task_id: 'retry-task', games_count: 5 },
      });

      const result = await retryFailedGames({ gameIds: [1, 2, 3, 4, 5] });

      expect(api.post).toHaveBeenCalledWith('/api/v1/batches/', { game_ids: [1, 2, 3, 4, 5] });
      expect(result.batch_id).toBe('retry-batch');
    });
  });
});
