import React, { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import {
  analyzeSpecificGame,
  checkAnalysisStatus,
  classifyAnalysisPollingStatus,
  computeNextPollDelay,
  fetchGameAnalysis,
  hasRenderableAnalysisData,
  isAnalysisInFlight,
  restartAnalysis,
  shouldPollStatus,
} from '../services/gameAnalysisService';
import GameAnalysisResults from './GameAnalysisResults';
import BatchContextBanner from './singlegame/BatchContextBanner';
import AnalyzeGameConfirmDialog from './AnalyzeGameConfirmDialog';
import { parseSingleGameAnalysisSearch } from '../utils/singleGameAnalysisLinks';
import { humanizeAnalysisStatusMessage } from '../utils/singleGameAnalysisStatus';
import { trackSingleGameEvent } from '../utils/marketingAnalytics';
import { UserContext } from '../contexts/UserContext';
import api from '../services/api';
import './SingleGameAnalysis.css';
import { useTheme } from '../context/ThemeContext';
import { FaInfoCircle, FaSpinner, FaExclamationTriangle, FaClock, FaCheckCircle } from 'react-icons/fa';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import LinearProgress from '@mui/material/LinearProgress';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';

// Format time in MM:SS format
const formatTime = (seconds) => {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds < 10 ? '0' : ''}${remainingSeconds}`;
};

// Progress bar component that shows remaining time
const ProgressBar = ({ progress, isDarkMode, startTime }) => {
  const progressRef = useRef(progress);
  const [remainingTime, setRemainingTime] = useState('');

  // Update remaining time calculation whenever progress changes
    useEffect(() => {
    if (progress <= 0 || progress >= 100 || !startTime) return;

    progressRef.current = progress;

    // Calculate estimated time remaining
    const elapsedMs = Date.now() - startTime;
    const progressPercent = progress / 100;

    // Avoid division by zero
    if (progressPercent <= 0) return;

    const totalEstimatedMs = elapsedMs / progressPercent;
    const remainingMs = totalEstimatedMs - elapsedMs;

    // Convert to minutes and seconds
    const remainingMinutes = Math.floor(remainingMs / 60000);
    const remainingSeconds = Math.floor((remainingMs % 60000) / 1000);

    setRemainingTime(
      `${remainingMinutes}:${remainingSeconds < 10 ? '0' : ''}${remainingSeconds}`
    );
  }, [progress, startTime]);

    return (
    <Box className={`p-6 rounded-lg shadow-md ${isDarkMode ? 'bg-gray-800' : 'bg-white'}`}>
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
        <Typography variant="h6" className={isDarkMode ? 'text-white' : 'text-gray-800'}>
          Analysis Progress
        </Typography>
        {progress > 0 && progress < 100 && (
          <Box display="flex" alignItems="center">
            <FaClock className={`mr-2 ${isDarkMode ? 'text-blue-400' : 'text-blue-600'}`} />
            <Typography variant="body2" className={isDarkMode ? 'text-gray-300' : 'text-gray-600'}>
              Est. remaining: {remainingTime || 'Calculating...'}
            </Typography>
          </Box>
        )}
      </Box>

      <Box position="relative" mb={1}>
        <LinearProgress
          variant="determinate"
          value={progress}
          sx={{
            height: 10,
            borderRadius: 5,
            backgroundColor: isDarkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
            '& .MuiLinearProgress-bar': {
              backgroundColor: isDarkMode ? '#4f46e5' : '#3b82f6'
            }
          }}
        />
      </Box>

      <Box display="flex" justifyContent="space-between">
        <Typography variant="body2" className={isDarkMode ? 'text-gray-400' : 'text-gray-500'}>
          {progress === 0 ? 'Starting analysis...' : ''}
        </Typography>
        <Typography variant="body2" className={isDarkMode ? 'text-gray-300' : 'text-gray-700'} fontWeight="medium">
          {progress}%
        </Typography>
      </Box>
    </Box>
  );
};

// Information component to explain analysis process
const AnalysisInfo = ({ isDarkMode, ceyleryNotRunning }) => (
  <Card
    variant="outlined"
    className={`shadow-md rounded-lg p-4 mb-6`}
    sx={{
      backgroundColor: isDarkMode ? '#1f2937' : '#ffffff',
      color: isDarkMode ? '#f9fafb' : '#111827',
      borderColor: isDarkMode ? '#374151' : '#e5e7eb'
    }}
  >
    <CardContent>
      <Box display="flex" alignItems="flex-start" mb={2}>
        <FaInfoCircle size={24} className={`mt-1 mr-3 ${isDarkMode ? 'text-blue-400' : 'text-blue-600'}`} />
        <Box>
          <Typography
            variant="h6"
            gutterBottom
            sx={{ color: isDarkMode ? '#f9fafb' : '#111827' }}
          >
            Analysis in Progress
          </Typography>
          <Typography
            variant="body2"
            sx={{ color: isDarkMode ? '#d1d5db' : '#4b5563' }}
          >
            Our chess engine is analyzing your game moves. This typically takes 2-3 minutes to complete.
          </Typography>
        </Box>
      </Box>

      <Box ml={6}>
        <Typography
          variant="subtitle2"
          gutterBottom
          sx={{ color: isDarkMode ? '#e5e7eb' : '#374151' }}
        >
          What's happening now:
        </Typography>
        <Box sx={{ color: isDarkMode ? '#d1d5db' : '#4b5563' }}>
          <ul className="list-disc pl-5 space-y-1">
            <li>Analyzing each move with Stockfish 16 (3500+ ELO)</li>
            <li>Finding missed tactics and better alternatives</li>
            <li>Identifying key moments where the game shifted</li>
            <li>Evaluating opening, middlegame and endgame play</li>
            <li>Generating personalized improvement recommendations</li>
          </ul>
        </Box>

        <Typography
          variant="body2"
          className="mt-3"
          sx={{ color: isDarkMode ? '#d1d5db' : '#4b5563' }}
        >
          When complete, you'll receive a detailed analysis of your game with move-by-move evaluations
          and provide improvement suggestions.
        </Typography>

        {ceyleryNotRunning && (
          <Box
            className="mt-4 p-3 rounded-md border"
            sx={{
              backgroundColor: isDarkMode ? 'rgba(234, 88, 12, 0.2)' : 'rgba(254, 215, 170, 0.5)',
              borderColor: isDarkMode ? 'rgb(154, 52, 18)' : 'rgb(234, 88, 12)',
              color: isDarkMode ? 'rgb(254, 215, 170)' : 'rgb(154, 52, 18)'
            }}
          >
            <Box display="flex" alignItems="flex-start">
              <FaExclamationTriangle className="mt-1 mr-2" />
              <Box>
                <Typography
                  variant="subtitle2"
                  gutterBottom
                  sx={{ fontWeight: 'bold', marginBottom: '4px' }}
                >
                  System Notification
                </Typography>
                <Typography variant="body2">
                  We've detected some temporary server issues that may affect your analysis experience:
                </Typography>
                <ul className="list-disc pl-5 mt-2 space-y-1">
                  <li>The analysis is still running in the background</li>
                  <li>The progress bar shows an estimate of the analysis time</li>
                  <li>Results may be limited due to database or cache connectivity issues</li>
                  <li>You can try analyzing the game again later if results are incomplete</li>
                </ul>
              </Box>
            </Box>
          </Box>
        )}
      </Box>
    </CardContent>
  </Card>
);

// Error and retry component
const ErrorWithRetry = ({ error, onRetry, onBack, insufficientCredits = false, onBuyCredits }) => (
  <div className="flex flex-col items-center justify-center h-full">
    <div className="p-6 bg-red-50 dark:bg-red-900/20 rounded-lg shadow-md text-center max-w-xl w-full">
      <FaExclamationTriangle className="mx-auto text-red-500 text-4xl mb-4" />
      <h2 className="text-xl font-bold text-red-700 dark:text-red-400 mb-4">
        {error || "An error occurred during analysis"}
      </h2>
      <p className="mb-6 text-gray-700 dark:text-gray-300">
        {insufficientCredits
          ? 'Add credits to run a depth-20 deep review, or open this game from a Batch Coach citation for a free waiver when enabled.'
          : "We couldn't complete the analysis of your game. This could be due to server load or an issue with the game data."}
      </p>
      <div className="flex flex-col md:flex-row space-y-3 md:space-y-0 md:space-x-3 justify-center">
        {insufficientCredits && onBuyCredits ? (
          <button
            onClick={onBuyCredits}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md font-medium transition"
          >
            Get credits
          </button>
        ) : (
          <button
            onClick={onRetry}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium transition"
          >
            Try Again
          </button>
        )}
        <button
          onClick={onBack}
          className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600
          text-gray-800 dark:text-gray-200 rounded-md font-medium transition"
        >
          Back to Games
        </button>
            </div>
                    </div>
                </div>
);

// No data error component
const NoDataError = ({ gameId, onRetry, onBack }) => (
  <div className="flex flex-col items-center justify-center h-full p-8">
    <div className="p-6 bg-amber-50 dark:bg-amber-900/20 rounded-lg shadow-md text-center max-w-xl w-full">
      <FaExclamationTriangle className="mx-auto text-amber-500 text-4xl mb-4" />
      <h2 className="text-xl font-bold text-amber-700 dark:text-amber-400 mb-4">
        No Analysis Data Available
      </h2>
      <p className="mb-6 text-gray-700 dark:text-gray-300">
        We couldn't find any analysis data for this game. This could be because:
      </p>
      <ul className="text-left list-disc pl-8 mb-6 text-gray-700 dark:text-gray-300">
        <li>The analysis task failed to complete</li>
        <li>There was an issue with the chess engine</li>
        <li>The game data format is unsupported</li>
      </ul>
      <div className="flex flex-col md:flex-row space-y-3 md:space-y-0 md:space-x-3 justify-center">
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium transition"
        >
          Try Analyzing Again
        </button>
        <button
          onClick={onBack}
          className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600
          text-gray-800 dark:text-gray-200 rounded-md font-medium transition"
        >
          Back to Games
        </button>
                </div>
            </div>
        </div>
    );

const SingleGameAnalysis = () => {
  const { gameId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { isDarkMode } = useTheme();
  const { credits } = React.useContext(UserContext);
  const { batchId, move, priority } = parseSingleGameAnalysisSearch(location.search);
  const [showReanalyzeConfirm, setShowReanalyzeConfirm] = useState(false);
  const [confirmingReanalyze, setConfirmingReanalyze] = useState(false);
  const trackedViewRef = useRef(false);

  // State variables
  const [analysisData, setAnalysisData] = useState(null);
    const [loading, setLoading] = useState(true);
  const [analysisError, setAnalysisError] = useState(null);
  const [insufficientCreditsError, setInsufficientCreditsError] = useState(false);
  const [authError, setAuthError] = useState(false);
  const [progress, setProgress] = useState(0);
  const [loadingMessage, setLoadingMessage] = useState('Starting analysis...');
  const [pollingFailed, setPollingFailed] = useState(false);
  const [analysisStartTime, setAnalysisStartTime] = useState(Date.now());
  const isCeleryRunning = true;
  const [elapsedTime, setElapsedTime] = useState(0);
  const [statusMessage, setStatusMessage] = useState("Initializing analysis...");
  const [overdueMessage, setOverdueMessage] = useState(null);
  const [singleGameSendsEmail, setSingleGameSendsEmail] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api.get('/api/v1/public/site-config/')
      .then((response) => {
        if (!cancelled && response?.data) {
          setSingleGameSendsEmail(response.data.single_game_sends_completion_email !== false);
        }
      })
      .catch(() => {
        /* keep default */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Use refs to keep track of intervals and state across renders
  const progressIntervalRef = useRef(null);
  const statusCheckIntervalRef = useRef(null);
    const hasStartedRef = useRef(false);
  const hasExceededMaxRetries = useRef(false);
  const hasAttemptedDirectFetch = useRef(false);
  const hasAttemptedRecovery = useRef(false);
  const isFetchingAnalysisRef = useRef(false);
  const pollingErrorCount = useRef(0);
  const analysisCompleted = useRef(false);
  const analysisErrorRef = useRef(false);
  const pollingTimeoutRef = useRef(null);
  const pollDelayRef = useRef(5000);
  const activeTaskIdRef = useRef(null);
  const timeoutIds = useRef([]);
  const POLL_MIN_DELAY = 5000;
  const POLL_MAX_DELAY = 30000;

  const scheduleStatusPoll = (delay = POLL_MIN_DELAY) => {
    if (analysisCompleted.current || isFetchingAnalysisRef.current || analysisErrorRef.current) {
      return;
    }

    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
    }

    pollingTimeoutRef.current = setTimeout(async () => {
      await pollForAnalysisStatus();

      if (!analysisCompleted.current && !analysisErrorRef.current) {
        scheduleStatusPoll(pollDelayRef.current);
      }
    }, delay);
  };

  // Poll for analysis status
  const pollForAnalysisStatus = async () => {
    if (!gameId) return;
    if (analysisCompleted.current || isFetchingAnalysisRef.current) return;

    try {
      setPollingFailed(false);
      const statusResponse = await checkAnalysisStatus(gameId, {
        taskId: activeTaskIdRef.current,
      });
      console.log(`Analysis status for game ${gameId}:`, statusResponse);
      pollDelayRef.current = computeNextPollDelay({
        currentDelay: pollDelayRef.current,
        minDelay: POLL_MIN_DELAY,
        maxDelay: POLL_MAX_DELAY,
        hadError: false,
      });

      const classification = classifyAnalysisPollingStatus(statusResponse.status, statusResponse.progress);

      // If we have a complete analysis, fetch it
      if (classification.isSuccess) {
        clearAllIntervals();
        setLoadingMessage('Analysis complete! Loading results...');
        analysisCompleted.current = true;
        await fetchAnalysisData();
        return;
      }

      if (classification.isTerminalFailure) {
        clearAllIntervals();
        analysisErrorRef.current = true;
        setLoading(false);

        if (statusResponse.status === 'AUTH_ERROR') {
          setAuthError(true);
          return;
        }

        setAnalysisError(statusResponse.message || 'Analysis failed. Please try again.');
        return;
      }

      // Verify we should continue polling
      if (!shouldPollStatus(statusResponse.status, statusResponse.progress)) {
        clearAllIntervals();
        return;
      }

      // Update progress
      const progressValue = parseInt(statusResponse.progress) || 0;
      setProgress(progressValue);

      if (statusResponse.message) {
        const humanized = humanizeAnalysisStatusMessage(statusResponse.message, progressValue);
        setStatusMessage(humanized.status);
        setLoadingMessage(humanized.detail);
      } else if (progressValue < 30) {
        setStatusMessage('Reviewing your moves');
        setLoadingMessage('Stockfish depth 20 is analyzing each position. You can leave this page — we will keep working.');
      } else if (progressValue < 60) {
        setStatusMessage('Calculating patterns');
        setLoadingMessage('Measuring accuracy, swings, and time use. Check Games for live progress.');
      } else if (progressValue < 90) {
        setStatusMessage('Writing your coaching summary');
        setLoadingMessage('Generating takeaway, critical moments, and practice notes.');
      } else {
        setStatusMessage('Almost ready');
        setLoadingMessage('Finalizing your depth-20 report…');
      }

      // Handle stale progress - if we've been at the same progress for too long, try a direct fetch
      const prevProgress = parseInt(localStorage.getItem(`last_known_progress_${gameId}`)) || 0;
      const prevProgressTime = parseInt(localStorage.getItem(`last_progress_update_${gameId}`)) || 0;
      const currentTime = Date.now();

      // Check if progress has been the same for more than 30 seconds
      if (prevProgress === progressValue &&
          prevProgressTime > 0 &&
          (currentTime - prevProgressTime) > 30000 &&
          !hasAttemptedRecovery.current) {
        hasAttemptedRecovery.current = true;
        console.log('Progress appears stalled, attempting direct fetch to recover');
        try {
          await fetchAnalysisData();
        } catch (err) {
          console.error('Recovery fetch failed', err);
          // Try restarting the analysis if we can't fetch and progress is stalled
          if (progressValue < 90) {
            setLoadingMessage('Analysis appears stalled. Attempting to recover...');
            try {
              await startAnalysis();
              setLoadingMessage('Analysis restarted successfully.');
              hasAttemptedRecovery.current = false;
            } catch (startErr) {
              console.error('Failed to restart analysis', startErr);
              setLoadingMessage('Unable to recover analysis. You may need to try again.');
            }
          }
        }
      }

      // Update the last known progress
      localStorage.setItem(`last_known_progress_${gameId}`, String(progressValue));
      localStorage.setItem(`last_progress_update_${gameId}`, String(currentTime));

    } catch (error) {
      console.error('Error polling for analysis status:', error);
      pollingErrorCount.current += 1;
      pollDelayRef.current = computeNextPollDelay({
        currentDelay: pollDelayRef.current,
        minDelay: POLL_MIN_DELAY,
        maxDelay: POLL_MAX_DELAY,
        hadError: true,
      });

      // If we encounter several polling errors, try to fetch the analysis directly
      if (pollingErrorCount.current >= 3 && !hasAttemptedDirectFetch.current) {
        hasAttemptedDirectFetch.current = true;
        setLoadingMessage('Having trouble checking status. Attempting to fetch results directly...');
        try {
          await fetchAnalysisData();
        } catch (fetchError) {
          console.error('Direct fetch after polling errors failed:', fetchError);
          // If direct fetch fails and we've had multiple polling errors, show the recovery UI
          if (pollingErrorCount.current >= 5) {
            setPollingFailed(true);
          }
        }
      }
    }
  };

  // Function to clear all intervals
  const clearAllIntervals = () => {
    if (statusCheckIntervalRef.current) {
      clearInterval(statusCheckIntervalRef.current);
      statusCheckIntervalRef.current = null;
    }
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }

    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
      pollingTimeoutRef.current = null;
    }

    // Clear all timeout IDs
    timeoutIds.current.forEach(timeoutId => {
      clearTimeout(timeoutId);
    });
    timeoutIds.current = [];
  };

  useEffect(() => {
    analysisErrorRef.current = Boolean(analysisError);
    if (analysisErrorRef.current) {
      clearAllIntervals();
    }
  }, [analysisError]);

  // Handle analysis restart
  const handleRestartAnalysis = async () => {
    try {
      setLoading(true);
      setAnalysisError(null);
      setInsufficientCreditsError(false);
      analysisErrorRef.current = false;
      setPollingFailed(false);
      setLoadingMessage('Restarting analysis...');

      // Use the restart analysis function to force a new analysis
      const response = await restartAnalysis(gameId);

      if (response && response.success) {
        // Reset all analysis state
        setProgress(0);
        setAnalysisData(null);
        setAnalysisStartTime(Date.now());
        hasAttemptedDirectFetch.current = false;
        hasAttemptedRecovery.current = false;
        pollingErrorCount.current = 0;
        hasExceededMaxRetries.current = false;
        analysisCompleted.current = false;
        pollDelayRef.current = POLL_MIN_DELAY;

        // Start polling again
        scheduleStatusPoll(POLL_MIN_DELAY);
      } else {
        setAnalysisError('Failed to restart analysis. Please try again.');
        setLoading(false);
      }
    } catch (error) {
      console.error('Error restarting analysis:', error);
      setAnalysisError(error.message || 'Failed to restart analysis. Please try again.');
      setLoading(false);
    }
  };

  // Function to fetch analysis data
  const fetchAnalysisData = async () => {
    if (isFetchingAnalysisRef.current) {
      return false;
    }

    isFetchingAnalysisRef.current = true;
    setLoadingMessage('Retrieving analysis results...');
    try {
      const data = await fetchGameAnalysis(gameId, 0, {
        batchId,
        move,
        priority,
        ignoreStoredError: Boolean(activeTaskIdRef.current),
      });

      // Check for error message in the data itself
      if (data.error) {
        console.warn('Error returned in analysis data:', data.error);
        // While the current task is still queued or running, keep polling — don't surface stale errors.
        const inFlight = data.status === 'PENDING'
          || data.status === 'STARTED'
          || data.status === 'PROCESSING'
          || data.status === 'PROGRESS'
          || data.status === 'IN_PROGRESS';
        if (inFlight && activeTaskIdRef.current) {
          isFetchingAnalysisRef.current = false;
          return false;
        }
        setAnalysisError(data.error);
        setLoading(false);
        localStorage.removeItem(`analysis_complete_${gameId}`);
        isFetchingAnalysisRef.current = false;
        return false;
      }

      if (isAnalysisInFlight(data) || (activeTaskIdRef.current && !hasRenderableAnalysisData(data))) {
        console.log('Analysis still in progress, continuing to poll');
        isFetchingAnalysisRef.current = false;
        return false;
      }

      if (hasRenderableAnalysisData(data)) {
        console.log('Analysis data retrieved successfully:', data);
        setAnalysisData(data);
        setLoading(false);
        analysisCompleted.current = true;
        localStorage.setItem(`analysis_complete_${gameId}`, 'true');
        isFetchingAnalysisRef.current = false;
        return true;
      }

      console.warn('Retrieved data structure is invalid:', data);
      setAnalysisError('The analysis data structure is invalid or incomplete. Please try again.');
      setLoading(false);
      isFetchingAnalysisRef.current = false;
      return false;
        } catch (error) {
      console.error('Error fetching analysis data:', error);
      setAnalysisError(error.message || 'Failed to load analysis data');
            setLoading(false);
      isFetchingAnalysisRef.current = false;
      return false;
    }
  };

  useEffect(() => {
    if (!analysisData || loading || trackedViewRef.current) {
      return;
    }
    trackedViewRef.current = true;
    trackSingleGameEvent(batchId ? 'single_game_from_batch' : 'single_game_view', {
      game_id: gameId,
      batch_id: batchId,
      move,
      priority,
    });
  }, [analysisData, loading, batchId, gameId, move, priority]);

  const startAnalysis = async ({ forceReanalyze = false } = {}) => {
    try {
      setLoading(true);
      setProgress(0);
      setAnalysisData(null);
      setAnalysisError(null);
      setInsufficientCreditsError(false);
      analysisErrorRef.current = false;
      setAuthError(false);
      setPollingFailed(false);
      setLoadingMessage('Your review runs in the background — feel free to leave and check Games later.');
      setStatusMessage('Starting depth-20 review…');

      // Reset refs
      hasAttemptedDirectFetch.current = false;
      hasAttemptedRecovery.current = false;
      pollingErrorCount.current = 0;
      hasExceededMaxRetries.current = false;
      analysisCompleted.current = false;
      isFetchingAnalysisRef.current = false;
      pollDelayRef.current = POLL_MIN_DELAY;
      activeTaskIdRef.current = null;

      // Clear all existing intervals and timeouts
      clearAllIntervals();

      // Reset localStorage flags
      localStorage.removeItem(`analysis_complete_${gameId}`);
      localStorage.removeItem(`analysis_error_${gameId}`);
      localStorage.removeItem(`last_known_progress_${gameId}`);
      localStorage.removeItem(`last_progress_update_${gameId}`);

      // Set the analysis start time for timing calculations
      setAnalysisStartTime(Date.now());

      console.log(`Starting analysis for game ${gameId}`);
      const response = await analyzeSpecificGame(gameId, {
        batchId: forceReanalyze ? null : batchId,
        move,
        priority,
        fromBatch: Boolean(batchId) && !forceReanalyze,
        forceReanalyze,
      });
      console.log('Analysis started response:', response);

      if (response && response.success) {
        if (response.task_id) {
          activeTaskIdRef.current = response.task_id;
        }
        setLoadingMessage('Queued or running — no need to keep this tab open. We will load results when ready.');
        setStatusMessage('Depth-20 review started');

        // Set an initial delay before polling to give task time to register
        const initialDelayId = setTimeout(() => {
          // Start polling
          scheduleStatusPoll(POLL_MIN_DELAY);
        }, 3000);

        timeoutIds.current.push(initialDelayId);

        // Set a backup timeout to prevent infinite loading
        const timeoutDuration = 5 * 60 * 1000; // 5 minutes
        const timeoutId = setTimeout(() => {
          if (!analysisCompleted.current) {
            hasExceededMaxRetries.current = true;
            console.log('Analysis timeout reached, attempting direct fetch');
            fetchAnalysisData()
              .then(success => {
                if (!success) {
                  setPollingFailed(true);
                  setLoadingMessage('Analysis timed out. Please try again.');
                }
              })
              .catch(() => {
                setPollingFailed(true);
                setLoadingMessage('Analysis timed out. Please try again.');
              });
          }
        }, timeoutDuration);

        timeoutIds.current.push(timeoutId);

      } else {
        setAnalysisError('Failed to start analysis. Please try again.');
        setLoading(false);
      }
    } catch (error) {
      console.error('Error starting analysis:', error);

      if (error.authError || error.auth_error) {
        setAuthError(true);
      } else if (error.insufficientCredits) {
        setInsufficientCreditsError(true);
        setAnalysisError(error.message || 'Insufficient credits to run a deep review.');
      } else {
        setAnalysisError(error.message || 'Failed to start analysis. Please try again.');
      }

      setLoading(false);
    }
  };

  // Track elapsed time and show overdue message if needed
  useEffect(() => {
    if (!loading) return;

    const elapsedTimeInterval = setInterval(() => {
      setElapsedTime(prev => {
        const newElapsedTime = prev + 1;
        // Set overdue message if analysis is taking too long (now 150 seconds - 2.5 minutes)
        if (newElapsedTime > 150 && progress < 95) { // 2.5 minutes
          setOverdueMessage("Analysis is taking longer than expected. The system might be busy, but we're still working on it!");
        }
        return newElapsedTime;
      });
    }, 1000);

    return () => clearInterval(elapsedTimeInterval);
  }, [loading, progress]);

  // Initialize analysis on component mount
  useEffect(() => {
    if (gameId && !hasStartedRef.current) {
      hasStartedRef.current = true;

      // Check if analysis was already completed
      const isComplete = localStorage.getItem(`analysis_complete_${gameId}`) === 'true';
      if (isComplete) {
        console.log(`Analysis previously marked as complete for game ${gameId}, verifying data...`);
        // We'll now verify that the analysis really has valid data
        fetchAnalysisData()
          .then(success => {
            if (!success) {
              console.log('Cached analysis data was invalid or incomplete, starting new analysis');
              // Clear localStorage flag to prevent false "completed" state
              localStorage.removeItem(`analysis_complete_${gameId}`);
              startAnalysis();
            }
          })
          .catch(err => {
            console.error('Error fetching cached analysis data:', err);
            // Clear cache and start fresh
            localStorage.removeItem(`analysis_complete_${gameId}`);
            startAnalysis();
          });
      } else {
        startAnalysis();
      }
    }

    // Cleanup function to clear any intervals when component unmounts
    return () => {
      clearAllIntervals();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gameId]);

  // If auth error, redirect to login
  useEffect(() => {
    if (authError) {
      navigate('/login?redirect=' + encodeURIComponent(window.location.pathname));
    }
  }, [authError, navigate]);

  // Function to handle retry
  const handleRetry = () => {
    // Clear any stored error state
    localStorage.removeItem(`analysis_error_${gameId}`);
    localStorage.removeItem(`analysis_complete_${gameId}`);
    localStorage.removeItem(`last_known_progress_${gameId}`);
    localStorage.removeItem(`last_progress_update_${gameId}`);

    // Reset state
    setAnalysisError(null);
    setInsufficientCreditsError(false);
    analysisErrorRef.current = false;
    setPollingFailed(false);
    setProgress(0);

    startAnalysis();
  };

  const handleRequestReanalyze = () => {
    setShowReanalyzeConfirm(true);
  };

  const handleConfirmReanalyze = async () => {
    setConfirmingReanalyze(true);
    setShowReanalyzeConfirm(false);
    trackedViewRef.current = false;
    try {
      await startAnalysis({ forceReanalyze: true });
    } finally {
      setConfirmingReanalyze(false);
    }
  };

  // Prefer the loading UI while a fresh analysis is running (ignore stale error state).
  if (analysisError && !loading) {
    return (
      <ErrorWithRetry
        error={analysisError}
        onRetry={handleRetry}
        onBack={() => navigate('/games')}
        insufficientCredits={insufficientCreditsError}
        onBuyCredits={() => navigate('/credits')}
      />
    );
  }

  // Show loading state
  if (loading) {
    return (
      <div className={`container mx-auto px-4 py-8 ${isDarkMode ? 'bg-gray-900 text-white' : 'bg-gray-50 text-gray-900'}`}>
        <div className="max-w-6xl mx-auto">
          <div className="mb-6 flex items-center">
            <button
              onClick={() => navigate('/games')}
              className={`mr-4 px-3 py-1.5 rounded text-sm font-medium transition ${
                isDarkMode
                  ? 'bg-gray-800 text-gray-200 hover:bg-gray-700'
                  : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
              }`}
            >
              ← Back to Games
                </button>
            <h1 className="text-2xl font-bold">Game Analysis</h1>
      </div>

          <div className="mb-6">
            <AnalysisInfo isDarkMode={isDarkMode} ceyleryNotRunning={!isCeleryRunning} />
                </div>

          <div className="mb-6">
                <ProgressBar
                    progress={progress}
                    isDarkMode={isDarkMode}
                    startTime={analysisStartTime}
                />
          </div>

          <div className={`mt-4 p-4 rounded-md ${isDarkMode ? 'bg-gray-800' : 'bg-white'} shadow-md`}>
            <div className="flex items-center mb-2">
              <div className={`mr-3 ${
                isDarkMode ? 'text-blue-400' : 'text-blue-600'
              }`}>
                {progress < 100 ? (
                  <FaSpinner className="animate-spin" size={20} />
                ) : (
                  <FaCheckCircle size={20} />
                )}
              </div>
              <h3 className="font-semibold">{statusMessage}</h3>
            </div>
            <div className={`ml-8 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              <p>{loadingMessage}</p>
              <div
                className={`mt-4 rounded-lg border px-4 py-3 text-sm ${
                  isDarkMode
                    ? 'border-indigo-700/60 bg-indigo-950/40 text-indigo-100'
                    : 'border-indigo-200 bg-indigo-50 text-indigo-900'
                }`}
              >
                <p className="font-medium">Runs in the background</p>
                <p className={`mt-1 ${isDarkMode ? 'text-indigo-200/90' : 'text-indigo-800'}`}>
                  {singleGameSendsEmail
                    ? 'Depth-20 reviews often take 5–15 minutes. You can close this tab — we\'ll email you when ready. Games also shows live progress and a toast when you\'re signed in.'
                    : 'Depth-20 reviews often take 5–15 minutes. You do not need to wait here — open Games for progress, or return to this link when finished.'}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => navigate('/games')}
                    className={`px-3 py-1.5 rounded-md text-sm font-medium ${
                      isDarkMode
                        ? 'bg-indigo-600 text-white hover:bg-indigo-500'
                        : 'bg-indigo-600 text-white hover:bg-indigo-700'
                    }`}
                  >
                    Go to Games
                  </button>
                  {batchId ? (
                    <button
                      type="button"
                      onClick={() => navigate(`/batch-report/${batchId}`)}
                      className={`px-3 py-1.5 rounded-md text-sm font-medium border ${
                        isDarkMode
                          ? 'border-indigo-500 text-indigo-100 hover:bg-indigo-900/50'
                          : 'border-indigo-300 text-indigo-800 hover:bg-indigo-100'
                      }`}
                    >
                      Back to batch report
                    </button>
                  ) : null}
                </div>
              </div>
              {elapsedTime > 0 ? (
                <p className="mt-3 text-xs opacity-80">Time elapsed: {formatTime(elapsedTime)}</p>
              ) : null}
              {overdueMessage && (
                <div className={`mt-4 p-3 rounded-md ${
                  isDarkMode ? 'bg-amber-900 text-amber-200' : 'bg-amber-50 text-amber-800'
                }`}>
                  <FaExclamationTriangle className="inline-block mr-2 text-amber-600" />
                  {overdueMessage}
                </div>
              )}

              {pollingFailed && (
                <div className={`mt-4 p-3 rounded-md ${
                  isDarkMode ? 'bg-red-900/30 text-red-200' : 'bg-red-50 text-red-800'
                }`}>
                  <FaExclamationTriangle className="inline-block mr-2 text-red-600" />
                  We're having trouble communicating with the analysis server.
                  <button
                    onClick={handleRestartAnalysis}
                    className={`ml-2 px-3 py-1 rounded-md text-sm font-medium ${
                      isDarkMode ? 'bg-red-800 text-white' : 'bg-red-100 text-red-900'
                    }`}
                  >
                    Try Again
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Show analysis results or no data error
  return (
    <div className={`container mx-auto px-4 py-8 ${isDarkMode ? 'bg-gray-900 text-white' : 'bg-gray-50 text-gray-900'}`}>
      <div className="max-w-6xl mx-auto">
        <div className="mb-6 flex items-center">
          <button
            onClick={() => navigate('/games')}
            className={`mr-4 px-3 py-1.5 rounded text-sm font-medium transition ${
              isDarkMode
                ? 'bg-gray-800 text-gray-200 hover:bg-gray-700'
                : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
            }`}
          >
            ← Back to Games
          </button>
          <h1 className="text-2xl font-bold">Game Analysis Results</h1>
        </div>

        <BatchContextBanner
          batchId={batchId}
          batchContext={analysisData?.batch_context}
          move={move}
          priority={priority}
        />

        {analysisData && (
          (analysisData.moves && analysisData.moves.length > 0) ||
          (analysisData.positions && analysisData.positions.length > 0) ||
          (analysisData.metrics && Object.keys(analysisData.metrics).length > 0)
        ) ? (
          <GameAnalysisResults
            analysisData={analysisData}
            batchId={batchId}
            initialMoveNumber={move}
            gameId={gameId}
            priority={priority}
            onReanalyze={handleRequestReanalyze}
          />
        ) : (
          <NoDataError
            gameId={gameId}
            onRetry={handleRetry}
            onBack={() => navigate('/games')}
          />
        )}
      </div>

      <AnalyzeGameConfirmDialog
        open={showReanalyzeConfirm}
        onClose={() => setShowReanalyzeConfirm(false)}
        onConfirm={handleConfirmReanalyze}
        creditsRequired={1}
        creditsAvailable={credits}
        isReanalyze
        confirming={confirmingReanalyze}
        sendsCompletionEmail={singleGameSendsEmail}
      />
    </div>
    );
};

export default SingleGameAnalysis;
