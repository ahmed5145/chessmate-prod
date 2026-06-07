import api from '../api';
import {
  fetchGameFeedback,
  regenerateBatchCoaching,
} from '../apiRequests';

jest.mock('../api', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    post: jest.fn(),
    defaults: { headers: { common: {} } },
  },
}));

describe('apiRequests analysis API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('fetchGameFeedback', () => {
    it('normalizes nested analysis payload', async () => {
      api.get.mockResolvedValue({
        data: {
          analysis: {
            overall: {
              accuracy: 0.82,
              blunders: 1,
              mistakes: 2,
              inaccuracies: 3,
              position_quality: 0.7,
            },
            phases: { opening: { score: 0.8 } },
            tactics: { opportunities: 4, successful: 2, missed: 1, success_rate: 0.5 },
            critical_moments: [{ move_number: 12 }],
            strengths: ['Solid opening'],
            weaknesses: ['Time trouble'],
          },
        },
      });

      const result = await fetchGameFeedback('game-42');

      expect(api.get).toHaveBeenCalledWith('/api/v1/game/game-42/analysis/');
      expect(result).toMatchObject({
        status: 'COMPLETED',
        game_id: 'game-42',
        analysis_complete: true,
        analysis: {
          overall: {
            accuracy: 0.82,
            blunders: 1,
            mistakes: 2,
            inaccuracies: 3,
            position_quality: 0.7,
          },
          critical_moments: [{ move_number: 12 }],
          strengths: ['Solid opening'],
          weaknesses: ['Time trouble'],
        },
      });
    });

    it('accepts flat analysis response shape', async () => {
      api.get.mockResolvedValue({
        data: {
          overall: { accuracy: 0.55, blunders: 0, mistakes: 1, inaccuracies: 1, position_quality: 0.4 },
          critical_moments: [],
        },
      });

      const result = await fetchGameFeedback('flat-game');

      expect(result.analysis.overall.accuracy).toBe(0.55);
    });

    it('throws when response body is empty', async () => {
      api.get.mockResolvedValue({ data: null });

      await expect(fetchGameFeedback('missing')).rejects.toThrow('Invalid analysis data structure');
    });
  });

  describe('regenerateBatchCoaching', () => {
    it('requires batch id', async () => {
      await expect(regenerateBatchCoaching()).rejects.toThrow('Failed to regenerate coaching');
      expect(api.post).not.toHaveBeenCalled();
    });

    it('posts regenerate endpoint and returns payload', async () => {
      api.post.mockResolvedValue({
        data: { status: 'completed', coaching_report: { executive_summary: 'Updated' } },
      });

      const data = await regenerateBatchCoaching('batch-77');

      expect(api.post).toHaveBeenCalledWith('/api/v1/batches/batch-77/regenerate-coaching/');
      expect(data.coaching_report.executive_summary).toBe('Updated');
    });

    it('throws when server returns empty body', async () => {
      api.post.mockResolvedValue({ data: null });

      await expect(regenerateBatchCoaching('batch-1')).rejects.toThrow('Failed to regenerate coaching');
    });
  });
});
