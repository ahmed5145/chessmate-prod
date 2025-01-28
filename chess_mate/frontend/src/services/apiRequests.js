import api from './api';

// Authentication functions
export const loginUser = async (credentials) => {
    try {
        localStorage.removeItem('tokens');
        
        const response = await api.post('/api/login/', credentials);
        const { tokens, message } = response.data;
        
        if (!tokens?.access || !tokens?.refresh) {
            throw new Error('Invalid response from server');
        }
        
        localStorage.setItem('tokens', JSON.stringify(tokens));
        api.defaults.headers.common['Authorization'] = `Bearer ${tokens.access}`;
        
        return { message: message || 'Login successful!', tokens };
    } catch (error) {
        if (error.response?.status === 401) {
            throw new Error("Invalid credentials");
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
        const response = await api.get("/api/games/");
        return response.data;
    } catch (error) {
        if (error.response?.status === 401) {
            throw new Error("Please log in to view your games");
        }
        throw error.response?.data || new Error("Failed to fetch games");
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

export const fetchExternalGames = async (platform, username, gameType) => {
    try {
        const effectiveGameType = gameType === "all" ? "rapid" : gameType;
        const response = await api.post("/api/games/fetch/", {
            platform,
            username,
            game_type: effectiveGameType
        });
        return response.data;
    } catch (error) {
        if (error.response?.status === 400) {
            throw new Error("Invalid request parameters");
        }
        throw error.response?.data || new Error("Failed to fetch external games");
    }
};

// Game analysis functions
export const analyzeSpecificGame = async (gameId) => {
    try {
        const response = await api.post(`/api/game/${gameId}/analyze/`, {
            depth: 20,
            use_ai: true
        });

        // Validate response structure
        if (!response.data) {
            throw new Error("Invalid response from server");
        }

        // If we have analysis data, validate its structure
        if (response.data.analysis) {
            if (!Array.isArray(response.data.analysis)) {
                throw new Error("Invalid analysis data format");
            }
            return response.data;
        }

        // If we have a task ID, validate it
        if (response.data.task_id) {
            if (typeof response.data.task_id !== 'string') {
                throw new Error("Invalid task ID format");
            }
            return response.data;
        }

        throw new Error("Invalid response format: missing analysis or task_id");
    } catch (error) {
        if (error.response?.status === 404) {
            throw new Error("Game not found");
        }
        if (error.response?.status === 401) {
            throw new Error("Please log in to analyze games");
        }
        if (error.response?.status === 403) {
            throw new Error("Access denied. Please try again.");
        }
        throw error.response?.data || error;
    }
};

export const checkAnalysisStatus = async (taskId) => {
    try {
        const response = await api.get(`/api/game/analysis/status/${taskId}/`);

        // Validate response structure
        if (!response.data) {
            throw new Error("Invalid response from server");
        }

        // Validate status field
        if (!response.data.status || !['pending', 'processing', 'completed', 'failed'].includes(response.data.status)) {
            throw new Error("Invalid analysis status");
        }

        // If completed, validate result structure
        if (response.data.status === 'completed' && response.data.result) {
            if (!response.data.result.results || !response.data.result.results.moves) {
                throw new Error("Invalid analysis result format");
            }
        }

        return response.data;
    } catch (error) {
        if (error.response?.status === 404) {
            throw new Error("Analysis not found");
        }
        if (error.response?.status === 403) {
            throw new Error("Access denied. Please try again.");
        }
        throw error.response?.data || error;
    }
};

export const fetchGameAnalysis = async (gameId) => {
    try {
        const response = await api.get(`/api/game/${gameId}/analysis/`);

        // Validate response structure
        if (!response.data) {
            throw new Error("Invalid response from server");
        }

        // Validate analysis data structure
        if (!response.data.analysis || !Array.isArray(response.data.analysis)) {
            throw new Error("Invalid analysis data format");
        }

        return response.data;
    } catch (error) {
        if (error.response?.status === 404) {
            throw new Error("Analysis not found");
        }
        if (error.response?.status === 403) {
            throw new Error("Access denied. Please try again.");
        }
        throw error.response?.data || error;
    }
};

export const analyzeBatchGames = async (numGames) => {
    try {
        const response = await api.post("/api/games/batch-analyze/", {
            num_games: parseInt(numGames, 10),
            include_unanalyzed: true
        });
        return response.data;
    } catch (error) {
        if (error.response?.status === 400) {
            throw new Error("Invalid request parameters");
        }
        if (error.response?.status === 403) {
            // If CSRF error, retry once
            if (error.response.data.includes('CSRF')) {
                return analyzeBatchGames(numGames);
            }
            throw new Error("Access denied. Please try again.");
        }
        throw error.response?.data || new Error("Failed to start batch analysis");
    }
};

export const checkBatchAnalysisStatus = async (taskId) => {
    try {
        const response = await api.get(`/api/games/batch-analyze/status/${taskId}/`);
        return response.data;
    } catch (error) {
        if (error.response?.status === 404) {
            throw new Error("Analysis status not found");
        }
        if (error.response?.status === 403) {
            // If CSRF error, retry once
            if (error.response.data.includes('CSRF')) {
                return checkBatchAnalysisStatus(taskId);
            }
            throw new Error("Access denied. Please try again.");
        }
        throw error.response?.data || new Error("Failed to check batch analysis status");
    }
};

// User profile functions
export const getUserProfile = async () => {
    try {
        const response = await api.get("/api/profile/");
        return response.data;
    } catch (error) {
        if (error.response?.status === 401) {
            throw new Error("Please log in to view your profile");
        }
        throw error.response?.data || new Error("Failed to fetch profile");
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
        const response = await api.post("/auth/password-reset/", { email });
        return response.data;
    } catch (error) {
        if (error.response?.status === 400) {
            throw new Error("Invalid email address");
        }
        throw error.response?.data || new Error("Failed to request password reset");
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
        if (error.response?.status === 400) {
            throw new Error("Invalid password or token");
        }
        throw error.response?.data || new Error("Failed to reset password");
    }
};

// Credit system functions
export const getCredits = async () => {
    try {
        const response = await api.get("/credits/");
        return response.data;
    } catch (error) {
        if (error.response?.status === 401) {
            throw new Error("Please log in to view your credits");
        }
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