import api from '../api';
import {
  checkBatchAnalysisStatus,
  fetchBatchAnalysis,
} from '../gameAnalysisService';

jest.mock('../api', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
  },
}));

describe('gameAnalysisService batch status', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('checkBatchAnalysisStatus', () => {
    it('returns FAILURE when task id is missing', async () => {
      const result = await checkBatchAnalysisStatus();

      expect(api.get).not.toHaveBeenCalled();
      expect(result).toMatchObject({
        state: 'FAILURE',
        meta: { error: 'No taskId provided' },
      });
    });

    it('maps STARTED to PROGRESS and normalizes metadata', async () => {
      api.get.mockResolvedValue({
        data: {
          state: 'STARTED',
          meta: { current: 2, total: 5, progress: 40, message: 'Game 2 of 5' },
          completed_games: [{ id: 1 }],
          failed_games: [],
          batch_feedback: { summary: 'partial' },
        },
      });

      const result = await checkBatchAnalysisStatus('task-1');

      expect(api.get).toHaveBeenCalledWith('/api/v1/games/batch-status/');
      expect(result).toMatchObject({
        state: 'PROGRESS',
        meta: { current: 2, total: 5, progress: 40, message: 'Game 2 of 5' },
        batch_feedback: { summary: 'partial' },
      });
    });

    it('throws when the request fails', async () => {
      api.get.mockRejectedValue(new Error('offline'));

      await expect(checkBatchAnalysisStatus('task-2')).rejects.toThrow('offline');
    });
  });

  describe('fetchBatchAnalysis', () => {
    it('requires a task id', async () => {
      await expect(fetchBatchAnalysis()).rejects.toThrow('No task ID provided');
    });

    it('returns in-progress payload for PROGRESS state', async () => {
      api.get.mockResolvedValue({
        data: {
          state: 'PROGRESS',
          meta: { current: 1, total: 4, progress: 25, message: 'Analyzing' },
        },
      });

      const result = await fetchBatchAnalysis('task-3');

      expect(result).toMatchObject({
        status: 'in_progress',
        progress: { current: 1, total: 4, progress: 25, message: 'Analyzing' },
      });
    });

    it('returns completed payload for SUCCESS state', async () => {
      api.get.mockResolvedValue({
        data: {
          state: 'SUCCESS',
          meta: { current: 4, total: 4 },
          results: { coach_summary: 'Done' },
        },
      });

      const result = await fetchBatchAnalysis('task-4');

      expect(result).toMatchObject({
        status: 'completed',
        batch_feedback: { coach_summary: 'Done' },
        progress: { message: 'Analysis complete', progress: 100 },
      });
    });

    it('throws for FAILURE responses', async () => {
      api.get.mockResolvedValue({
        data: { state: 'FAILURE', error: 'Engine crashed' },
      });

      await expect(fetchBatchAnalysis('task-5')).rejects.toThrow('Engine crashed');
    });
  });
});
