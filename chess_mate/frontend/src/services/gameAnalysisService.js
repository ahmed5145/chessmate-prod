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
        const response = await api.post(`/api/game/${gameId}/analyze/`);
        return response.data;
    } catch (error) {
        console.error('Error starting analysis:', error);
        throw error.response?.data?.error || error.message || 'Failed to start analysis';
    }
};

export const checkAnalysisStatus = async (taskId) => {
    try {
        const response = await api.get(`/api/game/analysis/status/${taskId}/`);
        return response.data;
    } catch (error) {
        console.error('Error checking analysis status:', error);
        throw error.response?.data?.error || error.message || 'Failed to check analysis status';
    }
};

export const fetchGameAnalysis = async (gameId) => {
    try {
        const response = await api.get(`/api/game/${gameId}/analysis/`);
        return response.data;
    } catch (error) {
        console.error('Error fetching analysis:', error);
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