import api from './api';

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
    try {
        const response = await api.post(`/api/game/${gameId}/analyze/`);
        
        // Check if analysis is already complete
        if (response.data.analysis_complete || response.data.status === 'COMPLETED') {
            return {
                status: 'COMPLETED',
                analysis: response.data.analysis || response.data,
                message: 'Analysis completed'
            };
        }

        // Check if task already exists and handle it consistently
        if (response.data.message?.toLowerCase().includes('already exists')) {
            return {
                status: 'PENDING',
                taskId: response.data.task_id,
                isExistingTask: true,
                message: response.data.message
            };
        }
        
        // Return consistent response format for new tasks
        return {
            status: response.data.status || 'PENDING',
            taskId: response.data.task_id,
            isExistingTask: false,
            message: response.data.message || 'Analysis started'
        };
    } catch (error) {
        console.error('Analysis error:', error);
        throw new Error(error.response?.data?.error || error.message || 'Failed to start analysis');
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
        console.log('Raw status response:', response.data);
        
        // Normalize status to uppercase and handle both response formats
        const status = (response.data.status || '').toUpperCase();
        console.log('Status normalized to:', status);
        
        // If analysis is complete, fetch and return the analysis data
        if (status === 'COMPLETED' || status === 'SUCCESS') {
            console.log('Analysis completed, fetching results');
            // Handle both response formats (info.game_id and direct game_id)
            const gameId = response.data.game_id || 
                          response.data.info?.game_id || 
                          response.data.info?.gameId;
            console.log('Game ID from response:', gameId);
            
            if (!gameId) {
                console.error('No game ID in completed response:', response.data);
                throw new Error('Game ID missing from completed analysis');
            }

            try {
                console.log('Fetching analysis data for game:', gameId);
                const analysisData = await fetchGameAnalysis(gameId);
                console.log('Fetched analysis data:', analysisData);
                
                if (!analysisData) {
                    throw new Error('No analysis data received');
                }
                
                return {
                    status: 'COMPLETED',
                    analysis: analysisData,
                    gameId,
                    progress: 100
                };
            } catch (analysisError) {
                console.error('Error fetching analysis data:', analysisError);
                throw new Error('Failed to fetch analysis results');
            }
        }
        
        // For in-progress status, return normalized response
        return {
            status,
            progress: response.data.progress || 0,
            message: response.data.message || 'Analysis in progress',
            isExistingTask: response.data.isExistingTask || false,
            gameId: response.data.game_id || response.data.info?.game_id
        };
    } catch (error) {
        console.error('Error checking analysis status:', error);
        throw new Error(error.response?.data?.message || 'Failed to check analysis status');
    }
};

export const fetchGameAnalysis = async (gameId) => {
    try {
        console.log('Fetching analysis for game:', gameId);
        const response = await api.get(`/api/game/${gameId}/analysis/`);
        console.log('Analysis response:', response.data);

        // Check if response has analysis data
        if (!response.data || !response.data.analysis) {
            throw new Error('No analysis data found');
        }

        // The analysis data is valid if it contains the required fields
        const analysisData = response.data.analysis;
        if (!analysisData.moves || !analysisData.overall || !analysisData.phases) {
            console.error('Missing required analysis fields:', analysisData);
            throw new Error('Invalid analysis data structure');
        }

        return response.data;
    } catch (error) {
        console.error('Error fetching analysis:', error);
        throw new Error('Failed to fetch analysis results');
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