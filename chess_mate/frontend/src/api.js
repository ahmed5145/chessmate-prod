import axios from "axios";
import { jwtDecode } from "jwt-decode";

// API Configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Token refresh queue to prevent race conditions
let isRefreshing = false;
let refreshSubscribers = [];

// Subscribe to token refresh
const subscribeTokenRefresh = (cb) => refreshSubscribers.push(cb);

// Execute subscribers with new token
const onRefreshed = (token) => {
  refreshSubscribers.map(cb => cb(token));
  refreshSubscribers = [];
};

// Add request interceptor to add auth token
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

// Add response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      if (!isRefreshing) {
        isRefreshing = true;
        
        try {
          const tokens = localStorage.getItem('tokens');
          if (!tokens) {
            throw new Error('No refresh token available');
          }
          
          const { refresh } = JSON.parse(tokens);
          const response = await axios.post(`${API_BASE_URL}/token/refresh/`, {
            refresh: refresh
          });
          
          const { access } = response.data;
          const newTokens = JSON.parse(tokens);
          newTokens.access = access;
          localStorage.setItem('tokens', JSON.stringify(newTokens));
          
          onRefreshed(access);
          originalRequest.headers.Authorization = `Bearer ${access}`;
          return api(originalRequest);
        } catch (refreshError) {
          refreshSubscribers = [];
          localStorage.removeItem('tokens');
          window.location.href = '/';
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      }
      
      // If refresh is already in progress, wait for it to complete
      return new Promise(resolve => {
        subscribeTokenRefresh(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          resolve(api(originalRequest));
        });
      });
    }
    
    return Promise.reject(error);
  }
);

// Helper function to add the Authorization header if the user is authenticated
const setAuthHeader = (token) => {
  if (token) {
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common["Authorization"];
  }
};

// Helper function to check if the user is online
const isUserOnline = () => {
  return navigator.onLine;
};

// Helper function to remove tokens if they are expired and the user is not online
const removeExpiredTokens = () => {
  const accessToken = localStorage.getItem("access_token");
  const refreshToken = localStorage.getItem("refresh_token");

  if (accessToken) {
    const decodedAccessToken = jwtDecode(accessToken);
    const currentTime = Date.now() / 1000;

    if (decodedAccessToken.exp < currentTime && !isUserOnline()) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      setAuthHeader(null);
    }
  }

  if (refreshToken) {
    const decodedRefreshToken = jwtDecode(refreshToken);
    const currentTime = Date.now() / 1000;

    if (decodedRefreshToken.exp < currentTime && !isUserOnline()) {
      localStorage.removeItem("refresh_token");
    }
  }
};

// Call removeExpiredTokens on script load
removeExpiredTokens();

// Helper function to get CSRF token
const getCsrfToken = async () => {
  try {
    await axios.get(`${API_BASE_URL}/csrf/`, { withCredentials: true });
    return document.cookie.split('; ')
      .find(row => row.startsWith('csrftoken='))
      ?.split('=')[1];
  } catch (error) {
    console.error('Error fetching CSRF token:', error);
    return null;
  }
};

// Refresh the access token
export const refreshToken = async (refreshToken) => {
  try {
    const response = await api.post("/token/refresh/", { refresh: refreshToken });
    const { access } = response.data;
    setAuthHeader(access); // Set the new access token
    localStorage.setItem("access_token", access); // Update the access token in local storage
    return access;
  } catch (error) {
    throw new Error(error.response ? error.response.data : error.message);
  }
};

// API functions

// Register a new user
export const registerUser = async (userData) => {
  try {
    const response = await api.post("/register/", userData);
    return response.data;
  } catch (error) {
    throw new Error(error.response ? error.response.data : error.message);
  }
};

// Login a user
export const loginUser = async (credentials) => {
  try {
    // Remove existing tokens before attempting to login
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("tokens");
    setAuthHeader(null);

    const csrfToken = await getCsrfToken();
    
    const response = await api.post("/login/", credentials, {
      headers: {
        'X-CSRFToken': csrfToken,
      },
    });
    
    const { tokens, message } = response.data;
    
    if (!tokens || !tokens.access || !tokens.refresh) {
      throw new Error("Invalid response from server");
    }
    
    // Store tokens
    localStorage.setItem("access_token", tokens.access);
    localStorage.setItem("refresh_token", tokens.refresh);
    localStorage.setItem("tokens", JSON.stringify(tokens));
    
    // Set authorization header for future requests
    setAuthHeader(tokens.access);
    
    return {
      message: message || "Login successful!",
      tokens
    };
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data);
    }
    throw new Error(error.message || "Login failed");
  }
};

// Fetch games for the authenticated user
export const fetchUserGames = async () => {
  try {
    const response = await api.get("/dashboard/");
    return response.data.games;
  } catch (error) {
    throw new Error(error.response ? error.response.data : error.message);
  }
};

// Fetch games from an external platform
export const fetchExternalGames = async (platform, username, gameType) => {
  try {
    // Handle "all" game type by using "rapid" as default
    const effectiveGameType = gameType === "all" ? "rapid" : gameType;
    
    const response = await api.post("/fetch-games/", {
      platform,
      username,
      game_type: effectiveGameType
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response ? error.response.data : error.message);
  }
};

// Analyze a specific game
export const analyzeSpecificGame = async (gameId) => {
  try {
    const response = await api.post(`/game/${gameId}/analysis/`, {
      depth: 20,
      use_ai: true
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      if (error.response.status === 401) {
        throw new Error("Session expired. Please log in again.");
      }
      throw new Error(error.response.data);
    } else if (error.request) {
      // The request was made but no response was received
      throw new Error("No response from server. Please try again.");
    } else {
      // Something happened in setting up the request that triggered an Error
      throw new Error("Failed to analyze game. Please try again.");
    }
  }
};

// Analyze a batch of games
export const analyzeBatchGames = async (numGames) => {
  try {
    const response = await api.post("/games/batch-analyze/", { num_games: parseInt(numGames, 10) });
    return response.data;
  } catch (error) {
    throw new Error(error.response ? error.response.data : error.message);
  }
};

// Fetch analysis for a game
export const fetchGameAnalysis = async (gameId) => {
  try {
    const response = await api.get(`/game/${gameId}/analysis/`);
    return response.data.analysis;
  } catch (error) {
    throw new Error(error.response ? error.response.data : error.message);
  }
};

// Fetch feedback for a specific game
export const fetchGameFeedback = async (gameId) => {
  try {
    const response = await api.get(`/feedback/${gameId}/`);
    return response.data.feedback;
  } catch (error) {
    throw new Error(error.response ? error.response.data : error.message);
  }
};

// Fetch all available games
export const fetchAllGames = async () => {
  try {
    const response = await api.get("/games/");
    return response.data;
  } catch (error) {
    throw new Error(error.response ? error.response.data : error.message);
  }
};

// Log out the user
export const logoutUser = async () => {
  try {
    const refreshToken = localStorage.getItem("refresh_token");
    if (refreshToken) {
      await api.post("/logout/", { refresh_token: refreshToken });
    }
  } catch (error) {
    console.error("Error logging out:", error);
  } finally {
    setAuthHeader(null);
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("tokens");
  }
};

export const requestPasswordReset = async (email) => {
  const response = await fetch(`${API_BASE_URL}/auth/password-reset/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email }),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Failed to request password reset");
  }
  return data;
};

export const resetPassword = async (uid, token, newPassword) => {
  const response = await fetch(`${API_BASE_URL}/auth/password-reset/confirm/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ uid, token, new_password: newPassword }),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Failed to reset password");
  }
  return data;
};

const getToken = () => {
  const tokens = localStorage.getItem('tokens');
  if (!tokens) {
    throw new Error('No authentication token found');
  }
  return JSON.parse(tokens).access;
};

export const getUserProfile = async () => {
  const response = await fetch(`${API_BASE_URL}/profile/`, {
    headers: {
      'Authorization': `Bearer ${getToken()}`,
    },
  });

  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.error || 'Failed to fetch profile');
    error.status = response.status;
    throw error;
  }
  return data;
};

export const updateUserProfile = async (profileData) => {
  const response = await fetch(`${API_BASE_URL}/profile/`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${getToken()}`,
    },
    body: JSON.stringify(profileData),
  });

  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.error || 'Failed to update profile');
    error.status = response.status;
    throw error;
  }
  return data;
};
