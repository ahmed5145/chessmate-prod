import api from '../api';
import {
  loginUser,
  logoutUser,
  registerUser,
  resendVerificationEmail,
} from '../apiRequests';
import { clearTokens, setTokens } from '../authService';

jest.mock('../api', () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
    defaults: { headers: { common: {} } },
  },
}));

jest.mock('../authService', () => ({
  setTokens: jest.fn(),
  clearTokens: jest.fn(),
}));

describe('apiRequests auth API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    api.defaults.headers.common = {};
  });

  describe('loginUser', () => {
    it('stores tokens from wrapped success response', async () => {
      api.post.mockResolvedValue({
        data: {
          status: 'success',
          data: {
            access: 'access-1',
            refresh: 'refresh-1',
            user: { id: 7, email: 'player@example.com' },
          },
        },
      });

      const result = await loginUser('player@example.com', 'secret');

      expect(api.post).toHaveBeenCalledWith('/api/v1/auth/login/', {
        email: 'player@example.com',
        password: 'secret',
        remember_me: true,
      });
      expect(setTokens).toHaveBeenCalledWith('access-1', 'refresh-1', { rememberMe: true });
      expect(api.defaults.headers.common.Authorization).toBe('Bearer access-1');
      expect(result).toEqual({
        success: true,
        user: { id: 7, email: 'player@example.com' },
      });
    });

    it('stores tokens from direct response format', async () => {
      api.post.mockResolvedValue({
        data: {
          access: 'access-2',
          refresh: 'refresh-2',
          user: { id: 3 },
        },
      });

      await loginUser('a@b.com', 'pw', false);

      expect(setTokens).toHaveBeenCalledWith('access-2', 'refresh-2', { rememberMe: false });
    });

    it('throws when tokens are missing from response', async () => {
      api.post.mockResolvedValue({ data: { user: { id: 1 } } });

      await expect(loginUser('a@b.com', 'pw')).rejects.toThrow(
        'Authentication tokens not found in server response'
      );
    });

    it('maps 401 to extracted detail message', async () => {
      api.post.mockRejectedValue({
        response: { status: 401, data: { detail: 'Invalid credentials' } },
      });

      await expect(loginUser('a@b.com', 'pw')).rejects.toThrow('Invalid credentials');
    });

    it('maps 403 to verification message', async () => {
      api.post.mockRejectedValue({ response: { status: 403 } });

      await expect(loginUser('a@b.com', 'pw')).rejects.toThrow(
        'Account is locked or requires verification'
      );
    });

    it('maps 429 to rate limit message', async () => {
      api.post.mockRejectedValue({ response: { status: 429 } });

      await expect(loginUser('a@b.com', 'pw')).rejects.toThrow(
        'Too many login attempts. Please try again later.'
      );
    });
  });

  describe('logoutUser', () => {
    it('posts refresh token and clears local auth state', async () => {
      localStorage.setItem('tokens', JSON.stringify({ refresh: 'refresh-9' }));
      api.post.mockResolvedValue({ data: {} });

      const result = await logoutUser();

      expect(api.post).toHaveBeenCalledWith('/api/v1/auth/logout/', { refresh: 'refresh-9' });
      expect(clearTokens).toHaveBeenCalled();
      expect(api.defaults.headers.common.Authorization).toBeUndefined();
      expect(result).toBe(true);
    });

    it('still clears tokens when logout request fails', async () => {
      localStorage.setItem('tokens', JSON.stringify({ refresh: 'refresh-9' }));
      api.post.mockRejectedValue(new Error('Server down'));

      const result = await logoutUser();

      expect(clearTokens).toHaveBeenCalled();
      expect(result).toBe(false);
    });
  });

  describe('registerUser', () => {
    it('returns registration payload on success', async () => {
      api.post.mockResolvedValue({ data: { status: 'success', user_id: 12 } });

      const data = await registerUser({ email: 'new@example.com', password: 'long-enough' });

      expect(api.post).toHaveBeenCalledWith('/api/v1/auth/register/', {
        email: 'new@example.com',
        password: 'long-enough',
      });
      expect(data).toEqual({ status: 'success', user_id: 12 });
    });

    it('throws extracted validation error', async () => {
      api.post.mockRejectedValue({
        response: { data: { email: ['Enter a valid email address.'] } },
      });

      await expect(registerUser({ email: 'bad', password: 'x' })).rejects.toThrow(
        'email: Enter a valid email address.'
      );
    });
  });

  describe('resendVerificationEmail', () => {
    it('posts email and returns response data', async () => {
      api.post.mockResolvedValue({ data: { detail: 'Verification email sent.' } });

      const data = await resendVerificationEmail('player@example.com');

      expect(api.post).toHaveBeenCalledWith('/api/v1/auth/resend-verification/', {
        email: 'player@example.com',
      });
      expect(data).toEqual({ detail: 'Verification email sent.' });
    });

    it('throws on API failure', async () => {
      api.post.mockRejectedValue({
        response: { data: { detail: 'Already verified.' } },
      });

      await expect(resendVerificationEmail('player@example.com')).rejects.toThrow(
        'Already verified.'
      );
    });
  });
});
