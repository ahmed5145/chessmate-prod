import api from './api';
const ANALYSIS_START_DEDUP_WINDOW_MS = 15000;
const inFlightAnalysisStarts = new Map();
const recentAnalysisStarts = new Map();
const inFlightAnalysisFetches = new Map();

const SUCCESS_STATUSES = new Set(['SUCCESS', 'COMPLETED']);
const TERMINAL_FAILURE_STATUSES = new Set(['FAILURE', 'FAILED', 'ERROR', 'REVOKED', 'AUTH_ERROR']);

export const classifyAnalysisPollingStatus = (status, progress = 0) => {
    const normalizedStatus = String(status || '').toUpperCase();
    const numericProgress = Number(progress) || 0;

    return {
        normalizedStatus,
        isSuccess: SUCCESS_STATUSES.has(normalizedStatus) || numericProgress >= 100,
        isTerminalFailure: TERMINAL_FAILURE_STATUSES.has(normalizedStatus),
    };
};

export const computeNextPollDelay = ({ currentDelay, minDelay, maxDelay, hadError }) => {
    if (!hadError) {
        return minDelay;
    }

    return Math.min(maxDelay, currentDelay * 2);
};

export const shouldPollStatus = (status, progress = 0) => {
    const normalizedStatus = String(status || '').toUpperCase();
    const numericProgress = Number(progress) || 0;
    
    // Stop polling if we've reached 100% progress
    if (numericProgress >= 100) {
        return false;
    }
    
    // Stop polling if status is a terminal state (success or failure)
    if (SUCCESS_STATUSES.has(normalizedStatus) || TERMINAL_FAILURE_STATUSES.has(normalizedStatus)) {
        return false;
    }
    
    // Continue polling for all other states (PENDING, STARTED, PROCESSING, etc.)
    return true;
};

export const normalizeAnalysisResponsePayload = (rawPayload) => {
    const payload = rawPayload && typeof rawPayload === 'object' ? rawPayload : {};
    const unwrapped = payload.analysis_data && typeof payload.analysis_data === 'object'
        ? payload.analysis_data
        : payload;
    const extractedFeedback =
        (payload.feedback && typeof payload.feedback === 'object' ? payload.feedback : null) ||
        (unwrapped.feedback && typeof unwrapped.feedback === 'object' ? unwrapped.feedback : null) ||
        (payload.ai_feedback && typeof payload.ai_feedback === 'object' ? payload.ai_feedback : null) ||
        {};

    const normalizedAnalysisResults = unwrapped.analysis_results || {
        summary: unwrapped.metrics || {},
        moves: unwrapped.moves || unwrapped.movesAnalysis || []
    };

    const normalizedMetrics =
        (unwrapped.metrics && typeof unwrapped.metrics.summary === 'object'
            ? unwrapped.metrics.summary
            : unwrapped.metrics) ||
        normalizedAnalysisResults.summary ||
        {};

    return {
        ...unwrapped,
        analysis_results: normalizedAnalysisResults,
        metrics: normalizedMetrics,
        moves: unwrapped.moves || unwrapped.movesAnalysis || normalizedAnalysisResults.moves || [],
        feedback: extractedFeedback,
        ai_feedback: extractedFeedback,
        game_context: payload.game_context || unwrapped.game_context || {}
    };
};

export const analyzeSpecificGame = async (gameId) => {
    const numericGameId = Number(gameId);
    const dedupKey = Number.isFinite(numericGameId) ? String(numericGameId) : String(gameId);
    const now = Date.now();

    const cachedStart = recentAnalysisStarts.get(dedupKey);
    if (cachedStart && (now - cachedStart.timestamp) < ANALYSIS_START_DEDUP_WINDOW_MS) {
        console.log(`Skipping duplicate analysis start for game ${dedupKey} within dedup window`);
        return { ...cachedStart.response, deduplicated: true };
    }

    if (inFlightAnalysisStarts.has(dedupKey)) {
        console.log(`Reusing in-flight analysis start request for game ${dedupKey}`);
        return inFlightAnalysisStarts.get(dedupKey);
    }

    const requestPromise = (async () => {
        try {
            const response = await api.post(`/api/v1/games/${gameId}/analyze/`);
            console.log('Analysis started response:', response.data);

            const normalizedResponse = {
                success: true,
                task_id: response.data.task_id || response.data.id,
                status: response.data.status || 'started',
                message: response.data.message || 'Analysis started',
                redirect: false // Explicitly indicate no redirect
            };

            recentAnalysisStarts.set(dedupKey, {
                timestamp: Date.now(),
                response: normalizedResponse
            });

            return normalizedResponse;
        } catch (error) {
            console.error('Error starting analysis:', error);
            if (error.response?.status === 401) {
                throw new Error('Authentication required');
            }
            throw error.response?.data?.error || error.message || 'Failed to start analysis';
        } finally {
            inFlightAnalysisStarts.delete(dedupKey);
        }
    })();

    inFlightAnalysisStarts.set(dedupKey, requestPromise);
    return requestPromise;
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
            console.log(`Detailed task data for game ${gameId}:`, taskData);
            
            const status = taskData.status?.toUpperCase() || 'UNKNOWN';
            const progressValue = taskData.progress !== undefined ? Number(taskData.progress) : 0;
            
            // Store progress in localStorage
            if (progressValue > 0) {
                localStorage.setItem(`last_known_progress_${gameId}`, progressValue);
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
            
            // Handle processing status
            if (status === 'PROCESSING') {
                return {
                    status: 'PROCESSING',
                    progress: progressValue,
                    message: taskData.message || 'Analyzing game...'
                };
            }
            
            // For other statuses
            return {
                status: status,
                progress: progressValue,
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
        
        // Check for a 'not_found' status specifically
        if (data && data.status === 'not_found') {
            return {
                status: 'PENDING',
                progress: 0,
                message: data.message || 'Analysis task not found'
            };
        }
        
        // Fallback to unknown status
        console.warn('Unexpected response format:', data);
        return {
            status: 'UNKNOWN',
            progress: 0,
            message: 'Checking analysis status...'
        };
    } catch (error) {
        console.error('Error checking analysis status:', error);
        return {
            status: 'ERROR',
            error: error.message || 'Error checking status',
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
    const dedupKey = String(gameId);
    if (inFlightAnalysisFetches.has(dedupKey)) {
        return inFlightAnalysisFetches.get(dedupKey);
    }

    const requestPromise = (async () => {
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
            const normalizedPayload = normalizeAnalysisResponsePayload(response.data);

            const hasMetrics =
                (normalizedPayload.metrics && Object.keys(normalizedPayload.metrics).length > 0) ||
                (normalizedPayload.analysis_results && Object.keys(normalizedPayload.analysis_results).length > 0);
            const hasMoves =
                (Array.isArray(normalizedPayload.moves) && normalizedPayload.moves.length > 0) ||
                (Array.isArray(normalizedPayload.movesAnalysis) && normalizedPayload.movesAnalysis.length > 0);
            
            // If we have a valid analysis, mark it as complete in localStorage
            if (hasMetrics && hasMoves) {
                localStorage.setItem(`analysis_complete_${gameId}`, 'true');
                localStorage.removeItem(`analysis_error_${gameId}`);
                return {
                    ...normalizedPayload,
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
                ...normalizedPayload,
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
    } finally {
        inFlightAnalysisFetches.delete(dedupKey);
    }
    })();

    inFlightAnalysisFetches.set(dedupKey, requestPromise);
    return requestPromise;
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
        const numericGameId = Number(gameId);
        const dedupKey = Number.isFinite(numericGameId) ? String(numericGameId) : String(gameId);
        recentAnalysisStarts.delete(dedupKey);
        inFlightAnalysisStarts.delete(dedupKey);
        
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
            throw new Error('Authentication required');
        }
        throw error.response?.data?.error || error.message || 'Failed to restart analysis';
    }
};
