import api from './api';
import axios from 'axios';

// Authentication functions
export const loginUser = async (credentials) => {
    try {
        // Clear any existing tokens
        localStorage.removeItem('tokens');
        
        // Attempt login
        const response = await api.post('/api/login/', credentials);
        
        // If login successful, store tokens
        if (response.data.tokens) {
            localStorage.setItem('tokens', JSON.stringify(response.data.tokens));
            
            // Set the authorization header for subsequent requests
            api.defaults.headers.common['Authorization'] = `Bearer ${response.data.tokens.access}`;
            
            // Fetch user profile after successful login
            try {
                const profileData = await getUserProfile();
                return {
                    ...response.data,
                    profile: profileData
                };
            } catch (profileError) {
                console.error('Error fetching profile:', profileError);
                // Return login data even if profile fetch fails
                return response.data;
            }
        }
        
        return response.data;
    } catch (error) {
        console.error('Login error:', error);
        if (error.response?.status === 400) {
            throw new Error("Invalid email or password");
        }
        throw error.response?.data || new Error("Login failed");
    }
};

export const logoutUser = async () => {
    try {
        const tokens = localStorage.getItem('tokens');
        if (tokens) {
            const parsedTokens = JSON.parse(tokens);
            // First remove tokens from localStorage to prevent any race conditions
            localStorage.removeItem('tokens');
            delete api.defaults.headers.common['Authorization'];
            
            // Then blacklist the token on the server
            await api.post('/api/logout/', { refresh_token: parsedTokens.refresh });
        }
        return true;
    } catch (error) {
        console.error('Logout error:', error);
        // Even if the server request fails, we want to clear local storage
        localStorage.removeItem('tokens');
        delete api.defaults.headers.common['Authorization'];
        return false;
    }
};

export const registerUser = async (userData) => {
    try {
        const response = await api.post("/api/register/", userData);
        return response.data;
    } catch (error) {
        if (error.response?.status === 400) {
            throw error.response.data;
        }
        throw new Error("Registration failed");
    }
};

// Game management functions
export const fetchUserGames = async () => {
    try {
        console.log('Fetching user games...');
        const response = await api.get("/api/games/");
        console.log('Games response:', response.data);
        
        if (!Array.isArray(response.data)) {
            console.error('Invalid response format:', response.data);
            return [];
        }
        
        return response.data;
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
        const response = await api.get("/api/dashboard/");
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
        
        const response = await api.post("/api/games/fetch/", {
            platform: platform.toLowerCase(),
            username: username.trim(),
            game_type: effectiveGameType,
            num_games: numGames
        });
        
        console.log('External games response:', response.data);
        
        if (response.data.error) {
            throw new Error(response.data.error);
        }
        
        return response.data;
    } catch (error) {
        console.error('Fetch games error:', error);
        if (error.response?.status === 401) {
            throw new Error("Please log in to fetch games");
        }
        if (error.response?.status === 402) {
            throw new Error("Insufficient credits. Please purchase more credits to fetch games.");
        }
        throw new Error(error.response?.data?.error || error.message || "Failed to fetch external games");
    }
};

// Game analysis functions
export const analyzeSpecificGame = async (gameId) => {
    console.log('=== Starting Game Analysis ===');
    console.log('Parameters:', { gameId });
    
    try {
        console.log('Making analysis request for game:', gameId);
        const requestData = {
            depth: 20,
            use_ai: true
        };
        console.log('Request data:', requestData);
        
        const response = await api.post(`/api/game/${gameId}/analyze/`, requestData);
        console.log('Raw analysis response:', response);
        console.log('Analysis response data:', response.data);

        // Validate response structure
        if (!response.data) {
            console.error('Invalid response - missing data:', response);
            throw new Error("Invalid response from server");
        }

        // Handle Redis connection limit error
        if (response.data.error === 'max number of clients reached' || 
            response.data.error?.includes('max number of clients reached')) {
            console.warn('Redis connection limit reached:', response.data);
            throw new Error('Redis connection limit reached. Please try again in a few moments.');
        }

        // If the game is already analyzed, fetch and return the analysis immediately
        if (response.data.status === 'completed' && response.data.message?.includes('already analyzed')) {
            console.log('Game is already analyzed, fetching analysis data');
            try {
                const analysisResponse = await fetchGameAnalysis(gameId);
                return {
                    analysis: analysisResponse,
                    status: 'completed'
                };
            } catch (error) {
                console.error('Error fetching analysis for already analyzed game:', error);
                throw new Error('Game is marked as analyzed but failed to fetch analysis data');
            }
        }

        // If we have a task ID, return it
        if (response.data.task_id) {
            console.log('Analysis task created:', {
                taskId: response.data.task_id,
                status: response.data.status || 'pending'
            });
            return {
                task_id: response.data.task_id,
                status: response.data.status || 'pending'
            };
        }

        // If we have analysis data, validate and return it
        if (response.data.analysis) {
            console.log('Immediate analysis result received');
            return {
                analysis: response.data.analysis,
                status: 'completed'
            };
        }

        console.error('Invalid response format:', response.data);
        throw new Error("Invalid response format: missing analysis or task_id");
    } catch (error) {
        console.error('Analysis error:', {
            error,
            message: error.message,
            response: error.response?.data,
            status: error.response?.status
        });

        if (error.response?.status === 404) {
            throw new Error("Game not found");
        }
        if (error.response?.status === 401) {
            throw new Error("Please log in to analyze games");
        }
        if (error.response?.status === 402) {
            throw new Error("Insufficient credits. Please purchase more credits to analyze games.");
        }
        throw error.response?.data?.error || error.message || "Failed to analyze game";
    }
};

// Constants for analysis status
const ANALYSIS_STATUS = {
    PENDING: 'pending',
    IN_PROGRESS: 'in_progress',
    PROCESSING: 'processing',
    COMPLETED: 'completed',
    FAILED: 'failed'
};

const VALID_STATUSES = Object.values(ANALYSIS_STATUS);

export const checkAnalysisStatus = async (taskId) => {
    try {
        const response = await api.get(`/api/analysis/status/${taskId}/`);
        
        // Normalize status to uppercase for consistency
        const normalizedStatus = response.data.status?.toUpperCase();
        
        // Return a consistent response format
        const result = {
            status: normalizedStatus,
            message: response.data.message,
            game_id: response.data.game_id,
            progress: response.data.progress,
            error: response.data.error
        };
        
        // If status is completed or success, fetch the analysis data
        if (normalizedStatus === 'COMPLETED' || normalizedStatus === 'SUCCESS') {
            if (!response.data.game_id) {
                throw new Error('Game ID missing from completed analysis response');
            }
            
            try {
                console.log('Fetching analysis for completed game:', response.data.game_id);
                const analysisResponse = await fetchGameAnalysis(response.data.game_id);
                return {
                    ...result,
                    status: 'COMPLETED',
                    analysis: analysisResponse
                };
            } catch (analysisError) {
                console.error('Error fetching completed analysis:', analysisError);
                throw new Error('Failed to fetch analysis results');
            }
        }
        
        // For other statuses, just return the result
        return result;

    } catch (error) {
        console.error('Error checking analysis status:', error);
        throw error.response?.data?.error || error.message || 'Failed to check analysis status';
    }
};

export const fetchGameAnalysis = async (gameId) => {
    try {
        console.log('Fetching analysis for game:', gameId);
        const response = await api.get(`/api/game/${gameId}/analysis/`);
        console.log('Analysis response:', response.data);

        if (!response.data) {
            throw new Error("Invalid response from server");
        }

        // Extract analysis data from response
        const analysisData = response.data.analysis;
        if (!analysisData) {
            console.error('No analysis data in response:', response.data);
            throw new Error('No analysis data found in response');
        }

        // If analysis data contains analysis_results, return the full analysis object
        if (analysisData.analysis_results) {
            return {
                moves: analysisData.analysis_results,
                feedback: analysisData.feedback || {},
                depth: analysisData.depth,
                timestamp: analysisData.timestamp,
                source: analysisData.source,
                summary: {
                    accuracy: analysisData.feedback?.accuracy || 0,
                    mistakes: analysisData.feedback?.summary?.mistakes || 0,
                    blunders: analysisData.feedback?.summary?.blunders || 0,
                    inaccuracies: analysisData.feedback?.summary?.inaccuracies || 0,
                    avgTimePerMove: analysisData.feedback?.time_management?.avg_time_per_move || 0,
                    criticalMistakes: analysisData.feedback?.tactical_opportunities?.length || 0
                }
            };
        }

        // If analysis data is an array (direct analysis data), wrap it
        if (Array.isArray(analysisData)) {
            return {
                moves: analysisData,
                feedback: {},
                summary: {
                    accuracy: 0,
                    mistakes: 0,
                    blunders: 0,
                    inaccuracies: 0,
                    avgTimePerMove: 0,
                    criticalMistakes: 0
                }
            };
        }

        // If we get here, we don't recognize the format
        console.error('Unrecognized analysis format:', analysisData);
        throw new Error("Invalid analysis data format");
    } catch (error) {
        console.error('Error fetching analysis:', error);
        if (error.response?.status === 404) {
            throw new Error("Analysis not found - the game may still be processing");
        }
        if (error.response?.status === 403) {
            throw new Error("Access denied. Please try again.");
        }
        throw error.response?.data?.error || error.message || "Failed to fetch analysis";
    }
};

export const analyzeBatchGames = async (numGames, timeControl = 'all', includeAnalyzed = false) => {
    try {
        const response = await api.post('/api/games/batch-analyze/', {
            num_games: parseInt(numGames, 10),
            time_control: timeControl,
            include_analyzed: includeAnalyzed,
            depth: 20,
            use_ai: true
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

        const response = await api.get(`/api/games/batch-analyze/status/${taskId}/`);
        
        if (!response.data) {
            throw new Error('Invalid response from server');
        }

        const { state, meta = {}, completed_games = [], failed_games = [], aggregate_metrics = {} } = response.data;

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
            aggregate_metrics
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

// User profile functions
export const getUserProfile = async () => {
    try {
        const response = await api.get('/api/profile/');
        return response.data;
    } catch (error) {
        console.error('Error fetching profile data:', error);
        throw error.response?.data || new Error("Failed to fetch profile data");
    }
};

export const updateUserProfile = async (profileData) => {
    try {
        const response = await api.patch("/api/profile/", profileData);
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
        // No need for CSRF token for initial request
        const response = await api.post("/api/auth/password-reset/", { email });
        return response.data;
    } catch (error) {
        if (error.response?.status === 400) {
            throw new Error("Invalid email address");
        }
        throw error.response?.data?.error || new Error("Failed to request password reset");
    }
};

export const resetPassword = async (uid, token, newPassword) => {
    try {
        await api.get('/api/csrf/');
        // Make the password reset confirmation request
        const response = await api.post("/api/auth/password-reset/confirm/", {
            uid,
            token,
            new_password: newPassword
        });
        return response.data;
    } catch (error) {
        if (error.response?.status === 400) {
            throw new Error(error.response.data?.message || "Invalid password or token");
        }
        throw error.response?.data?.error || new Error("Failed to reset password");
    }
};

// Credit system functions
export const getCredits = async () => {
    try {
        const response = await api.get('/api/credits/');
        return response.data.credits;
    } catch (error) {
        console.error('Error fetching credits:', error);
        throw error.response?.data || new Error("Failed to fetch credits");
    }
};

export const purchaseCredits = async (packageId) => {
    try {
        const response = await api.post("/purchase-credits/", { package_id: packageId });
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
        const response = await api.post("/confirm-purchase/", { payment_id: paymentId });
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
        const response = await api.get('/api/profile/');
        return response.data;
    } catch (error) {
        console.error('Error fetching profile data:', error);
        throw error;
    }
};