/**
 * Auth token persistence for "Remember me".
 *
 * - Remember me ON: localStorage (survives browser restart) + longer refresh token from API.
 * - Remember me OFF: sessionStorage only (cleared when the browser session ends).
 *
 * Preference is stored in localStorage so the login checkbox restores the last choice.
 */

const REMEMBER_PREF_KEY = 'chessmate_remember_me';
const TOKEN_KEYS = ['access_token', 'refresh_token', 'accessToken', 'refreshToken', 'tokens'];

export const getRememberMePreference = () => localStorage.getItem(REMEMBER_PREF_KEY) !== 'false';

export const setRememberMePreference = (rememberMe) => {
  localStorage.setItem(REMEMBER_PREF_KEY, rememberMe ? 'true' : 'false');
};

export const getActiveTokenStorage = () => (
  getRememberMePreference() ? localStorage : sessionStorage
);

const readLegacyAccess = (storage) => {
  const tokensRaw = storage.getItem('tokens');
  if (!tokensRaw) {
    return null;
  }
  try {
    return JSON.parse(tokensRaw).access || null;
  } catch {
    return null;
  }
};

const readLegacyRefresh = (storage) => {
  const tokensRaw = storage.getItem('tokens');
  if (!tokensRaw) {
    return null;
  }
  try {
    return JSON.parse(tokensRaw).refresh || null;
  } catch {
    return null;
  }
};

export const readAccessToken = () => {
  const storage = getActiveTokenStorage();
  return (
    storage.getItem('access_token')
    || storage.getItem('accessToken')
    || readLegacyAccess(storage)
  );
};

export const readRefreshToken = () => {
  const storage = getActiveTokenStorage();
  return (
    storage.getItem('refresh_token')
    || storage.getItem('refreshToken')
    || readLegacyRefresh(storage)
  );
};

export const writeTokens = (accessToken, refreshToken, rememberMe = true) => {
  setRememberMePreference(rememberMe);
  clearAllTokenStorage();

  const storage = rememberMe ? localStorage : sessionStorage;

  if (accessToken) {
    storage.setItem('access_token', accessToken);
    storage.setItem('accessToken', accessToken);
  }
  if (refreshToken) {
    storage.setItem('refresh_token', refreshToken);
    storage.setItem('refreshToken', refreshToken);
  }
  if (accessToken || refreshToken) {
    storage.setItem('tokens', JSON.stringify({
      access: accessToken || null,
      refresh: refreshToken || null,
    }));
  }
};

export const writeAccessToken = (accessToken) => {
  const storage = getActiveTokenStorage();
  if (accessToken) {
    storage.setItem('access_token', accessToken);
    storage.setItem('accessToken', accessToken);
    const refreshToken = readRefreshToken();
    storage.setItem('tokens', JSON.stringify({
      access: accessToken,
      refresh: refreshToken || null,
    }));
  }
};

export const clearAllTokenStorage = () => {
  TOKEN_KEYS.forEach((key) => {
    localStorage.removeItem(key);
    sessionStorage.removeItem(key);
  });
};
