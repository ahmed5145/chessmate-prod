// Token storage helper functions
export const getAccessToken = () => {
    // Try new format first
    const accessToken = localStorage.getItem('accessToken');
    if (accessToken) return accessToken;
    
    // Fall back to old format
    try {
        const tokens = JSON.parse(localStorage.getItem('tokens') || '{}');
        return tokens.access || null;
    } catch (e) {
        console.error('Error parsing tokens from localStorage:', e);
        return null;
    }
};

export const getRefreshToken = () => {
    // Try new format first
    const refreshToken = localStorage.getItem('refreshToken');
    if (refreshToken) return refreshToken;
    
    // Fall back to old format
    try {
        const tokens = JSON.parse(localStorage.getItem('tokens') || '{}');
        return tokens.refresh || null;
    } catch (e) {
        console.error('Error parsing tokens from localStorage:', e);
        return null;
    }
};

export const setTokens = (accessToken, refreshToken) => {
    // Store in both formats for backward compatibility
    if (accessToken) {
        localStorage.setItem('accessToken', accessToken);
    } else {
        localStorage.removeItem('accessToken');
    }
    
    if (refreshToken) {
        localStorage.setItem('refreshToken', refreshToken);
    }
    
    // Also update old format
    const tokensObj = {
        access: accessToken || null,
        refresh: refreshToken || null
    };
    
    if (accessToken || refreshToken) {
        localStorage.setItem('tokens', JSON.stringify(tokensObj));
    } else {
        localStorage.removeItem('tokens');
    }
    
    return tokensObj;
};

export const clearTokens = () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('tokens');
};

export const refreshTokens = async () => {
    try {
        const refreshToken = getRefreshToken();
        
        if (!refreshToken) {
            console.warn('No refresh token available');
            return null;
        }
        
        const response = await fetch('http://localhost:8000/api/v1/auth/token/refresh/', { // TODO: change to production url in production
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
            // Store the new tokens
            setTokens(data.access, data.refresh || refreshToken);
            return data;
        }
        
        throw new Error('Invalid token refresh response');
    } catch (error) {
        console.error('Error refreshing token:', error);
        return null;
    }
};

export const resetPassword = async (token, newPassword) => {
    try {
        const response = await fetch('http://localhost:8000/api/v1/auth/reset-password/confirm/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
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
        // Get tokens using helper functions
        const accessToken = getAccessToken();
        const refreshToken = getRefreshToken();
        
        if (!accessToken && !refreshToken) {
            return false;
        }
        
        // If we have an access token, verify it's not expired
        if (accessToken) {
            try {
                // Parse the JWT to check expiration
                const base64Url = accessToken.split('.')[1];
                const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
                const jsonPayload = decodeURIComponent(atob(base64).split('').map(c => {
                    return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                }).join(''));
                
                const { exp } = JSON.parse(jsonPayload);
                
                // If token is not expired, user is authenticated
                if (exp * 1000 > Date.now()) {
                    return true;
                }
            } catch (e) {
                console.error('Error parsing JWT:', e);
            }
        }
        
        // If access token is expired but we have refresh token, try to refresh
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