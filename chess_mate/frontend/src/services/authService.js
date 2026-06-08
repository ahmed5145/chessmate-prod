import { API_URL } from '../config';
import {
  clearAllTokenStorage,
  getRememberMePreference,
  readAccessToken,
  readRefreshToken,
  writeAccessToken,
  writeTokens,
} from '../utils/tokenStorage';

const buildApiUrl = (path) => {
    const base = (API_URL || '').replace(/\/$/, '');
    const suffix = path.startsWith('/') ? path : `/${path}`;
    return `${base}${suffix}`;
};

// Token storage helper functions
export const getAccessToken = () => readAccessToken();

export const getRefreshToken = () => readRefreshToken();

export const setTokens = (accessToken, refreshToken, options = {}) => {
    const rememberMe = options.rememberMe !== false;
    writeTokens(accessToken, refreshToken, rememberMe);
    return {
        access: accessToken || null,
        refresh: refreshToken || null,
    };
};

export const setAccessToken = (accessToken) => {
    writeAccessToken(accessToken);
};

export const clearTokens = () => {
    clearAllTokenStorage();
};

export const refreshTokens = async () => {
    try {
        const refreshToken = getRefreshToken();

        if (!refreshToken) {
            console.warn('No refresh token available');
            return null;
        }

        const response = await fetch(buildApiUrl('/api/v1/auth/token/refresh/'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ refresh: refreshToken }),
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`Token refresh failed with status: ${response.status}`);
        }

        const data = await response.json();

        if (data && data.access) {
            setTokens(data.access, data.refresh || refreshToken, {
                rememberMe: getRememberMePreference(),
            });
            return data;
        }

        throw new Error('Invalid token refresh response');
    } catch (error) {
        console.error('Error refreshing token:', error);
        return null;
    }
};

export const resetPassword = async (uid, token, newPassword) => {
    try {
        const response = await fetch(buildApiUrl('/api/v1/auth/reset-password/confirm/'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                uid,
                token,
                new_password: newPassword
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || 'Failed to reset password. The link may have expired.');
        }

        return await response.json();
    } catch (error) {
        console.error('Password reset error:', error);
        throw error;
    }
};

export const checkAuthStatus = async () => {
    try {
        const accessToken = getAccessToken();
        const refreshToken = getRefreshToken();

        if (!accessToken && !refreshToken) {
            return false;
        }

        if (accessToken) {
            try {
                const base64Url = accessToken.split('.')[1];
                const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
                const jsonPayload = decodeURIComponent(atob(base64).split('').map(c => {
                    return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                }).join(''));

                const { exp } = JSON.parse(jsonPayload);

                if (exp * 1000 > Date.now()) {
                    return true;
                }
            } catch (e) {
                console.error('Error parsing JWT:', e);
            }
        }

        if (refreshToken) {
            try {
                const response = await refreshTokens();
                return response && response.access !== undefined;
            } catch (e) {
                console.error('Error refreshing token:', e);
                return false;
            }
        }

        return false;
    } catch (error) {
        console.error('Error checking auth status:', error);
        return false;
    }
};
