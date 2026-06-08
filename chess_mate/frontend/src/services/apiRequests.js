import api from './api';
import { setTokens, clearTokens } from './authService';
import { extractApiError } from '../utils/apiErrors';
import {
    analyzeSpecificGame as analyzeSpecificGameService,
    checkAnalysisStatus as checkAnalysisStatusService,
    fetchGameAnalysis as fetchGameAnalysisService,
    checkMultipleAnalysisStatuses as checkMultipleAnalysisStatusesService,
} from './gameAnalysisService';

// Authentication functions
export const loginUser = async (email, password, rememberMe = true) => {
    try {
        const response = await api.post("/api/v1/auth/login/", {
            email,
            password,
            remember_me: rememberMe,
        });

        // Check the response structure
        if (!response.data) {
            throw new Error("Invalid response from server");
        }

        // Handle response in standard format: { status: 'success', data: {...} }
        let userData = null;
        let accessToken = null;
        let refreshToken = null;

        // Extract tokens and user data from different possible response formats
        if (response.data.status === 'success' && response.data.data) {
            // Standard API format with status and data fields
            accessToken = response.data.data.access || null;
            refreshToken = response.data.data.refresh || null;
            userData = response.data.data.user || null;
        } else {
            // Direct format with access, refresh, and user fields
            accessToken = response.data.access || null;
            refreshToken = response.data.refresh || null;
            userData = response.data.user || null;
        }

        // Validate that we have the necessary data
        if (!accessToken || !refreshToken) {
            console.error('Missing tokens in response:', response.data);
            throw new Error("Authentication tokens not found in server response");
        }

        // Persist tokens through shared helper to keep all key formats in sync.
        setTokens(accessToken, refreshToken, { rememberMe });

        // Set default Authorization header
        api.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;

        return {
            success: true,
            user: userData || {}
        };
    } catch (error) {
        // Provide specific error messages based on status codes
        if (error.response?.status === 401) {
            const authMessage = extractApiError(
                error,
                'Invalid email or password'
            );
            throw new Error(authMessage);
        } else if (error.response?.status === 403) {
            throw new Error("Account is locked or requires verification");
        } else if (error.response?.status === 429) {
            throw new Error("Too many login attempts. Please try again later.");
        }

        // Handle error messages from backend
        if (error.response?.data?.message) {
            throw new Error(error.response.data.message);
        } else if (error.response?.data?.error) {
            throw new Error(error.response.data.error);
        } else if (error.message) {
            throw new Error(error.message);
        }

        throw new Error("Login failed, please try again");
    }
};

export const logoutUser = async () => {
    try {
        const tokens = JSON.parse(localStorage.getItem('tokens') || '{}');

        if (tokens.refresh) {
            await api.post("/api/v1/auth/logout/", { refresh: tokens.refresh });
        }

        // Clear tokens regardless of server response.
        clearTokens();
        delete api.defaults.headers.common['Authorization'];

        return true;
    } catch (error) {
        console.error('Logout error:', error);

        // Even if the server request fails, clear local auth state.
        clearTokens();
        delete api.defaults.headers.common['Authorization'];
        return false;
    }
};

export const registerUser = async (userData) => {
    try {
        const response = await api.post("/api/v1/auth/register/", userData);
        return response.data || {};
    } catch (error) {
        throw new Error(extractApiError(error, 'Registration failed. Please try again.'));
    }
};

export const resendVerificationEmail = async (email) => {
    try {
        const response = await api.post('/api/v1/auth/resend-verification/', { email });
        return response.data || {};
    } catch (error) {
        throw new Error(extractApiError(error, 'Could not resend verification email. Please try again.'));
    }
};

const extractGamesFromPage = (data) => {
    if (data?.results && Array.isArray(data.results)) {
        return data.results;
    }
    if (data?.data && Array.isArray(data.data)) {
        return data.data;
    }
    if (data?.games && Array.isArray(data.games)) {
        return data.games;
    }
    if (Array.isArray(data)) {
        return data;
    }
    return null;
};

const normalizeGameRow = (game) => {
    const rawStatus = String(game.analysis_status || game.status || '').toLowerCase();
    const isAnalyzed =
        rawStatus === 'analyzed' ||
        rawStatus === 'completed' ||
        !!game.analysis;
    let normalizedAnalysisStatus;
    if (isAnalyzed) {
        normalizedAnalysisStatus = 'analyzed';
    } else if (rawStatus === 'analyzing') {
        normalizedAnalysisStatus = 'analyzing';
    } else if (rawStatus === 'failed' || rawStatus === 'error') {
        normalizedAnalysisStatus = rawStatus;
    } else {
        normalizedAnalysisStatus = 'unanalyzed';
    }
    return {
        id: game.id,
        opponent: game.opponent || 'Unknown',
        result: game.result || 'unknown',
        date_played: game.date_played || game.played_at || new Date().toISOString(),
        played_at: game.played_at || game.date_played,
        opening_name: game.opening_name || 'Unknown Opening',
        time_control: game.time_control || game.time_control_type || 'unknown',
        time_control_type: game.time_control_type || game.time_control || 'unknown',
        status: game.status || normalizedAnalysisStatus,
        analysis_status: normalizedAnalysisStatus,
        analysis: isAnalyzed ? game.analysis || true : null,
        white: game.white || game.opponent || 'Unknown',
        black: game.black || game.user_username || 'Unknown',
        pgn: game.pgn || '',
        platform: game.platform || 'Unknown',
    };
};

const resolveNextGamesPath = (nextUrl) => {
    if (!nextUrl) {
        return null;
    }
    if (nextUrl.startsWith('http')) {
        const parsed = new URL(nextUrl);
        return `${parsed.pathname}${parsed.search}`;
    }
    return nextUrl;
};

// Game management functions
export const fetchUserGames = async () => {
    try {
        console.log('Fetching user games (all pages)...');
        const allRawGames = [];
        let path = '/api/v1/games/';

        while (path) {
            const response = await api.get(path);
            const pageGames = extractGamesFromPage(response.data);
            if (!pageGames) {
                console.error('Invalid response format:', response.data);
                break;
            }
            allRawGames.push(...pageGames);
            path = resolveNextGamesPath(response.data?.next);
        }

        const normalizedGames = allRawGames.map(normalizeGameRow);
        console.log(`Loaded ${normalizedGames.length} games across API pages`);

        return {
            results: normalizedGames,
            count: normalizedGames.length,
            next: null,
            previous: null,
        };
    } catch (error) {
        console.error('Error fetching games:', error);
        if (error.response?.status === 401) {
            throw new Error("Please log in to view your games");
        }
        throw new Error(error.response?.data?.message || "Failed to fetch games");
    }
};

const normalizeDashboardInsights = (insights) => {
    if (!Array.isArray(insights) || insights.length === 0) {
        return [{
            type: 'success',
            text: 'Import and analyze games to unlock personalized performance insights.',
        }];
    }

    if (insights[0]?.text) {
        return insights;
    }

    return insights.map((item) => {
        const mistakeCount = Number(item.mistake_count) || 0;
        const opponent = item.opponent || 'opponent';
        const summary = (item.summary || '').trim();
        let type = 'success';
        if (mistakeCount >= 5) {
            type = 'error';
        } else if (mistakeCount >= 2) {
            type = 'warning';
        }

        const text = summary
            ? `vs ${opponent}: ${summary}`
            : `vs ${opponent}: ${mistakeCount} mistake${mistakeCount === 1 ? '' : 's'} in recent analysis`;

        return { type, text: text.slice(0, 240) };
    });
};

const normalizeDashboardNextAction = (action) => {
    if (!action || typeof action !== 'object') {
        return null;
    }
    return {
        type: action.type || null,
        title: action.title,
        description: action.description,
        ctaLabel: action.cta_label,
        ctaTo: action.cta_to,
        secondaryLinks: Array.isArray(action.secondary_links)
            ? action.secondary_links.map((link) => ({
                label: link.label,
                to: link.to,
            }))
            : [],
    };
};

const normalizeDashboardFocusInsight = (focus) => {
    if (!focus || typeof focus !== 'object') {
        return null;
    }
    return {
        type: focus.type || 'success',
        text: focus.text,
        href: focus.href || null,
        actionLabel: focus.action_label || null,
        meta: focus.meta || null,
    };
};

const normalizeDashboardHeroMetrics = (metrics) => {
    if (!Array.isArray(metrics)) {
        return null;
    }
    return metrics
        .filter((metric) => metric?.label && metric?.value)
        .map((metric) => ({ label: metric.label, value: String(metric.value) }));
};

const normalizeSinceLastVisit = (sinceLastVisit) => {
    if (!sinceLastVisit || typeof sinceLastVisit !== 'object') {
        return {
            hasPreviousVisit: false,
            showBanner: false,
            gamesImported: 0,
            gamesAnalyzed: 0,
            batchReports: 0,
            summaryLines: [],
        };
    }
    return {
        hasPreviousVisit: Boolean(sinceLastVisit.has_previous_visit),
        showBanner: Boolean(sinceLastVisit.show_banner),
        gamesImported: Number(sinceLastVisit.games_imported) || 0,
        gamesAnalyzed: Number(sinceLastVisit.games_analyzed) || 0,
        batchReports: Number(sinceLastVisit.batch_reports) || 0,
        summaryLines: Array.isArray(sinceLastVisit.summary_lines)
            ? sinceLastVisit.summary_lines
            : [],
    };
};

const normalizeDashboardData = (raw) => {
    const gameStats = raw?.game_stats || {};
    const user = raw?.user || {};
    const analyzedGames = raw?.analyzed_games
        ?? gameStats.analyzed_games
        ?? gameStats.analyzed
        ?? 0;

    return {
        ...raw,
        total_games: raw?.total_games ?? gameStats.total ?? gameStats.total_games ?? 0,
        analyzed_games: analyzedGames,
        win_rate: raw?.win_rate ?? gameStats.win_rate ?? 0,
        average_accuracy: raw?.average_accuracy ?? 0,
        credits: raw?.credits ?? user.credits ?? 0,
        insights: normalizeDashboardInsights(raw?.insights || raw?.analysis_insights || []),
        nextAction: normalizeDashboardNextAction(raw?.next_action),
        focusInsight: normalizeDashboardFocusInsight(raw?.focus_insight),
        heroMetrics: normalizeDashboardHeroMetrics(raw?.hero_metrics),
        sinceLastVisit: normalizeSinceLastVisit(raw?.since_last_visit),
    };
};

export const refreshDashboardCache = async () => {
    try {
        await api.post('/api/v1/dashboard/refresh/');
    } catch (error) {
        console.warn('Dashboard cache refresh failed:', error);
    }
};

export const fetchDashboardData = async () => {
    try {
        const response = await api.get("/api/v1/dashboard/");
        return normalizeDashboardData(response.data);
    } catch (error) {
        if (error.response?.status === 401) {
            throw new Error("Please log in to view your dashboard");
        }
        throw error.response?.data || new Error("Failed to fetch dashboard data");
    }
};

export const fetchExternalGames = async (platform, username, gameType, numGames = 10) => {
    try {
        const effectiveGameType = gameType || "all";
        console.log('Fetching external games...', { platform, username, gameType: effectiveGameType, numGames });

        // Get user ID and token from localStorage
        let userId = null;
        let authHeader = null;

        try {
            const tokensString = localStorage.getItem('tokens');
            if (tokensString) {
                const tokens = JSON.parse(tokensString);
                if (tokens && tokens.access) {
                    // Set the authorization header
                    authHeader = `Bearer ${tokens.access}`;

                    // Get user ID from token
                    const decoded = JSON.parse(atob(tokens.access.split('.')[1]));
                    userId = decoded.user_id;
                    console.log('Using user ID from token:', userId);
                } else {
                    console.warn('Access token not found in tokens object');
                }
            } else {
                console.warn('No tokens found in localStorage');
            }
        } catch (e) {
            console.error('Error extracting token information:', e);
        }

        // Ensure we have authentication
        if (!authHeader) {
            throw new Error('Authentication required. Please log in again.');
        }

        // Make the API request with explicit Authorization header
        const response = await api.post("/api/v1/games/fetch/",
            {
            platform: platform.toLowerCase(),
            username: username.trim(),
            game_type: effectiveGameType,
                num_games: numGames,
                user_id: userId // Include user ID from token
            },
            {
                headers: {
                    'Authorization': authHeader
                }
            }
        );

        console.log('External games response:', response.data);

        if (response.data?.error) {
            throw new Error(response.data.error);
        }

        // Handle different response formats
        if (response.data?.data && Array.isArray(response.data.data)) {
            return response.data.data;
        } else if (response.data?.games && Array.isArray(response.data.games)) {
            return response.data.games;
        } else if (Array.isArray(response.data)) {
            return response.data;
        }

        // Return the original response if format is not recognized
        return response.data;
    } catch (error) {
        console.error('Fetch games error:', error);
        // Handle unauthorized errors
        if (error.response?.status === 401) {
            throw new Error("Authentication required. Please log in to fetch games.");
        }
        // Handle payment required errors
        if (error.response?.status === 402) {
            throw new Error("Insufficient credits. Please purchase more credits to fetch games.");
        }
        // Handle not found errors specifically to help debugging
        if (error.response?.status === 404) {
            throw new Error("The server returned a 404 error. The fetch games endpoint may not be configured properly.");
        }
        // Get the most descriptive error message possible
        const errorMessage =
            error.response?.data?.message ||
            error.response?.data?.error ||
            error.message ||
            "Failed to fetch external games";

        throw new Error(errorMessage);
    }
};

// Game analysis functions
export const analyzeSpecificGame = async (gameId) => {
    return analyzeSpecificGameService(gameId);
};

export const checkAnalysisStatus = async (gameId) => {
    return checkAnalysisStatusService(gameId);
};

export const fetchGameAnalysis = async (gameId) => {
    return fetchGameAnalysisService(gameId);
};

// DEPRECATED: Phase 1 task model — use createBatch() instead
// This endpoint uses the old /api/v1/games/batch-analyze/ task-based model.
// Kept for backward compatibility only. New code should use createBatch().
export const analyzeBatchGames = async (
    numGames,
    timeControl = 'all',
    includeAnalyzed = false,
    selectedGameIds = []
) => {
    try {
        const normalizedIds = Array.isArray(selectedGameIds)
            ? selectedGameIds.filter((id) => Number.isInteger(id))
            : [];

        const payload = {
            num_games: parseInt(numGames, 10),
            time_control: timeControl,
            include_analyzed: includeAnalyzed,
            depth: 20,
            use_ai: true
        };

        if (normalizedIds.length > 0) {
            payload.game_ids = normalizedIds;
            payload.num_games = normalizedIds.length;
        }

        const response = await api.post('/api/v1/games/batch-analyze/', {
            ...payload
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
        throw error.response?.data || new Error("Failed to start Batch Coach");
    }
};

// DEPRECATED: Phase 1 task model — use getBatchStatus() instead
// This endpoint uses the old /api/v1/games/batch-status/{taskId}/ task-based model.
// Kept for backward compatibility only. New code should use getBatchStatus().
export const checkBatchAnalysisStatus = async (taskId) => {
    try {
        if (!taskId) {
            throw new Error('No task ID provided');
        }

        const response = await api.get(`/api/v1/games/batch-status/${taskId}/`);

        if (!response.data) {
            throw new Error('Invalid response from server');
        }

        const { state, meta = {}, completed_games = [], failed_games = [], aggregate_metrics = {}, report_id = null } = response.data;

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
            aggregate_metrics,
            report_id
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
                error: error.message || 'Failed to check Batch Coach status',
                current: 0,
                total: 0,
                progress: 0,
                message: error.message || 'Failed to check Batch Coach status'
            },
            completed_games: [],
            failed_games: [],
            aggregate_metrics: null
        };
    }
};

/**
 * List the user's batch reports (Phase 2 /api/v1/batches/).
 * Falls back to legacy task-based endpoint if the new API is unavailable.
 */
export const fetchBatchReportHistory = async (limit = 20) => {
    try {
        const response = await api.get('/api/v1/batches/', {
            params: { limit }
        });

        if (response.data && Array.isArray(response.data.results)) {
            return response.data.results;
        }
    } catch (error) {
        if (error?.response?.status && error.response.status !== 404) {
            console.warn('Phase 2 batch history unavailable, trying legacy endpoint.', error);
        }
    }

    try {
        const legacy = await api.get('/api/v1/games/batch-reports/', {
            params: { limit }
        });

        if (!legacy.data || !Array.isArray(legacy.data.results)) {
            return [];
        }

        return legacy.data.results;
    } catch (error) {
        console.error('Error fetching batch report history:', error);
        throw error.response?.data || new Error('Failed to fetch batch report history');
    }
};

// DEPRECATED: Phase 1 task model — use getBatchReport() instead
// This endpoint fetches old batch reports using /api/v1/games/batch-reports/{reportId}/ task-based model.
// Kept for backward compatibility only. New code should use getBatchReport().
export const fetchBatchReportById = async (reportId) => {
    try {
        const response = await api.get(`/api/v1/games/batch-reports/${reportId}/`);

        if (!response.data || !response.data.report) {
            throw new Error('Invalid report response');
        }

        return response.data.report;
    } catch (error) {
        console.error('Error fetching batch report:', error);
        throw error.response?.data || new Error('Failed to fetch batch report');
    }
};

// ============================================================================
// Phase 2: Batch API (new resource model)
// ============================================================================
// These functions use the new /api/v1/batches/ resource model with proper
// separation of concerns: createBatch for submission, getBatchStatus for polling,
// getBatchReport for fetching the full analysis after completion.

/**
 * Create a new batch analysis job.
 *
 * @param {Object} options - Batch selection payload.
 * @param {Array<number>|null} options.gameIds - Array of saved game IDs.
 * @param {Array<string>|null} options.pgnList - Array of PGN strings.
 * @returns {Promise} Response with batch_id, task_id, status, and games_count
 *
 * Expected response shape (202):
 * {
 *   batch_id: "model-uuid",
 *   task_id: "celery-task-id",
 *   status: "pending",
 *   games_count: 10
 * }
 */
export const createBatch = async ({ gameIds = null, pgnList = null } = {}) => {
    try {
        const hasGameIds = Array.isArray(gameIds);
        const hasPgnList = Array.isArray(pgnList);

        if (!hasGameIds && !hasPgnList) {
            throw new Error('Either gameIds or pgnList must be provided');
        }

        const selectedCount = hasGameIds ? gameIds.length : pgnList.length;

        if (selectedCount < 5 || selectedCount > 30) {
            throw new Error('Batch size must be between 5 and 30 games');
        }

        const payload = hasGameIds
            ? { game_ids: gameIds }
            : { games: pgnList };

        const response = await api.post('/api/v1/batches/', payload);

        if (!response.data) {
            throw new Error('Invalid response from server');
        }

        const { batch_id, task_id, status, games_count } = response.data;

        if (!batch_id) {
            throw new Error('No batch ID received from server');
        }

        return {
            batch_id,
            task_id: task_id || batch_id,
            status: status || 'pending',
            games_count: games_count || selectedCount
        };
    } catch (error) {
        console.error('Error creating batch:', error);
        throw error.response?.data || new Error('Failed to create batch');
    }
};

/**
 * Poll the status of an ongoing or completed batch.
 *
 * @param {string} batchId - The batch ID from createBatch()
 * @returns {Promise} Response with status, progress, completed/failed counts
 *
 * Expected response shape (200):
 * {
 *   batch_id: "model-uuid",
 *   task_id: "celery-task-id",
 *   status: "pending" | "in_progress" | "completed" | "partial" | "failed",
 *   games_count: 10,
 *   completed_games: 8,
 *   failed_games: 2,
 *   progress: "8/10 games analyzed",
 *   errors: [
 *     { game_id: "game_0", message: "Invalid PGN" },
 *     ...
 *   ]
 * }
 */
export const getBatchStatus = async (batchId) => {
    try {
        if (!batchId) {
            throw new Error('Batch ID is required');
        }

        const response = await api.get(`/api/v1/batches/${batchId}/status/`);

        if (!response.data) {
            throw new Error('Invalid response from server');
        }

        const {
            batch_id,
            task_id,
            status = 'failed',
            games_count = 0,
            completed_games = 0,
            failed_games = 0,
            progress = '',
            errors = []
        } = response.data;

        return {
            batch_id: batch_id || batchId,
            task_id,
            status,
            games_count,
            completed_games,
            failed_games,
            progress,
            errors
        };
    } catch (error) {
        console.error('Error checking batch status:', error);
        throw error.response?.data || new Error('Failed to check batch status');
    }
};

/**
 * Fetch the complete analysis report for a batch.
 * Call only after getBatchStatus() returns status !== pending/in_progress.
 *
 * @param {string} batchId - The batch ID
 * @returns {Promise} Full report payload, or 202 if still in progress
 *
 * Expected response shapes:
 *
 * While in progress (202):
 * {
 *   status: "pending" | "in_progress",
 *   message: "Analysis in progress"
 * }
 *
 * On completion (200):
 * {
 *   id: "model-uuid",
 *   task_id: "celery-task-id",
 *   status: "completed" | "partial" | "failed",
 *   games_count: 10,
 *   batch_summary: {
 *     games_analyzed: 10,
 *     overall_accuracy: 0.85,
 *     date_range: "2025-01-01 to 2025-01-10",
 *     win_loss_draw: { wins: 6, losses: 2, draws: 2 },
 *     phase_performance: { opening: 0.88, middlegame: 0.82, endgame: 0.80 },
 *     recurring_weaknesses: [ ... ]
 *   },
 *   per_game_results: [
 *     {
 *       game_id: "game_0",
 *       total_moves: 40,
 *       result: "1-0",
 *       player_color: "white",
 *       opening_name: "Italian Game",
 *       phase_breakdown: { ... },
 *       move_quality: { blunder: 0, mistake: 1, inaccuracy: 4 },
 *       critical_moments: [ ... ]
 *     },
 *     ...
 *   ],
 *   coaching_report: {
 *     executive_summary: "...",
 *     coaching_narrative: { opening: "...", middlegame: "...", endgame: "..." },
 *     top_3_priorities: [
 *       {
 *         rank: 1,
 *         title: "Tactical Vision",
 *         why_it_matters: "...",
 *         how_to_fix: "...",
 *         specific_drill: "...",
 *         estimated_study_hours: 10
 *       },
 *       ...
 *     ],
 *     training_plan: {
 *       week_1: "...",
 *       week_2: "...",
 *       week_3: "...",
 *       week_4: "..."
 *     },
 *     one_thing_to_do_today: "..."
 *   } | null,  // null when status = partial (coaching generation failed)
 *   created_at: "2025-01-20T10:00:00Z",
 *   updated_at: "2025-01-20T10:15:00Z"
 * }
 *
 * On failure (200):
 * {
 *   status: "failed",
 *   message: "Analysis failed — insufficient games succeeded"
 * }
 */
/**
 * Regenerate coaching narrative only (reuses saved Stockfish analysis).
 *
 * POST /api/v1/batches/{batchId}/regenerate-coaching/
 */
/**
 * GET /api/v1/batches/{batchId}/compare/?other=<id|previous>
 */
/**
 * POST /api/v1/batches/{batchId}/share/
 */
export const enableBatchShare = async (batchId) => {
    try {
        const response = await api.post(`/api/v1/batches/${batchId}/share/`);
        return response.data;
    } catch (error) {
        throw error.response?.data || new Error('Failed to enable batch sharing');
    }
};

/**
 * DELETE /api/v1/batches/{batchId}/share/
 */
export const revokeBatchShare = async (batchId) => {
    try {
        const response = await api.delete(`/api/v1/batches/${batchId}/share/`);
        return response.data;
    } catch (error) {
        throw error.response?.data || new Error('Failed to revoke batch sharing');
    }
};

/**
 * GET /api/v1/batches/public/{shareToken}/report/ (no auth)
 */
export const getPublicBatchReport = async (shareToken) => {
    try {
        const { default: axios } = await import('axios');
        const { API_URL } = await import('../config');
        const base = (API_URL || '').replace(/\/$/, '');
        const response = await axios.get(`${base}/api/v1/batches/public/${shareToken}/report/`);
        return response.data;
    } catch (error) {
        throw error.response?.data || new Error('Shared report not found');
    }
};

export const fetchBatchCompare = async (batchId, other = 'previous') => {
    try {
        const response = await api.get(`/api/v1/batches/${batchId}/compare/`, {
            params: { other }
        });
        return response.data;
    } catch (error) {
        const payload = error.response?.data || { detail: 'Failed to load batch comparison.' };
        const err = new Error(payload.detail || 'Failed to load batch comparison.');
        err.status = error.response?.status;
        err.response = error.response;
        throw err;
    }
};

export const regenerateBatchCoaching = async (batchId) => {
    try {
        if (!batchId) {
            throw new Error('Batch ID is required');
        }

        const response = await api.post(`/api/v1/batches/${batchId}/regenerate-coaching/`);

        if (!response.data) {
            throw new Error('Invalid response from server');
        }

        return response.data;
    } catch (error) {
        console.error('Error regenerating batch coaching:', error);
        throw error.response?.data || new Error('Failed to regenerate coaching');
    }
};

export const getBatchReport = async (batchId) => {
    try {
        if (!batchId) {
            throw new Error('Batch ID is required');
        }

        const response = await api.get(`/api/v1/batches/${batchId}/report/`);

        if (!response.data) {
            throw new Error('Invalid response from server');
        }

        const {
            id,
            task_id,
            status,
            games_count = 0,
            batch_summary = null,
            per_game_results = [],
            coaching_report = null,
            failed_games = [],
            errors = [],
            created_at,
            updated_at,
            message,
            credits_refunded,
            credits_refunded_amount
        } = response.data;

        // Return full structure with all fields present
        return {
            id: id || batchId,
            task_id,
            status,
            games_count,
            batch_summary,
            per_game_results,
            coaching_report, // may be null when status = partial
            failed_games: Array.isArray(failed_games) ? failed_games : [],
            errors: Array.isArray(errors) ? errors : [],
            created_at,
            updated_at,
            message, // included for error cases
            credits_refunded: Boolean(credits_refunded),
            credits_refunded_amount: credits_refunded_amount ?? null
        };
    } catch (error) {
        console.error('Error fetching batch report:', error);
        throw error.response?.data || new Error('Failed to fetch batch report');
    }
};

// Convenience wrapper to re-run only failed games by passing game IDs or PGNs
export const retryFailedGames = async ({ gameIds = null, pgnList = null } = {}) => {
    // Behaves same as createBatch but exists for semantic clarity in UI
    return createBatch({ gameIds, pgnList });
};

// ============================================================================

// User profile functions
export const getUserProfile = async () => {
    try {
        const response = await api.get('/api/v1/profile/');
        return response.data;
    } catch (error) {
        console.error('Error fetching profile data:', error);
        throw error.response?.data || new Error("Failed to fetch profile data");
    }
};

export const updateUserProfile = async (profileData) => {
    try {
        const response = await api.patch("/api/v1/profile/update/", profileData);
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
        const response = await api.post("/api/v1/auth/reset-password/", { email });
        if (response.data?.status === 'error') {
            throw new Error(
                response.data.message ||
                "Password reset email is temporarily unavailable. Please try again later."
            );
        }
        return response.data;
    } catch (error) {
        console.error('Password reset request error:', error);
        if (error.response?.data?.message) {
            throw new Error(error.response.data.message);
        }
        if (error.message) {
            throw error;
        }
        throw new Error("Failed to send password reset link. Please try again later.");
    }
};

export const resetPassword = async (uid, token, newPassword) => {
    try {
        const response = await api.post("/api/v1/auth/reset-password/confirm/", {
            uid,
            token,
            new_password: newPassword
        });
        return response.data;
    } catch (error) {
        console.error('Password reset error:', error);
        if (error.response?.data?.message) {
            throw new Error(error.response.data.message);
        }
        throw new Error("Failed to reset password. The link may have expired.");
    }
};

// Credit system functions
export const getCredits = async () => {
    try {
        const response = await api.get('/api/v1/credits/');
        return response.data.credits;
    } catch (error) {
        console.error('Error fetching credits:', error);
        throw error.response?.data || new Error("Failed to fetch credits");
    }
};

export const purchaseCredits = async (packageId) => {
    try {
        const response = await api.post("/api/v1/purchase-credits/", { package_id: packageId });
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
        const response = await api.post("/api/v1/confirm-purchase/", { payment_id: paymentId });
        return response.data;
    } catch (error) {
        if (error.response?.status === 400) {
            throw new Error("Invalid payment confirmation");
        }
        throw error.response?.data || new Error("Failed to confirm purchase");
    }
};

const defaultPerformanceStats = () => ({
    bullet: { games: 0, winRate: 0, drawRate: 0, lossRate: 0 },
    blitz: { games: 0, winRate: 0, drawRate: 0, lossRate: 0 },
    rapid: { games: 0, winRate: 0, drawRate: 0, lossRate: 0 },
    classical: { games: 0, winRate: 0, drawRate: 0, lossRate: 0 },
});

const normalizeProfileData = (raw) => {
    const nestedProfile = raw?.data?.profile || raw?.profile || {};
    const nestedUser = raw?.data?.user || {};

    return {
        ...raw,
        username: raw?.username ?? nestedUser.username,
        email: raw?.email ?? nestedUser.email,
        credits: raw?.credits ?? nestedProfile.credits ?? 0,
        chess_com_username: raw?.chess_com_username ?? nestedProfile.chess_com_username ?? '',
        chesscom_username:
            raw?.chesscom_username ??
            raw?.chess_com_username ??
            nestedProfile.chess_com_username ??
            '',
        lichess_username: raw?.lichess_username ?? nestedProfile.lichess_username ?? '',
        total_games: raw?.total_games ?? 0,
        win_rate: raw?.win_rate ?? 0,
        performance_stats: raw?.performance_stats ?? defaultPerformanceStats(),
        time_control_distribution: raw?.time_control_distribution ?? {
            bullet: 0,
            blitz: 0,
            rapid: 0,
            classical: 0,
        },
        achievements: Array.isArray(raw?.achievements) ? raw.achievements : [],
    };
};

export const fetchProfileData = async () => {
    try {
        const response = await api.get('/api/v1/profile/');
        return normalizeProfileData(response.data);
    } catch (error) {
        console.error('Error fetching profile data:', error);
        throw error;
    }
};

export async function checkMultipleAnalysisStatuses(gameIds) {
    return checkMultipleAnalysisStatusesService(gameIds);
}
