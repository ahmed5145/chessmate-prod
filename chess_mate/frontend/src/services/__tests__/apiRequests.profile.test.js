import api from '../api';
import {
  confirmPurchase,
  fetchExternalGames,
  fetchProfileData,
  getCredits,
  getUserProfile,
  purchaseCredits,
  requestPasswordReset,
  resetPassword,
  updateUserProfile,
} from '../apiRequests';

jest.mock('../api', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
    defaults: { headers: { common: {} } },
  },
}));

const makeAccessToken = (userId) => {
  const payload = btoa(JSON.stringify({ user_id: userId }));
  return `header.${payload}.signature`;
};

describe('apiRequests profile and credits API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  describe('getUserProfile', () => {
    it('returns profile payload', async () => {
      api.get.mockResolvedValue({ data: { username: 'coach', credits: 12 } });

      const data = await getUserProfile();

      expect(api.get).toHaveBeenCalledWith('/api/v1/profile/');
      expect(data).toEqual({ username: 'coach', credits: 12 });
    });
  });

  describe('fetchProfileData', () => {
    it('normalizes nested profile response', async () => {
      api.get.mockResolvedValue({
        data: {
          data: {
            user: { username: 'player', email: 'p@example.com' },
            profile: { credits: 5, lichess_username: 'lichess_user' },
          },
        },
      });

      const data = await fetchProfileData();

      expect(data.username).toBe('player');
      expect(data.email).toBe('p@example.com');
      expect(data.credits).toBe(5);
      expect(data.lichess_username).toBe('lichess_user');
    });
  });

  describe('updateUserProfile', () => {
    it('patches profile update endpoint', async () => {
      api.patch.mockResolvedValue({ data: { lichess_username: 'new_name' } });

      const data = await updateUserProfile({ lichess_username: 'new_name' });

      expect(api.patch).toHaveBeenCalledWith('/api/v1/profile/update/', {
        lichess_username: 'new_name',
      });
      expect(data).toEqual({ lichess_username: 'new_name' });
    });

    it('rethrows validation payload on 400', async () => {
      const validation = { lichess_username: ['Already taken'] };
      api.patch.mockRejectedValue({ response: { status: 400, data: validation } });

      await expect(updateUserProfile({ lichess_username: 'taken' })).rejects.toEqual(validation);
    });
  });

  describe('getCredits', () => {
    it('returns credits balance', async () => {
      api.get.mockResolvedValue({ data: { credits: 9 } });

      await expect(getCredits()).resolves.toBe(9);
    });
  });

  describe('purchaseCredits', () => {
    it('posts package id', async () => {
      api.post.mockResolvedValue({ data: { checkout_url: 'https://pay.example/checkout' } });

      const data = await purchaseCredits('starter');

      expect(api.post).toHaveBeenCalledWith('/api/v1/purchase-credits/', { package_id: 'starter' });
      expect(data.checkout_url).toContain('checkout');
    });

    it('maps 400 to invalid package message', async () => {
      api.post.mockRejectedValue({ response: { status: 400 } });

      await expect(purchaseCredits('bad')).rejects.toThrow('Invalid package selection');
    });
  });

  describe('confirmPurchase', () => {
    it('confirms payment id', async () => {
      api.post.mockResolvedValue({ data: { credits: 20 } });

      const data = await confirmPurchase('pay_123');

      expect(api.post).toHaveBeenCalledWith('/api/v1/confirm-purchase/', { payment_id: 'pay_123' });
      expect(data.credits).toBe(20);
    });
  });

  describe('requestPasswordReset', () => {
    it('throws when API returns error status', async () => {
      api.post.mockResolvedValue({ data: { status: 'error', message: 'SMTP unavailable' } });

      await expect(requestPasswordReset('user@example.com')).rejects.toThrow('SMTP unavailable');
    });

    it('returns success payload', async () => {
      api.post.mockResolvedValue({ data: { status: 'ok', message: 'Email sent' } });

      await expect(requestPasswordReset('user@example.com')).resolves.toEqual({
        status: 'ok',
        message: 'Email sent',
      });
    });
  });

  describe('resetPassword', () => {
    it('posts reset confirmation payload', async () => {
      api.post.mockResolvedValue({ data: { status: 'success' } });

      const data = await resetPassword('uid-1', 'token-1', 'new-pass-123');

      expect(api.post).toHaveBeenCalledWith('/api/v1/auth/reset-password/confirm/', {
        uid: 'uid-1',
        token: 'token-1',
        new_password: 'new-pass-123',
      });
      expect(data).toEqual({ status: 'success' });
    });
  });

  describe('fetchExternalGames', () => {
    it('requires authentication', async () => {
      await expect(fetchExternalGames('lichess', 'player', 'rapid')).rejects.toThrow(
        'Authentication required. Please log in again.'
      );
    });

    it('posts fetch request with token user id and normalizes games array', async () => {
      localStorage.setItem(
        'tokens',
        JSON.stringify({ access: makeAccessToken(77) })
      );
      api.post.mockResolvedValue({
        data: {
          data: [{ id: 'g1' }, { id: 'g2' }],
        },
      });

      const games = await fetchExternalGames('Lichess', '  PlayerName ', null, 5);

      expect(api.post).toHaveBeenCalledWith(
        '/api/v1/games/fetch/',
        {
          platform: 'lichess',
          username: 'PlayerName',
          game_type: 'all',
          num_games: 5,
          user_id: 77,
        },
        {
          headers: {
            Authorization: expect.stringMatching(/^Bearer /),
          },
        }
      );
      expect(games).toHaveLength(2);
    });

    it('maps 402 to insufficient credits message', async () => {
      localStorage.setItem(
        'tokens',
        JSON.stringify({ access: makeAccessToken(1) })
      );
      api.post.mockRejectedValue({ response: { status: 402 } });

      await expect(fetchExternalGames('chess.com', 'user', 'blitz')).rejects.toThrow(
        'Insufficient credits. Please purchase more credits to fetch games.'
      );
    });
  });
});
