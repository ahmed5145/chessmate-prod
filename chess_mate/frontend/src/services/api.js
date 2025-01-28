import axios from 'axios';
import { jwtDecode } from "jwt-decode";

const API_BASE_URL = (process.env.REACT_APP_API_URL || 'http://localhost:8000').replace(/\/$/, '');

// Create axios instance
const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
    }
});

// Request interceptor
api.interceptors.request.use(
    async (config) => {
        // Get CSRF token if not present
        if (!document.cookie.includes('csrftoken')) {
            await getCsrfToken();
        }
        
        // Add CSRF token to headers
        const csrfToken = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
            
        if (csrfToken) {
            config.headers['X-CSRFToken'] = csrfToken;
        }

        // Add authorization token if present
        const tokens = localStorage.getItem('tokens');
        if (tokens) {
            const { access } = JSON.parse(tokens);
            config.headers.Authorization = `Bearer ${access}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;
        
        // Handle 401 (Unauthorized)
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;
            
            try {
                const tokens = localStorage.getItem('tokens');
                if (tokens) {
                    const { refresh } = JSON.parse(tokens);
                    const response = await axios.post(`${API_BASE_URL}/api/token/refresh/`, 
                        { refresh },
                        { withCredentials: true }
                    );
                    const { access } = response.data;
                    
                    localStorage.setItem('tokens', JSON.stringify({ access, refresh }));
                    originalRequest.headers.Authorization = `Bearer ${access}`;
                    
                    return api(originalRequest);
                }
            } catch (refreshError) {
                console.error('Token refresh failed:', refreshError);
                localStorage.removeItem('tokens');
                window.location.href = '/login';
            }
        }
        
        // Handle 403 (Forbidden)
        if (error.response?.status === 403) {
            console.error('Forbidden access:', error.response.data);
            // Try to refresh CSRF token
            if (error.response.data.includes('CSRF')) {
                await getCsrfToken();
                return api(originalRequest);
            }
        }
        
        return Promise.reject(error);
    }
);

// Helper function to get CSRF token
const getCsrfToken = async () => {
    try {
        const response = await axios.get(`${API_BASE_URL}/api/csrf/`, { 
            withCredentials: true,
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        return response.data.csrfToken;
    } catch (error) {
        console.error('Error fetching CSRF token:', error);
        return null;
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
        const currentTime = Date.now() / 1000;
        
        if (parsedTokens.access) {
            const decodedAccess = jwtDecode(parsedTokens.access);
            if (decodedAccess.exp < currentTime && !isUserOnline()) {
                localStorage.removeItem('tokens');
                api.defaults.headers.common['Authorization'] = null;
            }
        }
    } catch (error) {
        console.error('Error checking token expiration:', error);
        localStorage.removeItem('tokens');
    }
};

// Call removeExpiredTokens on script load
removeExpiredTokens();

export default api; 