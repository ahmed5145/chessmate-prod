import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const analyzeSpecificGame = async (gameId) => {
    try {
        const response = await axios.post(
            `${API_BASE_URL}/api/game/${gameId}/analyze/`,
            {},
            {
                withCredentials: true,
                headers: {
                    'Content-Type': 'application/json',
                }
            }
        );

        if (response.data && response.data.task_id) {
            return {
                status: 'started',
                task_id: response.data.task_id
            };
        } else {
            throw new Error('Invalid response format');
        }
    } catch (error) {
        console.error('Error starting analysis:', error);
        throw error.response?.data?.error || error.message || 'Failed to start analysis';
    }
};

export const checkAnalysisStatus = async (taskId) => {
    try {
        const response = await axios.get(
            `${API_BASE_URL}/api/game/analysis/status/${taskId}/`,
            {
                withCredentials: true,
                headers: {
                    'Content-Type': 'application/json',
                }
            }
        );

        if (response.data) {
            return {
                status: response.data.status,
                result: response.data.result,
                error: response.data.error
            };
        } else {
            throw new Error('Invalid response format');
        }
    } catch (error) {
        console.error('Error checking analysis status:', error);
        throw error.response?.data?.error || error.message || 'Failed to check analysis status';
    }
};

export const fetchGameAnalysis = async (gameId) => {
    try {
        const response = await axios.get(
            `${API_BASE_URL}/api/game/${gameId}/analysis/`,
            {
                withCredentials: true,
                headers: {
                    'Content-Type': 'application/json',
                }
            }
        );

        if (response.data && response.data.analysis_data) {
            return response.data.analysis_data;
        } else {
            throw new Error('Invalid response format');
        }
    } catch (error) {
        console.error('Error fetching analysis:', error);
        throw error.response?.data?.error || error.message || 'Failed to fetch analysis';
    }
}; 