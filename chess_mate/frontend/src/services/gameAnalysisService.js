import axios from 'axios';
import api from './api';
import { API_URL } from '../config';

const API_BASE_URL = API_URL;
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
        const response = await api.post(`/api/v1/games/${gameId}/analyze/`);
        console.log('Analysis started response:', response.data);
        
        // Return with consistent structure
        return {
            success: true,
            task_id: response.data.task_id || response.data.id,
            status: response.data.status || 'started',
            message: response.data.message || 'Analysis started',
            redirect: false // Explicitly indicate no redirect
        };
    } catch (error) {
        console.error('Error starting analysis:', error);
        if (error.response?.status === 401) {
            throw { auth_error: true, message: 'Authentication required' };
        }
        throw error.response?.data?.error || error.message || 'Failed to start analysis';
    }
};

export const checkAnalysisStatus = async (gameId) => {
    try {
        console.log(`Checking analysis status for game ${gameId}`);
        const response = await api.get(`/api/v1/games/${gameId}/analysis/status/`);
        
        // Process the response data
        const data = response.data;
        console.log(`Analysis status response for game ${gameId}:`, data);
        
        // Handle direct task response without a task wrapper
        if (data && data.status && !data.task) {
            // The response contains direct task status
            const status = data.status.toUpperCase();
            
            // If task is complete
            if (status === 'SUCCESS' || status === 'COMPLETED') {
                localStorage.setItem(`analysis_complete_${gameId}`, 'true');
                localStorage.removeItem(`last_known_progress_${gameId}`);
                localStorage.removeItem(`last_progress_update_${gameId}`);
                return {
                    status: 'SUCCESS',
                    progress: 100,
                    message: data.message || 'Analysis completed'
                };
            }
            
            // If task failed
            if (status === 'FAILURE' || status === 'FAILED' || status === 'ERROR') {
                localStorage.setItem(`analysis_error_${gameId}`, data.error || 'Analysis failed');
                return {
                    status: 'FAILURE',
                    progress: 0,
                    error: data.error || 'Analysis task failed'
                };
            }
            
            // Save progress to localStorage for continuity
            if (data.progress !== undefined) {
                localStorage.setItem(`last_known_progress_${gameId}`, data.progress);
                localStorage.setItem(`last_progress_update_${gameId}`, Date.now());
            }
            
            return {
                status: status,
                progress: data.progress || 0,
                message: data.message || 'Analyzing game...'
            };
        }
        
        // Handle standard response with task wrapper
        if (data && data.task) {
            const taskData = data.task;
            const status = taskData.status?.toUpperCase() || 'UNKNOWN';
            
            // Store progress in localStorage
            if (taskData.progress !== undefined) {
                localStorage.setItem(`last_known_progress_${gameId}`, taskData.progress);
                localStorage.setItem(`last_progress_update_${gameId}`, Date.now());
            }
            
            // If task is complete, mark it as complete
            if (status === 'SUCCESS' || status === 'COMPLETED') {
                console.log('Analysis completed for game:', gameId);
                localStorage.setItem(`analysis_complete_${gameId}`, 'true');
                localStorage.removeItem(`last_known_progress_${gameId}`);
                localStorage.removeItem(`last_progress_update_${gameId}`);
                return {
                    status: 'SUCCESS',
                    progress: 100,
                    message: taskData.message || 'Analysis completed'
                };
            }
            
            // Check for failure
            if (status === 'FAILURE' || status === 'FAILED' || status === 'ERROR') {
                console.error('Analysis failed for game:', gameId, taskData.error);
                localStorage.setItem(`analysis_error_${gameId}`, taskData.error || 'Analysis failed');
                return {
                    status: 'FAILURE',
                    error: taskData.error || 'Analysis task failed',
                    progress: 0
                };
            }
            
            // For other statuses
            return {
                status: status,
                progress: taskData.progress || 0,
                message: taskData.message || 'Analyzing game...'
            };
        }
        
        // Handle case where no task or task status is found
        // Check if we have cached progress in localStorage
        const cachedProgress = localStorage.getItem(`last_known_progress_${gameId}`);
        
        if (cachedProgress) {
            const lastUpdate = localStorage.getItem(`last_progress_update_${gameId}`);
            const now = Date.now();
            
            // If the cached progress is recent (less than 5 minutes old)
            if (lastUpdate && (now - lastUpdate) < 300000) {
                return {
                    status: 'PROCESSING',
                    progress: parseInt(cachedProgress, 10) || 0,
                    message: 'Continuing analysis...'
                };
            }
        }
        
        // Fallback to unknown status
        return {
            status: 'UNKNOWN',
            progress: 0,
            message: 'Checking analysis status...'
        };
    } catch (error) {
        console.error('Error checking analysis status:', error);
        return {
            status: 'ERROR',
            error: error.message,
            progress: 0
        };
    }
};

// Helper function to simulate analysis progress for better UX when API fails
const simulateProgressResponse = (gameId) => {
    // Get the start time from localStorage or set it now
    let analysisStartTime = localStorage.getItem(`analysis_start_${gameId}`);
    if (!analysisStartTime) {
        analysisStartTime = Date.now();
        localStorage.setItem(`analysis_start_${gameId}`, analysisStartTime);
    }
    
    // Calculate progress based on time elapsed (simulate 2 minute analysis)
    const TOTAL_ANALYSIS_TIME = 2 * 60 * 1000; // 2 minutes in ms
    const timeElapsed = Date.now() - parseInt(analysisStartTime);
    const calculatedProgress = Math.min(Math.floor((timeElapsed / TOTAL_ANALYSIS_TIME) * 100), 99);
    
    return {
        task_id: gameId,
        status: 'in_progress',
        progress: calculatedProgress,
        message: calculatedProgress < 95 
            ? `Analysis in progress (${calculatedProgress}%)`
            : 'Almost done, finalizing analysis...',
        error: null,
        redirect: false,
        simulated: true // Flag to indicate this is simulated progress
    };
}

export const fetchGameAnalysis = async (gameId, retry = 0) => {
    // Check if we have a stored error for this game analysis
    const storedError = localStorage.getItem(`analysis_error_${gameId}`);
    if (storedError && retry === 0) {
        console.error(`Analysis error found for game ${gameId}:`, storedError);
        return {
            error: storedError,
            status: 'FAILURE',
            metrics: {},
            movesAnalysis: [],
            ai_feedback: null,
            isComplete: false
        };
    }
    
    // If retrying, clear the error
    if (retry > 0 && storedError) {
        localStorage.removeItem(`analysis_error_${gameId}`);
    }

    try {
        console.log(`Fetching analysis for game ${gameId}`);
        const response = await api.get(`/api/v1/games/${gameId}/analysis/`);
        
        // Check if we got a valid response with data
        if (response.data && Object.keys(response.data).length > 0) {
            console.log(`Analysis data received for game ${gameId}:`, response.data);
            
            // If we have a valid analysis, mark it as complete in localStorage
            if (response.data.metrics && response.data.movesAnalysis) {
                localStorage.setItem(`analysis_complete_${gameId}`, 'true');
                localStorage.removeItem(`analysis_error_${gameId}`);
                return {
                    ...response.data,
                    isComplete: true
                };
            }
            
            // If we have a task status but no complete analysis
            if (response.data.status) {
                const status = response.data.status;
                
                // If the analysis is still in progress
                if (status === 'PENDING' || status === 'STARTED' || status === 'PROGRESS') {
                    // Get the progress if available
                    const progress = response.data.progress || 
                                    localStorage.getItem(`last_known_progress_${gameId}`) || 0;
                    return {
                        error: null,
                        status: status,
                        progress: progress,
                        metrics: {},
                        movesAnalysis: [],
                        ai_feedback: null,
                        isComplete: false
                    };
                }
                
                // If the analysis failed
                if (status === 'FAILURE' || status === 'FAILED' || status === 'ERROR') {
                    const errorMessage = response.data.error || 'Analysis failed';
                    localStorage.setItem(`analysis_error_${gameId}`, errorMessage);
                    return {
                        error: errorMessage,
                        status: 'FAILURE',
                        metrics: {},
                        movesAnalysis: [],
                        ai_feedback: null,
                        isComplete: false
                    };
                }
            }
            
            // Return the data as is if it doesn't match our expected format
            return {
                ...response.data,
                isComplete: false
            };
        }
        
        // If we didn't get valid data, check the analysis status
        const statusResult = await checkAnalysisStatus(gameId);
        console.log(`Status check for game ${gameId}:`, statusResult);
        
        if (statusResult.status === 'FAILURE') {
            localStorage.setItem(`analysis_error_${gameId}`, statusResult.error || 'Analysis failed');
            return {
                error: statusResult.error || 'Analysis failed',
                status: 'FAILURE',
                metrics: {},
                movesAnalysis: [],
                ai_feedback: null,
                isComplete: false
            };
        }
        
        // Return empty analysis data with status
        return {
            error: null,
            status: statusResult.status,
            progress: statusResult.progress || 0,
            metrics: {},
            movesAnalysis: [],
            ai_feedback: null,
            isComplete: false
        };
    } catch (error) {
        console.error(`Error fetching analysis for game ${gameId}:`, error);
        
        // Store the error
        localStorage.setItem(`analysis_error_${gameId}`, error.message || 'Failed to fetch analysis');
        
        return {
            error: error.message || 'Failed to fetch analysis',
            status: 'ERROR',
            metrics: {},
            movesAnalysis: [],
            ai_feedback: null,
            isComplete: false
        };
    }
};

// Helper function to normalize metrics data
const normalizeMetrics = (metrics) => {
    const defaultMetrics = {
        overall: {},
        move_quality: {},
        time_management: {},
        consistency: {},
        phases: {
            opening: {},
            middlegame: {},
            endgame: {}
        },
        tactics: {},
        advantage: {},
        resourcefulness: {},
        metadata: {
            is_white: true,
            total_moves: 0,
            opening_length: 0,
            middlegame_length: 0,
            endgame_length: 0
        }
    };

    // Ensure all required sections exist
    const normalizedMetrics = {
        ...defaultMetrics,
        ...metrics
    };

    // Ensure all numeric values are numbers
    Object.keys(normalizedMetrics).forEach(section => {
        if (typeof normalizedMetrics[section] === 'object') {
            Object.keys(normalizedMetrics[section]).forEach(key => {
                const value = normalizedMetrics[section][key];
                if (typeof value === 'string' && !isNaN(value)) {
                    normalizedMetrics[section][key] = parseFloat(value);
                }
            });
        }
    });

    return normalizedMetrics;
};

// Helper function to normalize moves data
const normalizeMoves = (moves) => {
    return moves.map(move => ({
        move_number: parseInt(move.move_number) || 0,
        move: move.move || '',
        san: move.san || '',
        is_white: Boolean(move.is_white),
        evaluation: parseFloat(move.evaluation) || 0,
        classification: move.classification || 'neutral',
        position_metrics: move.position_metrics || {}
    }));
};

// Helper function to normalize positions data
const normalizePositions = (positions) => {
    return positions.map(position => ({
        move_number: parseInt(position.move_number) || 0,
        fen: position.fen || '',
        score: parseFloat(position.score) || 0,
        best_move: position.best_move || null,
        position_metrics: position.position_metrics || {}
    }));
};

export const fetchBatchAnalysis = async (taskId) => {
    try {
        if (!taskId) {
            throw new Error('No task ID provided');
        }

        const response = await api.get(
            `/api/v1/games/batch-status/`
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
        const response = await api.get(`/api/v1/games/batch-status/`);

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

export const checkMultipleAnalysisStatuses = async (gameIds) => {
    try {
        console.log('Checking status for', gameIds.length, 'games:', gameIds);
        
        // Use the api instance which handles authentication correctly
        const response = await api.post(`/api/v1/games/batch-status/`, {
            game_ids: gameIds
        });

        console.log('Batch status API response:', response.status, response.data);

        if (!response.data || !response.data.statuses) {
            console.error('Batch status API error: Invalid response format', response.data);
            
            // Return simulated progress for each game ID instead of empty object
            const simulatedStatuses = {};
            gameIds.forEach(gameId => {
                simulatedStatuses[gameId] = simulateProgressResponse(gameId);
            });
            return simulatedStatuses;
        }

        return response.data.statuses;
    } catch (error) {
        console.error('Batch status API error:', error);
        
        if (error.response) {
            console.error(
                'Status:', error.response.status,
                'Data:', error.response.data,
                'Headers:', error.response.headers
            );
        } else if (error.request) {
            console.error('No response received. Request:', error.request);
        } else {
            console.error('Error setting up request:', error.message);
        }
        
        // Return simulated progress for each game ID instead of empty object
        const simulatedStatuses = {};
        gameIds.forEach(gameId => {
            simulatedStatuses[gameId] = simulateProgressResponse(gameId);
        });
        return simulatedStatuses;
    }
};

// Helper function to restart an analysis that appears to be stuck
export const restartAnalysis = async (gameId) => {
    try {
        console.log(`Force restarting analysis for game ${gameId}`);
        
        // First clear any cached completion markers
        localStorage.removeItem(`analysis_complete_${gameId}`);
        localStorage.removeItem(`last_progress_${gameId}`);
        localStorage.removeItem(`last_progress_time_${gameId}`);
        localStorage.removeItem(`analysis_start_${gameId}`);
        localStorage.removeItem(`last_known_progress_${gameId}`);
        localStorage.removeItem(`last_progress_update_${gameId}`);
        
        // Start a new analysis
        const response = await api.post(`/api/v1/games/${gameId}/analyze/`, {
            force_restart: true
        });
        
        console.log('Analysis restart response:', response.data);
        
        return {
            success: true,
            task_id: response.data.task_id || response.data.id,
            status: response.data.status || 'started',
            message: 'Analysis restarted successfully',
            restart: true
        };
    } catch (error) {
        console.error('Error restarting analysis:', error);
        if (error.response?.status === 401) {
            throw { auth_error: true, message: 'Authentication required' };
        }
        throw error.response?.data?.error || error.message || 'Failed to restart analysis';
    }
};
