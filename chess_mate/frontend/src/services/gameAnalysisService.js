import axios from 'axios';
import api from './api';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const CACHE_TTL = 3600 * 1000; // 1 hour in milliseconds

// Initialize IndexedDB
const initDB = () => {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('chessmate', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('analysis')) {
                db.createObjectStore('analysis', { keyPath: 'gameId' });
            }
        };
    });
};

// Cache analysis in IndexedDB
const cacheAnalysis = async (gameId, data) => {
    try {
        const db = await initDB();
        const tx = db.transaction('analysis', 'readwrite');
        const store = tx.objectStore('analysis');
        
        await store.put({
            gameId,
            data,
            timestamp: Date.now()
        });
    } catch (error) {
        console.error('Error caching analysis:', error);
    }
};

// Get cached analysis from IndexedDB
const getCachedAnalysis = async (gameId) => {
    try {
        const db = await initDB();
        const tx = db.transaction('analysis', 'readonly');
        const store = tx.objectStore('analysis');
        const result = await store.get(gameId);
        
        if (result && (Date.now() - result.timestamp) < CACHE_TTL) {
            return result.data;
        }
        return null;
    } catch (error) {
        console.error('Error getting cached analysis:', error);
        return null;
    }
};

export const analyzeSpecificGame = async (gameId) => {
    try {
        // Check cache first
        const cachedData = await getCachedAnalysis(gameId);
        if (cachedData && cachedData.status === 'completed') {
            return cachedData;
        }

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
            // Handle the response format from the backend
            const result = {
                status: response.data.status,
                message: response.data.message,
                game_id: response.data.game_id
            };

            // If the status is completed, fetch the analysis immediately
            if (result.status === 'completed') {
                try {
                    const analysisResponse = await fetchGameAnalysis(result.game_id);
                    return {
                        ...result,
                        analysis: analysisResponse
                    };
                } catch (analysisError) {
                    console.error('Error fetching analysis after completion:', analysisError);
                }
            }

            return result;
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
        // Check cache first
        const cachedData = await getCachedAnalysis(gameId);
        if (cachedData) {
            return cachedData;
        }

        const response = await axios.get(
            `${API_BASE_URL}/api/game/${gameId}/analysis/`,
            {
                withCredentials: true,
                headers: {
                    'Content-Type': 'application/json',
                }
            }
        );

        console.log('Analysis response:', response.data); // Debug log

        if (response.data) {
            // Handle different response formats
            const analysisData = response.data.analysis_data || response.data.analysis || response.data;
            
            if (analysisData) {
                await cacheAnalysis(gameId, analysisData);
                return analysisData;
            } else {
                console.error('No analysis data in response:', response.data);
                throw new Error('No analysis data found in response');
            }
        } else {
            throw new Error('Invalid response format');
        }
    } catch (error) {
        console.error('Error fetching analysis:', error);
        console.error('Error details:', error.response?.data); // Log response data if available
        throw error.response?.data?.error || error.message || 'Failed to fetch analysis';
    }
};

export const fetchBatchAnalysis = async (taskId) => {
    try {
        if (!taskId) {
            throw new Error('No task ID provided');
        }

        const response = await api.get(
            `/api/games/batch-analyze/status/${taskId}/`
        );

        if (!response.data) {
            throw new Error('Invalid response format');
        }

        const { state, meta, results, error } = response.data;

        // Handle error state
        if (state === 'FAILURE' || error) {
            throw new Error(error || 'Analysis failed');
        }

        // Handle progress state
        if (state === 'PROGRESS') {
            return {
                status: 'in_progress',
                progress: {
                    current: meta?.current || 0,
                    total: meta?.total || 0,
                    message: meta?.message || 'Analyzing games...',
                    progress: meta?.progress || 0
                }
            };
        }

        // Handle success state
        if (state === 'SUCCESS') {
            return {
                status: 'completed',
                batch_feedback: results || {},
                progress: {
                    current: meta?.current || 0,
                    total: meta?.total || 0,
                    message: 'Analysis complete',
                    progress: 100
                }
            };
        }

        // Handle unknown state
        throw new Error(`Unknown state: ${state}`);
    } catch (error) {
        console.error('Error fetching batch analysis:', error);
        throw error;
    }
};

export const checkBatchAnalysisStatus = async (taskId) => {
    if (!taskId) {
        console.error('No taskId provided to checkBatchAnalysisStatus');
        return {
            state: 'FAILURE',
            meta: {
                error: 'No taskId provided',
                current: 0,
                total: 0,
                progress: 0,
                message: 'No taskId provided'
            }
        };
    }

    try {
        // Use the api instance which handles authentication and CSRF automatically
        const response = await api.get(`/api/games/batch-analyze/status/${taskId}/`);
        
        if (!response.data) {
            throw new Error('Invalid response from server');
        }

        // Ensure we have a state, defaulting to FAILURE if not present
        const state = response.data.state || 'FAILURE';
        const meta = response.data.meta || {};
        const completed_games = response.data.completed_games || [];
        const failed_games = response.data.failed_games || [];
        const batch_feedback = response.data.batch_feedback || {};

        // Common response structure
        return {
            state: state === 'STARTED' ? 'PROGRESS' : state, // Convert STARTED to PROGRESS
            meta: {
                current: meta.current || 0,
                total: meta.total || 0,
                message: meta.message || 'Analyzing games...',
                progress: meta.progress || 0
            },
            completed_games,
            failed_games,
            batch_feedback
        };
    } catch (error) {
        console.error('Error checking batch analysis status:', error);
        throw error;
    }
};