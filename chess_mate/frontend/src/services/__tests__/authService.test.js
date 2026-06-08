import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from '../authService';

describe('authService token storage', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it('reads direct access and refresh token keys', () => {
    localStorage.setItem('access_token', 'access-direct');
    localStorage.setItem('refresh_token', 'refresh-direct');

    expect(getAccessToken()).toBe('access-direct');
    expect(getRefreshToken()).toBe('refresh-direct');
  });

  it('falls back to legacy tokens json blob', () => {
    localStorage.setItem('tokens', JSON.stringify({ access: 'legacy-access', refresh: 'legacy-refresh' }));

    expect(getAccessToken()).toBe('legacy-access');
    expect(getRefreshToken()).toBe('legacy-refresh');
  });

  it('writes all supported token key formats', () => {
    setTokens('new-access', 'new-refresh');

    expect(localStorage.getItem('access_token')).toBe('new-access');
    expect(localStorage.getItem('accessToken')).toBe('new-access');
    expect(localStorage.getItem('refresh_token')).toBe('new-refresh');
    expect(localStorage.getItem('refreshToken')).toBe('new-refresh');
    expect(JSON.parse(localStorage.getItem('tokens'))).toEqual({
      access: 'new-access',
      refresh: 'new-refresh',
    });
  });

  it('clears every stored auth key', () => {
    setTokens('a', 'r');
    clearTokens();

    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
    expect(localStorage.getItem('accessToken')).toBeNull();
    expect(localStorage.getItem('refreshToken')).toBeNull();
    expect(localStorage.getItem('tokens')).toBeNull();
  });

  it('stores tokens in sessionStorage when remember me is off', () => {
    setTokens('session-access', 'session-refresh', { rememberMe: false });

    expect(sessionStorage.getItem('access_token')).toBe('session-access');
    expect(sessionStorage.getItem('refresh_token')).toBe('session-refresh');
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('chessmate_remember_me')).toBe('false');
  });
});
