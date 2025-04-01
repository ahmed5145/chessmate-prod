import api from './api';
import { toast } from 'react-hot-toast';

// Authentication functions
export const loginUser = async (email, password) => {
    try {
        // Clear any existing tokens
        localStorage.removeItem('tokens');
        
        // Attempt login
        const response = await api.post('/api/login/', {
            email,
            password
        });

        // Handle successful login
        if (response.data?.tokens) {
            localStorage.setItem('tokens', JSON.stringify(response.data.tokens));
            api.defaults.headers.common['Authorization'] = `Bearer ${response.data.tokens.access}`;
            
            // Fetch user profile
            try {
                const profileResponse = await api.get('/api/profile/');
                return {
                    success: true,
                    data: {
                        ...response.data,
                        profile: profileResponse.data
                    }
                };
            } catch (profileError) {
                console.error('Error fetching profile:', profileError);
                // Still return success even if profile fetch fails
                return {
                    success: true,
                    data: response.data
                };
            }
        }
        
        throw new Error('Invalid response format');
    } catch (error) {
        console.error('Login error:', error);
        
        // Handle specific error cases
        const errorMessage = error.response?.data?.detail || 
                           error.response?.data?.error ||
                           error.message ||
                           'An error occurred during login';
                           
        toast.error(errorMessage);
        
        return {
            success: false,
            error: errorMessage
        };
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
    try {
        const response = await api.post(`/api/game/${gameId}/analyze/`);
        return response.data;
    } catch (error) {
        if (error.response?.status === 401) {
            throw new Error('Authentication failed');
        }
        throw new Error(error.response?.data?.message || 'Failed to start game analysis');
    }
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

export const checkAnalysisStatus = async (taskId) => {
    try {
        console.log('Checking status for task:', taskId);
        const response = await api.get(`/api/analysis/status/${taskId}/`);
        console.log('Status response:', response.data);
        
        if (!response.data) {
            throw new Error('Invalid response from server');
        }

        // If analysis is complete, fetch the analysis data
        if (response.data.status === 'completed' || response.data.status === 'SUCCESS') {
            if (!response.data.game_id) {
                throw new Error('Game ID missing from completed analysis');
            }

            try {
                const analysisData = await fetchGameAnalysis(response.data.game_id);
                return {
                    status: 'COMPLETED',
                    analysis: analysisData.analysis_results,
                    feedback: analysisData.feedback,
                    gameId: response.data.game_id,
                    progress: 100
                };
            } catch (analysisError) {
                console.error('Error fetching analysis data:', analysisError);
                // Return a more detailed error message
                const errorMessage = analysisError.message || 'Unknown error occurred';
                throw new Error(`Failed to fetch analysis results: ${errorMessage}`);
            }
        } else if (response.data.status === 'ERROR' || response.data.status === 'FAILURE' || response.data.status === 'FAILED') {
            // Handle error states explicitly
            throw new Error(response.data.message || 'Analysis failed');
        }
        
        // For in-progress status, return normalized response
        return {
            status: response.data.status?.toUpperCase() || 'PENDING',
            progress: response.data.progress || 0,
            message: response.data.message || 'Analysis in progress'
        };
    } catch (error) {
        console.error('Error checking analysis status:', error);
        throw error.response?.data?.message || error.message || 'Failed to check analysis status';
    }
};

export const fetchGameAnalysis = async (gameId) => {
    try {
        console.log('Fetching analysis for game:', gameId);
        const response = await api.get(`/api/game/${gameId}/analysis/`);
        console.log('Analysis response:', response.data);

        if (!response.data) {
            throw new Error('Invalid response from server');
        }

        // Extract analysis data from response
        const analysisData = response.data.analysis;
        if (!analysisData) {
            throw new Error('No analysis data found');
        }

        // Transform the response to match the expected structure
        const transformedData = {
            analysis_complete: true,
            analysis_results: {
                moves: analysisData.moves || [],
                overall: {
                    accuracy: analysisData.overall?.accuracy || 0,
                    mistakes: analysisData.overall?.mistakes || 0,
                    blunders: analysisData.overall?.blunders || 0,
                    inaccuracies: analysisData.overall?.inaccuracies || 0,
                    avg_centipawn_loss: analysisData.overall?.avg_centipawn_loss || 0,
                    moves_count: analysisData.overall?.moves_count || 0
                },
                phases: {
                    opening: {
                        accuracy: analysisData.phases?.opening?.accuracy || 0,
                        moves_count: analysisData.phases?.opening?.moves_count || 0,
                        time_management: analysisData.phases?.opening?.time_management || {}
                    },
                    middlegame: analysisData.phases?.middlegame || {},
                    endgame: analysisData.phases?.endgame || {}
                },
                tactics: {
                    missed: analysisData.tactics?.missed || 0,
                    successful: analysisData.tactics?.successful || 0,
                    success_rate: analysisData.tactics?.success_rate || 0,
                    opportunities: analysisData.tactics?.opportunities || 0,
                    tactical_score: analysisData.tactics?.tactical_score || 0,
                    pattern_recognition: analysisData.tactics?.pattern_recognition || 0
                },
                positional: {
                    king_safety: analysisData.positional?.king_safety || 0,
                    center_control: analysisData.positional?.center_control || 0,
                    pawn_structure: analysisData.positional?.pawn_structure || 0,
                    piece_activity: analysisData.positional?.piece_activity || 0,
                    space_advantage: analysisData.positional?.space_advantage || 0
                },
                time_management: {
                    average_time: analysisData.time_management?.average_time || 0,
                    time_variance: analysisData.time_management?.time_variance || 0,
                    time_consistency: analysisData.time_management?.time_consistency || 0,
                    time_pressure_moves: analysisData.time_management?.time_pressure_moves || 0,
                    time_pressure_percentage: analysisData.time_management?.time_pressure_percentage || 0
                },
                advantage: analysisData.advantage || {},
                resourcefulness: analysisData.resourcefulness || {}
            },
            feedback: response.data.feedback || {}
        };

        console.log('Transformed data:', transformedData);
        return transformedData;
    } catch (error) {
        console.error('Error fetching game analysis:', error);
        throw error.response?.data?.message || error.message || 'Failed to fetch game analysis';
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

export const fetchGameFeedback = async (gameId) => {
  try {
    const response = await api.get(`/api/game/${gameId}/analysis/`);
    
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