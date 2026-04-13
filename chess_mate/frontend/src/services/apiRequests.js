import api from './api';
import { toast } from 'react-hot-toast';
import { refreshTokens, getAccessToken, getRefreshToken, setTokens, clearTokens } from './authService';
import {
    analyzeSpecificGame as analyzeSpecificGameService,
    checkAnalysisStatus as checkAnalysisStatusService,
    fetchGameAnalysis as fetchGameAnalysisService,
    checkMultipleAnalysisStatuses as checkMultipleAnalysisStatusesService,
} from './gameAnalysisService';
import { API_URL } from '../config';

// Define API base URL
const API_BASE_URL = API_URL;

// Authentication functions
export const loginUser = async (email, password) => {
    try {
        console.log('Logging in user with email:', email);
        const response = await api.post("/api/v1/auth/login/", { email, password });
        console.log('Login response:', response.data);
        
        // Check the response structure
        if (!response.data) {
            throw new Error("Invalid response from server");
        }
        
        // Handle response in standard format: { status: 'success', data: {...} }
        let userData = null;
        let accessToken = null;
        let refreshToken = null;
        
        // Extract tokens and user data from different possible response formats
        if (response.data.status === 'success' && response.data.data) {
            // Standard API format with status and data fields
            accessToken = response.data.data.access || null;
            refreshToken = response.data.data.refresh || null;
            userData = response.data.data.user || null;
        } else {
            // Direct format with access, refresh, and user fields
            accessToken = response.data.access || null;
            refreshToken = response.data.refresh || null;
            userData = response.data.user || null;
        }
        
        // Validate that we have the necessary data
        if (!accessToken || !refreshToken) {
            console.error('Missing tokens in response:', response.data);
            throw new Error("Authentication tokens not found in server response");
        }
        
        // Persist tokens through shared helper to keep all key formats in sync.
        setTokens(accessToken, refreshToken);
        
        // Set default Authorization header
        api.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;
        
        console.log('Login successful, user data:', userData);

        return {
            success: true,
            user: userData || {}
        };
    } catch (error) {
        console.error('Login error details:', error);
        // Provide specific error messages based on status codes
        if (error.response?.status === 401) {
            throw new Error("Invalid credentials");
        } else if (error.response?.status === 403) {
            throw new Error("Account is locked or requires verification");
        } else if (error.response?.status === 429) {
            throw new Error("Too many login attempts. Please try again later.");
        }
        
        // Handle error messages from backend
        if (error.response?.data?.message) {
            throw new Error(error.response.data.message);
        } else if (error.response?.data?.error) {
            throw new Error(error.response.data.error);
        } else if (error.message) {
            throw new Error(error.message);
        }
        
        throw new Error("Login failed, please try again");
    }
};

export const logoutUser = async () => {
    try {
        const tokens = JSON.parse(localStorage.getItem('tokens') || '{}');
        
        if (tokens.refresh) {
            await api.post("/api/v1/auth/logout/", { refresh: tokens.refresh });
        }
        
        // Clear tokens regardless of server response.
        clearTokens();
        delete api.defaults.headers.common['Authorization'];

        return true;
    } catch (error) {
        console.error('Logout error:', error);
        
        // Even if the server request fails, clear local auth state.
        clearTokens();
        delete api.defaults.headers.common['Authorization'];
        return false;
    }
};

export const registerUser = async (userData) => {
    try {
        const response = await api.post("/api/v1/auth/register/", userData);
        console.log('Registration response:', response.data);
        
        // Check for standard success structure
        if (response.data && response.data.status === 'success') {
            // Return the data object that contains the tokens
            return response.data.data;
        }
        
        // If it's not in standard format, return the full response data
        return response.data;
    } catch (error) {
        console.error('Registration error details:', error.response?.data || error);
        if (error.response?.status === 400) {
            throw error.response.data;
        }
        throw new Error(error.response?.data?.message || "Registration failed");
    }
};

// Game management functions
export const fetchUserGames = async () => {
    try {
        console.log('Fetching user games...');
        const response = await api.get("/api/v1/games/");
        console.log('Games response:', response.data);

        let games = [];
        
        // Process different response formats to extract games
        if (response.data?.results && Array.isArray(response.data.results)) {
            games = response.data.results;
        } else if (response.data?.data && Array.isArray(response.data.data)) {
            games = response.data.data;
        } else if (response.data?.games && Array.isArray(response.data.games)) {
            games = response.data.games;
        } else if (Array.isArray(response.data)) {
            games = response.data;
        } else {
            console.error('Invalid response format:', response.data);
            return { results: [] };
        }
        
        // Normalize and validate each game object
        const normalizedGames = games.map(game => {
            const normalizedAnalysisStatus = game.analysis_status || game.status || (game.analysis ? 'analyzed' : 'pending');
            return {
                id: game.id,
                opponent: game.opponent || 'Unknown',
                result: game.result || 'unknown',
                date_played: game.date_played || game.played_at || new Date().toISOString(),
                opening_name: game.opening_name || 'Unknown Opening',
                status: game.status || normalizedAnalysisStatus,
                analysis_status: normalizedAnalysisStatus,
                white: game.white || game.opponent || 'Unknown',
                black: game.black || game.user_username || 'Unknown',
                pgn: game.pgn || '',
                platform: game.platform || 'Unknown',
                // Add any other required fields with defaults
            };
        });
        
        console.log('Normalized games:', normalizedGames);
        
        // Return in the format expected by components
        return {
            results: normalizedGames,
            count: normalizedGames.length,
            next: response.data?.next || null,
            previous: response.data?.previous || null
        };
    } catch (error) {
        console.error('Error fetching games:', error);
        if (error.response?.status === 401) {
            throw new Error("Please log in to view your games");
        }
        throw new Error(error.response?.data?.message || "Failed to fetch games");
    }
};

export const fetchDashboardData = async () => {
    try {
        const response = await api.get("/api/v1/dashboard/");
        return response.data;
    } catch (error) {
        if (error.response?.status === 401) {
            throw new Error("Please log in to view your dashboard");
        }
        throw error.response?.data || new Error("Failed to fetch dashboard data");
    }
};

export const fetchExternalGames = async (platform, username, gameType, numGames = 10) => {
    try {
        const effectiveGameType = gameType === "all" ? "rapid" : gameType;
        console.log('Fetching external games...', { platform, username, gameType: effectiveGameType, numGames });

        // Get user ID and token from localStorage
        let userId = null;
        let authHeader = null;
        
        try {
            const tokensString = localStorage.getItem('tokens');
            if (tokensString) {
                const tokens = JSON.parse(tokensString);
                if (tokens && tokens.access) {
                    // Set the authorization header
                    authHeader = `Bearer ${tokens.access}`;
                    
                    // Get user ID from token
                    const decoded = JSON.parse(atob(tokens.access.split('.')[1]));
                    userId = decoded.user_id;
                    console.log('Using user ID from token:', userId);
                } else {
                    console.warn('Access token not found in tokens object');
                }
            } else {
                console.warn('No tokens found in localStorage');
            }
        } catch (e) {
            console.error('Error extracting token information:', e);
        }
        
        // Ensure we have authentication
        if (!authHeader) {
            throw new Error('Authentication required. Please log in again.');
        }

        // Make the API request with explicit Authorization header
        const response = await api.post("/api/v1/games/fetch/", 
            {
            platform: platform.toLowerCase(),
            username: username.trim(),
            game_type: effectiveGameType,
                num_games: numGames,
                user_id: userId // Include user ID from token
            },
            {
                headers: {
                    'Authorization': authHeader
                }
            }
        );

        console.log('External games response:', response.data);

        if (response.data?.error) {
            throw new Error(response.data.error);
        }

        // Handle different response formats
        if (response.data?.data && Array.isArray(response.data.data)) {
            return response.data.data;
        } else if (response.data?.games && Array.isArray(response.data.games)) {
            return response.data.games;
        } else if (Array.isArray(response.data)) {
            return response.data;
        }

        // Return the original response if format is not recognized
        return response.data;
    } catch (error) {
        console.error('Fetch games error:', error);
        // Handle unauthorized errors
        if (error.response?.status === 401) {
            throw new Error("Authentication required. Please log in to fetch games.");
        }
        // Handle payment required errors
        if (error.response?.status === 402) {
            throw new Error("Insufficient credits. Please purchase more credits to fetch games.");
        }
        // Handle not found errors specifically to help debugging
        if (error.response?.status === 404) {
            throw new Error("The server returned a 404 error. The fetch games endpoint may not be configured properly.");
        }
        // Get the most descriptive error message possible
        const errorMessage = 
            error.response?.data?.message || 
            error.response?.data?.error || 
            error.message || 
            "Failed to fetch external games";
        
        throw new Error(errorMessage);
    }
};

// Game analysis functions
export const analyzeSpecificGame = async (gameId) => {
    return analyzeSpecificGameService(gameId);
};

// Constants for analysis status
const ANALYSIS_STATUS = {
    PENDING: 'PENDING',
    IN_PROGRESS: 'IN_PROGRESS',
    PROCESSING: 'PROCESSING',
    COMPLETED: 'COMPLETED',
    SUCCESS: 'SUCCESS',
    FAILED: 'FAILED',
    FAILURE: 'FAILURE',
    ERROR: 'ERROR',
    TIMEOUT: 'TIMEOUT'
};

const isValidStatus = (status) => {
    return Object.values(ANALYSIS_STATUS).includes(status?.toUpperCase());
};

export const checkAnalysisStatus = async (gameId) => {
    return checkAnalysisStatusService(gameId);
};

export const fetchGameAnalysis = async (gameId) => {
    return fetchGameAnalysisService(gameId);
};

export const analyzeBatchGames = async (
    numGames,
    timeControl = 'all',
    includeAnalyzed = false,
    selectedGameIds = []
) => {
    try {
        const normalizedIds = Array.isArray(selectedGameIds)
            ? selectedGameIds.filter((id) => Number.isInteger(id))
            : [];

        const payload = {
            num_games: parseInt(numGames, 10),
            time_control: timeControl,
            include_analyzed: includeAnalyzed,
            depth: 20,
            use_ai: true
        };

        if (normalizedIds.length > 0) {
            payload.game_ids = normalizedIds;
            payload.num_games = normalizedIds.length;
        }

        const response = await api.post('/api/v1/games/batch-analyze/', {
            ...payload
        });

        if (!response.data) {
            throw new Error('Invalid response from server');
        }

        const { task_id, total_games, status, estimated_time, message } = response.data;

        if (!task_id) {
            throw new Error('No task ID received from server');
        }

        return {
            task_id,
            total_games,
            status,
            estimated_time,
            message
        };
    } catch (error) {
        console.error('Error starting batch analysis:', error);
        throw error.response?.data || new Error("Failed to start batch analysis");
    }
};

export const checkBatchAnalysisStatus = async (taskId) => {
    try {
        if (!taskId) {
            throw new Error('No task ID provided');
        }

        const response = await api.get(`/api/v1/games/batch-status/${taskId}/`);

        if (!response.data) {
            throw new Error('Invalid response from server');
        }

        const { state, meta = {}, completed_games = [], failed_games = [], aggregate_metrics = {}, report_id = null } = response.data;

        // Common response structure
        const result = {
            state: state || 'FAILURE',
            meta: {
                current: meta?.current || 0,
                total: meta?.total || 0,
                message: meta?.message || 'Analyzing games...',
                progress: meta?.progress || 0,
                error: meta?.error
            },
            completed_games,
            failed_games,
            aggregate_metrics,
            report_id
        };

        // Handle error state
        if (state === 'FAILURE') {
            result.meta.error = meta?.error || 'Analysis failed';
            result.meta.message = meta?.message || 'Analysis failed';
            return result;
        }

        // Handle progress state
        if (state === 'PROGRESS' || state === 'PENDING' || state === 'STARTED') {
            result.meta.message = meta?.message || 'Analysis in progress...';
            return result;
        }

        // Handle success state
        if (state === 'SUCCESS') {
            result.meta.message = 'Analysis complete';
            result.meta.progress = 100;
            return result;
        }

        // Handle unknown state
        result.state = 'FAILURE';
        result.meta.error = `Unknown state: ${state}`;
        result.meta.message = 'Analysis failed due to unknown state';
        return result;

    } catch (error) {
        console.error('Error checking batch analysis status:', error);
        return {
            state: 'FAILURE',
            meta: {
                error: error.message || 'Failed to check batch analysis status',
                current: 0,
                total: 0,
                progress: 0,
                message: error.message || 'Failed to check batch analysis status'
            },
            completed_games: [],
            failed_games: [],
            aggregate_metrics: null
        };
    }
};

export const fetchBatchReportHistory = async (limit = 20) => {
    try {
        const response = await api.get('/api/v1/games/batch-reports/', {
            params: { limit }
        });

        if (!response.data || !Array.isArray(response.data.results)) {
            return [];
        }

        return response.data.results;
    } catch (error) {
        console.error('Error fetching batch report history:', error);
        throw error.response?.data || new Error('Failed to fetch batch report history');
    }
};

export const fetchBatchReportById = async (reportId) => {
    try {
        const response = await api.get(`/api/v1/games/batch-reports/${reportId}/`);

        if (!response.data || !response.data.report) {
            throw new Error('Invalid report response');
        }

        return response.data.report;
    } catch (error) {
        console.error('Error fetching batch report:', error);
        throw error.response?.data || new Error('Failed to fetch batch report');
    }
};

// User profile functions
export const getUserProfile = async () => {
    try {
        const response = await api.get('/api/v1/profile/');
        return response.data;
    } catch (error) {
        console.error('Error fetching profile data:', error);
        throw error.response?.data || new Error("Failed to fetch profile data");
    }
};

export const updateUserProfile = async (profileData) => {
    try {
        const response = await api.patch("/api/v1/profile/", profileData);
        return response.data;
    } catch (error) {
        if (error.response?.status === 400) {
            throw error.response.data;
        }
        throw error.response?.data || new Error("Failed to update profile");
    }
};

// Password reset functions
export const requestPasswordReset = async (email) => {
    try {
        const response = await api.post("/api/v1/auth/reset-password/", { email });
        return response.data;
    } catch (error) {
        console.error('Password reset request error:', error);
        if (error.response?.data?.message) {
            throw new Error(error.response.data.message);
        }
        throw new Error("Failed to send password reset link. Please try again later.");
    }
};

export const resetPassword = async (token, newPassword) => {
    try {
        const response = await api.post("/api/v1/auth/reset-password/confirm/", {
            token,
            new_password: newPassword
        });
        return response.data;
    } catch (error) {
        console.error('Password reset error:', error);
        if (error.response?.data?.message) {
            throw new Error(error.response.data.message);
        }
        throw new Error("Failed to reset password. The link may have expired.");
    }
};

// Credit system functions
export const getCredits = async () => {
    try {
        const response = await api.get('/api/v1/credits/');
        return response.data.credits;
    } catch (error) {
        console.error('Error fetching credits:', error);
        throw error.response?.data || new Error("Failed to fetch credits");
    }
};

export const purchaseCredits = async (packageId) => {
    try {
        const response = await api.post("/api/v1/purchase-credits/", { package_id: packageId });
        return response.data;
    } catch (error) {
        if (error.response?.status === 400) {
            throw new Error("Invalid package selection");
        }
        throw error.response?.data || new Error("Failed to purchase credits");
    }
};

export const confirmPurchase = async (paymentId) => {
    try {
        const response = await api.post("/api/v1/confirm-purchase/", { payment_id: paymentId });
        return response.data;
    } catch (error) {
        if (error.response?.status === 400) {
            throw new Error("Invalid payment confirmation");
        }
        throw error.response?.data || new Error("Failed to confirm purchase");
    }
};

export const fetchProfileData = async () => {
    try {
        const response = await api.get('/api/v1/profile/');
        return response.data;
    } catch (error) {
        console.error('Error fetching profile data:', error);
        throw error;
    }
};

export const fetchGameFeedback = async (gameId) => {
  try {
    const response = await api.get(`/api/v1/game/${gameId}/analysis/`);

    if (!response.data) {
      throw new Error('Invalid analysis data structure');
    }

    // Extract analysis data, handling both nested and flat structures
    const analysisData = response.data.analysis || response.data;

    // Return the properly structured response
    return {
      status: 'COMPLETED',
      game_id: gameId,
      analysis: {
        overall: {
          accuracy: analysisData.overall?.accuracy || 0,
          blunders: analysisData.overall?.blunders || 0,
          mistakes: analysisData.overall?.mistakes || 0,
          inaccuracies: analysisData.overall?.inaccuracies || 0,
          position_quality: analysisData.overall?.position_quality || 0
        },
        phases: analysisData.phases || {
          opening: {},
          middlegame: {},
          endgame: {}
        },
        tactics: analysisData.tactics || {
          opportunities: 0,
          successful: 0,
          missed: 0,
          success_rate: 0
        },
        time_management: analysisData.time_management || {
          average_time: 0,
          time_variance: 0,
          time_pressure_moves: 0,
          time_pressure_percentage: 0
        },
        positional: analysisData.positional || {},
        advantage: analysisData.advantage || {
          winning_positions: 0,
          conversion_rate: 0,
          average_advantage: 0
        },
        resourcefulness: analysisData.resourcefulness || {
          recovery_rate: 0,
          defensive_score: 0,
          critical_defense: 0,
          best_move_finding: 0
        },
        strengths: analysisData.strengths || [],
        weaknesses: analysisData.weaknesses || [],
        critical_moments: analysisData.critical_moments || [],
        improvement_areas: analysisData.improvement_areas || []
      },
      analysis_complete: true
    };
  } catch (error) {
    console.error('Error fetching game feedback:', error);
    throw error;
  }
};

// Handle authentication errors without redirecting
const handleAuthError = (error) => {
    console.error('Auth error in API request:', error);
    
    // Return a standardized error response
    return {
        status: 'error',
        error: 'auth_error',
        message: 'Authentication required. Please login to continue.',
        code: error.response?.status || 401
    };
};

// General API error handler with improved consistency
const handleApiError = (error, customMessage = null) => {
    // Network errors
    if (error.message === 'Network Error' || !error.response) {
        return {
            status: 'error',
            error: 'network_error',
            message: 'Network connection issue. Please check your internet connection.',
            code: 0
        };
    }
    
    // Authentication errors
    if (error.response && (error.response.status === 401 || error.response.status === 403)) {
        return handleAuthError(error);
    }
    
    // Server errors
    if (error.response && error.response.status >= 500) {
        return {
            status: 'error',
            error: 'server_error',
            message: customMessage || 'Server error. Please try again later.',
            code: error.response.status
        };
    }
    
    // Other HTTP errors
    if (error.response) {
        const message = error.response.data?.message || 
                      error.response.data?.detail || 
                      error.response.data?.error ||
                      customMessage ||
                      'Request failed. Please try again.';
        
        return {
            status: 'error',
            error: 'request_error',
            message: message,
            code: error.response.status,
            details: error.response.data
        };
    }
    
    // Generic error
    return {
        status: 'error',
        error: 'unknown_error',
        message: customMessage || error.message || 'An unexpected error occurred.',
        code: 0
    };
};

// Find the checkMultipleAnalysisStatuses function and replace it with this

export async function checkMultipleAnalysisStatuses(gameIds) {
    return checkMultipleAnalysisStatusesService(gameIds);
}
