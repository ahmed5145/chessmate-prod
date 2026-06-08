import api from '../api';
import { regenerateBatchCoaching } from '../apiRequests';

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
