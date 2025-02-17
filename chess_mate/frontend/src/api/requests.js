import api from './index';

// API functions
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
        throw error.response?.data || new Error("Login failed");
    }
};

export const logoutUser = async () => {
    try {
        const tokens = localStorage.getItem('tokens');
        if (tokens) {
            const parsedTokens = JSON.parse(tokens);
            await api.post('/api/logout/', { refresh_token: parsedTokens.refresh });
        }
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        localStorage.removeItem('tokens');
        delete api.defaults.headers.common['Authorization'];
    }
};

export const registerUser = async (userData) => {
    try {
        const response = await api.post("/api/register/", userData);
        return response.data;
    } catch (error) {
        throw error.response?.data || error;
    }
};

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

export const fetchExternalGames = async (platform, username, gameType) => {
    try {
        const effectiveGameType = gameType === "all" ? "rapid" : gameType;
        const response = await api.post("/api/fetch-games/", {
            platform: platform.toLowerCase(),
            username: username.trim(),
            game_type: effectiveGameType,
            num_games: 10
        });
        
        if (response.data.error) {
            throw new Error(response.data.error);
        }
        
        console.log('Fetch games response:', response.data);
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

export const analyzeGame = async (gameId) => {
    try {
        const response = await api.post(`/api/game/${gameId}/analysis/`, {
            depth: 20,
            use_ai: true
        });
        return response.data;
    } catch (error) {
        throw error.response?.data || new Error("Failed to start analysis");
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
        throw error.response?.data || new Error("Failed to start batch analysis");
    }
};

export const checkAnalysisStatus = async (taskId) => {
    try {
        const response = await api.get(`/api/game/analysis/status/${taskId}/`);
        return response.data;
    } catch (error) {
        if (error.response?.status === 401) {
            throw new Error("Session expired. Please log in again.");
        }
        if (error.response?.status === 404) {
            throw new Error("Analysis task not found.");
        }
        throw new Error(error.response?.data?.error || "Failed to check analysis status.");
    }
};

export const checkBatchAnalysisStatus = async (taskId) => {
    try {
        const response = await api.get(`/api/games/batch-analyze/status/${taskId}/`);
        return response.data;
    } catch (error) {
        throw error.response?.data || new Error("Failed to check batch analysis status");
    }
};

export const fetchGameAnalysis = async (gameId) => {
    try {
        const response = await api.get(`/api/game/${gameId}/analysis/`);
        return response.data.analysis;
    } catch (error) {
        throw error.response?.data || new Error("Failed to fetch analysis");
    }
};

export const fetchGameFeedback = async (gameId) => {
    try {
        const response = await api.get(`/api/feedback/${gameId}/`);
        return response.data.feedback;
    } catch (error) {
        throw error.response?.data || new Error("Failed to fetch feedback");
    }
};

export const getUserProfile = async () => {
    try {
        const response = await api.get("/api/profile/");
        return response.data;
    } catch (error) {
        throw error.response?.data || new Error("Failed to fetch profile");
    }
};

export const updateUserProfile = async (profileData) => {
    try {
        const response = await api.patch("/api/profile/", profileData);
        return response.data;
    } catch (error) {
        throw error.response?.data || new Error("Failed to update profile");
    }
};

export const requestPasswordReset = async (email) => {
    try {
        const response = await api.post("/api/auth/password-reset/", { email });
        return response.data;
    } catch (error) {
        throw error.response?.data || new Error("Failed to request password reset");
    }
};

export const resetPassword = async (uid, token, newPassword) => {
    try {
        const response = await api.post("/api/auth/password-reset/confirm/", {
            uid,
            token,
            new_password: newPassword
        });
        return response.data;
    } catch (error) {
        throw error.response?.data || new Error("Failed to reset password");
    }
};

export const analyzeSpecificGame = async (gameId) => {
    try {
        const response = await api.post(`/api/game/${gameId}/analyze/`, {
            depth: 20,
            use_ai: true
        });
        return response.data;
    } catch (error) {
        if (error.response?.status === 401) {
            throw new Error("Session expired. Please log in again.");
        }
        if (error.response?.status === 402) {
            throw new Error("Insufficient credits. Please purchase more credits to analyze games.");
        }
        throw new Error(error.response?.data?.error || "Failed to analyze game. Please try again.");
    }
}; 