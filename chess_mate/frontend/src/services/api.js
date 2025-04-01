import axios from 'axios';
import { jwtDecode } from "jwt-decode";
import { toast } from 'react-hot-toast';

// Get the base URL from environment variables or use a default
const getBaseUrl = () => {
    return process.env.REACT_APP_API_URL || 'http://localhost:8000';
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
});

// Track token refresh promise to prevent multiple simultaneous refreshes
let isRefreshing = false;
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
        '/api/login/',
        '/api/register/',
        '/api/token/refresh/',
        '/api/auth/password-reset/',
        '/api/auth/password-reset/confirm/',
        '/api/verify-email/',
        '/api/csrf/',
        '/api/logout/'
    ];
    return authEndpoints.some(endpoint => url.includes(endpoint));
};

// Get CSRF token from cookie or fetch from server
const getCsrfToken = async () => {
    try {
        // For auth endpoints, we don't need CSRF token
        const currentUrl = window.location.pathname;
        if (currentUrl.includes('login') || currentUrl.includes('register')) {
            return null;
        }

        // Try to get CSRF token from cookie first
        const csrfToken = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
            
        if (csrfToken) {
            return csrfToken;
        }

        // If no token in cookie, fetch it from the server
        const response = await axios.get(`${API_BASE_URL}/api/csrf/`, { withCredentials: true });
        return response.data.csrfToken;
    } catch (error) {
        console.error('Error fetching CSRF token:', error);
        return null;
    }
};

// Check if endpoint requires CSRF
const requiresCsrf = (url, method) => {
    // Auth endpoints are exempt from CSRF
    if (isAuthEndpoint(url)) {
        return false;
    }
    return !['get', 'options', 'head'].includes(method.toLowerCase());
};

// Setup request interceptor for CSRF and Auth
api.interceptors.request.use(async (config) => {
    // Add CORS headers for all requests
    config.headers['Access-Control-Allow-Origin'] = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    config.headers['Access-Control-Allow-Credentials'] = 'true';
    
    // For auth endpoints, we need special handling
    if (isAuthEndpoint(config.url)) {
        // Don't add CSRF token for auth endpoints
        return {
            ...config,
            headers: {
                ...config.headers,
                'Content-Type': 'application/json',
            }
        };
    }

    // Add auth token if available
    const tokens = localStorage.getItem('tokens');
    if (tokens) {
        try {
            const { access } = JSON.parse(tokens);
            if (access && !isTokenExpired(access)) {
                config.headers.Authorization = `Bearer ${access}`;
            }
        } catch (error) {
            console.error('Error parsing tokens:', error);
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
            toast.error('Unable to connect to the server. Please try again.');
            return Promise.reject(error);
        }

        const originalRequest = error.config;
        
        // Handle 401 errors
        if (error.response?.status === 401 && !originalRequest._retry) {
            // Skip token refresh for auth endpoints
            if (isAuthEndpoint(originalRequest.url)) {
                return Promise.reject(error);
            }

            if (isRefreshing) {
                try {
                    const token = await new Promise(resolve => subscribeTokenRefresh(resolve));
                    originalRequest.headers['Authorization'] = `Bearer ${token}`;
                    return api(originalRequest);
                } catch (error) {
                    return Promise.reject(error);
                }
            }

            originalRequest._retry = true;
            isRefreshing = true;
            
            try {
                const tokens = JSON.parse(localStorage.getItem('tokens') || '{}');
                if (!tokens.refresh) {
                    throw new Error('No refresh token available');
                }

                const response = await api.post('/api/token/refresh/', {
                    refresh: tokens.refresh
                });
                
                if (response.data.access) {
                    const newTokens = {
                        ...tokens,
                        access: response.data.access
                    };
                    localStorage.setItem('tokens', JSON.stringify(newTokens));
                    api.defaults.headers.common['Authorization'] = `Bearer ${response.data.access}`;
                    onTokenRefreshed(response.data.access);
                    return api(originalRequest);
                }
            } catch (refreshError) {
                console.error('Token refresh failed:', refreshError);
                localStorage.removeItem('tokens');
                window.location.href = '/login';
            } finally {
                isRefreshing = false;
            }
        }

        // Show error toast for user feedback
        const errorMessage = error.response?.data?.detail || 
                           error.response?.data?.error ||
                           error.message ||
                           'An error occurred';
        toast.error(errorMessage);

        return Promise.reject(error);
    }
);

// Helper function to check if token is expired
const isTokenExpired = (token) => {
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return payload.exp * 1000 < Date.now();
    } catch {
        return true;
    }
};

// Helper function to check if the user is online
const isUserOnline = () => navigator.onLine;

// Helper function to remove expired tokens
const removeExpiredTokens = () => {
    const tokens = localStorage.getItem('tokens');
    if (!tokens) return;
    
    try {
        const parsedTokens = JSON.parse(tokens);
        if (parsedTokens.access && isTokenExpired(parsedTokens.access)) {
            localStorage.removeItem('tokens');
            api.defaults.headers.common['Authorization'] = null;
        }
    } catch (error) {
        console.error('Error checking token expiration:', error);
        localStorage.removeItem('tokens');
    }
};

// Call removeExpiredTokens on script load
removeExpiredTokens();

// Helper function to ensure CSRF token after auth
const setCsrfAfterAuth = async () => {
    try {
        await getCsrfToken();
        return true;
    } catch (error) {
        console.error('Failed to set CSRF token after auth:', error);
        return false;
    }
};

export { setCsrfAfterAuth };
export default api; 