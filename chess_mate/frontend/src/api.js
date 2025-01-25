import { jwtDecode } from "jwt-decode";
import api from './api/requests';

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
          const response = await api.post("/token/refresh/", { refresh: refresh });
          
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
      api.defaults.headers.common["Authorization"] = null;
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

// API functions
export const loginUser = async (credentials) => {
    try {
        // Remove existing tokens before attempting to login
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("tokens");

        const response = await api.post("/login/", credentials);
        const { tokens, message } = response.data;

        if (!tokens || !tokens.access || !tokens.refresh) {
            throw new Error("Invalid response from server");
        }

        // Store tokens
        localStorage.setItem("access_token", tokens.access);
        localStorage.setItem("refresh_token", tokens.refresh);
        localStorage.setItem("tokens", JSON.stringify(tokens));

        // Set authorization header for future requests
        api.defaults.headers.common['Authorization'] = `Bearer ${tokens.access}`;

        return {
            message: message || "Login successful!",
            tokens
        };
    } catch (error) {
        if (error.response) {
            throw error.response.data;
        }
        throw new Error(error.message || "Login failed");
    }
};

// Register a new user
export const registerUser = async (userData) => {
    try {
        const response = await api.post("/register/", userData);
        return response.data;
    } catch (error) {
        throw error.response ? error.response.data : error;
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
        if (error.response?.status === 401) {
            throw new Error("Session expired. Please log in again.");
        }
        throw new Error(error.response?.data || "Failed to analyze game. Please try again.");
    }
};

// Analyze a batch of games
export const analyzeBatchGames = async (numGames) => {
  try {
    const response = await api.post("/games/batch-analyze/", { 
      num_games: parseInt(numGames, 10),
      include_unanalyzed: true // Add this to analyze all games, not just unanalyzed ones
    });
    
    // Check for progress in the response
    if (response.data && response.data.progress) {
      // Emit progress event
      const event = new CustomEvent('analysisProgress', { 
        detail: { 
          current: response.data.progress.current,
          total: response.data.progress.total
        }
      });
      window.dispatchEvent(event);
    }
    
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

// Logout user
export const logoutUser = async () => {
    try {
        const refreshToken = localStorage.getItem("refresh_token");
        if (refreshToken) {
            await api.post("/logout/", { refresh_token: refreshToken });
        }
    } catch (error) {
        console.error("Logout error:", error);
    } finally {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("tokens");
        delete api.defaults.headers.common['Authorization'];
    }
};

export const requestPasswordReset = async (email) => {
    try {
        const response = await api.post("/auth/password-reset/", { email });
        return response.data;
    } catch (error) {
        throw new Error(error.response?.data?.error || "Failed to request password reset");
    }
};

export const resetPassword = async (uid, token, newPassword) => {
    try {
        const response = await api.post("/auth/password-reset/confirm/", {
            uid,
            token,
            new_password: newPassword
        });
        return response.data;
    } catch (error) {
        throw new Error(error.response?.data?.error || "Failed to reset password");
    }
};

const getToken = () => {
  const tokens = localStorage.getItem('tokens');
  if (!tokens) {
    throw new Error('No authentication token found');
  }
  return JSON.parse(tokens).access;
};

export const getUserProfile = async () => {
    try {
        const response = await api.get("/profile/");
        return response.data;
    } catch (error) {
        const errorMessage = error.response?.data?.error || 'Failed to fetch profile';
        const customError = new Error(errorMessage);
        customError.status = error.response?.status;
        throw customError;
    }
};

export const updateUserProfile = async (profileData) => {
    try {
        const response = await api.patch("/profile/", profileData);
        return response.data;
    } catch (error) {
        const errorMessage = error.response?.data?.error || 'Failed to update profile';
        const customError = new Error(errorMessage);
        customError.status = error.response?.status;
        throw customError;
    }
};

export { api as default };
