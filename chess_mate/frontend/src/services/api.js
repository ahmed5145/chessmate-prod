import axios from 'axios';
import { jwtDecode } from "jwt-decode";

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
    withCredentials: true
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
    refreshSubscribers.map(callback => callback(token));
    refreshSubscribers = [];
};

// Helper function to get CSRF token
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

        // If no token in cookie, fetch from server
        console.log('Fetching CSRF token from server...');
        const response = await axios.get(`${API_BASE_URL}/api/csrf/`, { 
            withCredentials: true,
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        console.log('CSRF token response:', response.data);
        return response.data.csrfToken;
    } catch (error) {
        console.error('Error fetching CSRF token:', error);
        return null;
    }
};

// Helper function to set CSRF token after auth
const setCsrfAfterAuth = async () => {
    try {
        // Fetch new CSRF token
        const response = await axios.get(`${API_BASE_URL}/api/csrf/`, {
            withCredentials: true,
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        // The Django backend will set the CSRF cookie automatically
        return response.data.csrfToken;
    } catch (error) {
        console.error('Error setting CSRF token after auth:', error);
        return null;
    }
};

// Request interceptor to add authorization token
api.interceptors.request.use(
    (config) => {
        const tokens = localStorage.getItem('tokens');
        if (tokens) {
            const { access } = JSON.parse(tokens);
            config.headers.Authorization = `Bearer ${access}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        // If the error is 401 and we haven't tried to refresh the token yet
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            try {
                // Get the refresh token
                const tokens = localStorage.getItem('tokens');
                if (!tokens) {
                    throw new Error('No refresh token available');
                }

                const { refresh } = JSON.parse(tokens);
                
                // Try to get a new access token
                const response = await axios.post('/api/token/refresh/', { refresh });
                
                if (response.data.access) {
                    // Update the tokens in localStorage
                    localStorage.setItem('tokens', JSON.stringify({
                        ...JSON.parse(tokens),
                        access: response.data.access
                    }));

                    // Update the authorization header
                    originalRequest.headers.Authorization = `Bearer ${response.data.access}`;
                    
                    // Retry the original request
                    return api(originalRequest);
                }
            } catch (refreshError) {
                // If refresh fails, clear tokens and redirect to login
                localStorage.removeItem('tokens');
                window.location.href = '/login';
                return Promise.reject(refreshError);
            }
        }

        return Promise.reject(error);
    }
);

// Helper function to check if token is expired
const isTokenExpired = (token) => {
    try {
        const decoded = jwtDecode(token);
        const currentTime = Date.now() / 1000;
        return decoded.exp < currentTime;
    } catch (error) {
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

export default api; 