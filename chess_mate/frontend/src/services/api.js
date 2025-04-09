import axios from 'axios';
import { jwtDecode } from "jwt-decode";
import { toast } from 'react-hot-toast';
import { API_URL } from '../config';

// Get the base URL from environment variables or use a default
const getBaseUrl = () => {
    return API_URL || 'http://localhost:8000';
};

const API_BASE_URL = getBaseUrl();

console.log('API Configuration:', {
    baseURL: API_BASE_URL,
    fullLocation: window.location
});

// Create axios instance with default config
const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true,  // Required for CORS with credentials
    xsrfCookieName: 'csrftoken',  // Django's CSRF cookie name
    xsrfHeaderName: 'X-CSRFToken',  // Django's CSRF header name
    timeout: 15000, // 15 second timeout
});

// Track token refresh promise to prevent multiple simultaneous refreshes
let isRefreshing = false;
let refreshPromise = null;
let refreshSubscribers = [];

// Subscribe to token refresh
const subscribeTokenRefresh = (callback) => {
    refreshSubscribers.push(callback);
};

// Notify subscribers that token has been refreshed
const onTokenRefreshed = (token) => {
    refreshSubscribers.forEach(callback => callback(token));
    refreshSubscribers = [];
};

// Check if endpoint is an auth endpoint
const isAuthEndpoint = (url) => {
    const authEndpoints = [
        '/api/v1/auth/login/',
        '/api/v1/auth/register/',
        '/api/v1/auth/token/refresh/',
        '/api/v1/auth/reset-password/',
        '/api/v1/auth/reset-password/confirm/',
        '/api/v1/auth/verify-email/',
        '/api/v1/auth/csrf/',
        '/api/v1/auth/logout/'
    ];
    return authEndpoints.some(endpoint => url.includes(endpoint));
};

// Get CSRF token from cookie or fetch from server
const getCsrfToken = async () => {
    try {
        // Try to get CSRF token from cookie first
        const csrfToken = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];

        if (csrfToken) {
            return csrfToken;
        }

        // If no token in cookie, fetch it from the server
        const response = await axios.get(`${API_BASE_URL}/api/v1/auth/csrf/`, { 
            withCredentials: true,
            timeout: 5000 // 5 second timeout for CSRF token fetch
        });
        return response.data.csrfToken;
    } catch (error) {
        console.error('Error fetching CSRF token:', error);
        return null;
    }
};

// Check if endpoint requires CSRF
const requiresCsrf = (url, method) => {
    // GET, OPTIONS, and HEAD requests are exempt from CSRF protection
    if (['get', 'options', 'head'].includes(method.toLowerCase())) {
        return false;
    }

    // Auth endpoints have special handling via auth_csrf_exempt on the backend
    if (isAuthEndpoint(url)) {
        return false;
    }

    // All other POST, PUT, PATCH, DELETE requests need CSRF token
    return true;
};

// Unified function to get and set the access token
const getAccessToken = () => {
    // Try all possible storage locations
    const accessToken = localStorage.getItem('access_token') || localStorage.getItem('accessToken');
    
    // Check old format
    const oldTokens = localStorage.getItem('tokens');
    if (!accessToken && oldTokens) {
        try {
            const { access } = JSON.parse(oldTokens);
            return access;
        } catch (e) {
            console.error('Error parsing old tokens format:', e);
        }
    }
    
    return accessToken;
};

// Set access token with consistent key name
const setAccessToken = (token) => {
    localStorage.setItem('access_token', token);
    // Also update old format for backward compatibility
    const oldTokens = localStorage.getItem('tokens');
    if (oldTokens) {
        try {
            const tokens = JSON.parse(oldTokens);
            tokens.access = token;
            localStorage.setItem('tokens', JSON.stringify(tokens));
        } catch (e) {
            console.error('Error updating old tokens format:', e);
        }
    }
};

// Get refresh token from any storage location
const getRefreshToken = () => {
    const refreshToken = localStorage.getItem('refresh_token') || localStorage.getItem('refreshToken');
    
    // Check old format
    const oldTokens = localStorage.getItem('tokens');
    if (!refreshToken && oldTokens) {
        try {
            const { refresh } = JSON.parse(oldTokens);
            return refresh;
        } catch (e) {
            console.error('Error parsing old tokens format:', e);
        }
    }
    
    return refreshToken;
};

// Unified token refresh function that returns a promise
const refreshTokenAsync = async () => {
    // Use existing promise if already refreshing
    if (refreshPromise) {
        return refreshPromise;
    }
    
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
        return Promise.reject(new Error('No refresh token available'));
    }
    
    // Create and store the refresh promise
    refreshPromise = axios.post(`${API_BASE_URL}/api/v1/auth/token/refresh/`, {
        refresh: refreshToken
    }, {
        withCredentials: true
    })
    .then(response => {
        if (response.data && response.data.access) {
            setAccessToken(response.data.access);
            return response.data.access;
        }
        throw new Error('Invalid token refresh response');
    })
    .catch(error => {
        console.error('Token refresh failed:', error);
        // Clear tokens on refresh failure
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('tokens');
        throw error;
    })
    .finally(() => {
        // Clear the promise reference when done
        refreshPromise = null;
        isRefreshing = false;
    });
    
    return refreshPromise;
};

// Setup request interceptor for CSRF and Auth
api.interceptors.request.use(async (config) => {
    // Add auth token if available
    const accessToken = getAccessToken();
    
    if (accessToken && !isTokenExpired(accessToken)) {
        config.headers.Authorization = `Bearer ${accessToken}`;
    } else if (accessToken && isTokenExpired(accessToken) && !isAuthEndpoint(config.url)) {
        // Token is expired, try to refresh automatically before request
        try {
            const newToken = await refreshTokenAsync();
            config.headers.Authorization = `Bearer ${newToken}`;
        } catch (error) {
            console.error('Failed to refresh token before request:', error);
            // Continue with request without token - will be handled by response interceptor
        }
    }

    // Add CSRF token if required
    if (requiresCsrf(config.url, config.method)) {
        const token = await getCsrfToken();
        if (token) {
            config.headers['X-CSRFToken'] = token;
        }
    }

    return config;
}, (error) => {
    return Promise.reject(error);
});

// Setup response interceptor for error handling
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        // Handle CORS errors specifically
        if (error.message === 'Network Error') {
            console.error('CORS or Network Error:', error);
            toast.error('Unable to connect to the server. Please try again.', {
                id: 'network-error',
                duration: 3000
            });
            return Promise.reject(error);
        }

        const originalRequest = error.config;

        // Handle 403 Forbidden (CSRF errors)
        if (error.response?.status === 403 && !originalRequest._csrfRetry) {
            originalRequest._csrfRetry = true;

            // Refresh CSRF token and retry the request
            try {
                await refreshCsrfToken();
                const newToken = await getCsrfToken();
                if (newToken) {
                    originalRequest.headers['X-CSRFToken'] = newToken;
                    return api(originalRequest);
                }
            } catch (csrfError) {
                console.error('Error refreshing CSRF token:', csrfError);
            }
        }

        // Handle 401 errors - token expired or invalid
        if (error.response?.status === 401 && !originalRequest._retry) {
            // Skip token refresh for auth endpoints
            if (isAuthEndpoint(originalRequest.url)) {
                return Promise.reject(error);
            }

            originalRequest._retry = true;

            // If already refreshing, wait for it to complete
            if (isRefreshing) {
                try {
                    const token = await new Promise(resolve => {
                        subscribeTokenRefresh(resolve);
                    });
                    originalRequest.headers['Authorization'] = `Bearer ${token}`;
                    return api(originalRequest);
                } catch (waitError) {
                    return Promise.reject(waitError);
                }
            }

            // Start refresh process
            isRefreshing = true;

            try {
                const newToken = await refreshTokenAsync();
                // Update request authorization header
                originalRequest.headers['Authorization'] = `Bearer ${newToken}`;
                // Notify subscribers
                onTokenRefreshed(newToken);
                // Retry original request
                return api(originalRequest);
            } catch (refreshError) {
                console.error('Token refresh failed:', refreshError);
                // Handle authentication failure
                if (window.location.pathname !== '/login') {
                    toast.error('Your session has expired. Please log in again.', {
                        id: 'session-expired',
                        duration: 5000
                    });
                    
                    // Redirect to login after short delay
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 1500);
                }
                return Promise.reject(refreshError);
            }
        }

        // Handle other errors
        if (error.response?.status === 404) {
            console.error('API Endpoint not found (404):', error.config.url);
        }
        
        if (error.response?.data?.detail) {
            toast.error(error.response.data.detail);
        } else if (error.response?.data?.message) {
            toast.error(error.response.data.message);
        } else if (error.message && !error.message.includes('Network Error')) {
            toast.error(`Error: ${error.message}`);
        }

        return Promise.reject(error);
    }
);

// Check if JWT token is expired
const isTokenExpired = (token) => {
    try {
        const decoded = jwtDecode(token);
        const currentTime = Date.now() / 1000;
        return decoded.exp < currentTime;
    } catch (error) {
        console.error('Error decoding token:', error);
        return true; // Assume expired on error
    }
};

// Refresh CSRF token
const refreshCsrfToken = async () => {
    try {
        await axios.get(`${API_BASE_URL}/api/v1/auth/csrf/`, { 
            withCredentials: true,
            timeout: 5000
        });
        return true;
    } catch (error) {
        console.error('Error refreshing CSRF token:', error);
        return false;
    }
};

export default api;
