import axios from 'axios';

// Get the API URL from environment variables, with a production fallback
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://3.133.97.72/api';

console.log('API_BASE_URL:', API_BASE_URL); // Debug log

// Create axios instance with default config
const api = axios.create({
    baseURL: API_BASE_URL,
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
    }
});

// Helper function to get CSRF token
const getCsrfToken = async () => {
    try {
        const response = await axios.get(`${API_BASE_URL}/csrf/`, { 
            withCredentials: true,
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            }
        });
        const token = document.cookie.split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        
        console.log('CSRF Token:', token); // Debug log
        return token;
    } catch (error) {
        console.error('Error fetching CSRF token:', error);
        return null;
    }
};

// Add request interceptor to include CSRF token
api.interceptors.request.use(async (config) => {
    console.log('Request URL:', config.url); // Debug log
    
    if (['post', 'put', 'patch', 'delete'].includes(config.method?.toLowerCase())) {
        const csrfToken = await getCsrfToken();
        if (csrfToken) {
            config.headers['X-CSRFToken'] = csrfToken;
        }
    }
    return config;
}, (error) => {
    return Promise.reject(error);
});

// Add response interceptor to handle errors
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        console.error('API Error:', error.response || error); // Debug log
        
        const originalRequest = error.config;
        
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;
            
            try {
                const refreshToken = localStorage.getItem('refresh_token');
                if (refreshToken) {
                    const response = await api.post('/token/refresh/', { refresh: refreshToken });
                    const { access } = response.data;
                    
                    localStorage.setItem('access_token', access);
                    api.defaults.headers.common['Authorization'] = `Bearer ${access}`;
                    originalRequest.headers['Authorization'] = `Bearer ${access}`;
                    
                    return api(originalRequest);
                }
            } catch (refreshError) {
                console.error('Error refreshing token:', refreshError);
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                window.location.href = '/login';
            }
        }
        
        return Promise.reject(error);
    }
);

export default api; 