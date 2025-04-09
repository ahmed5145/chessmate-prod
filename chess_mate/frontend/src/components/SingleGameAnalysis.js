import React, { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { analyzeSpecificGame, checkAnalysisStatus, fetchGameAnalysis, restartAnalysis } from '../services/gameAnalysisService';
import GameAnalysisResults from './GameAnalysisResults';
import LoadingSpinner from './LoadingSpinner';
import './SingleGameAnalysis.css';
import { useTheme } from '../context/ThemeContext';
import { FaChess, FaInfoCircle, FaSpinner, FaExclamationTriangle, FaClock, FaCheckCircle } from 'react-icons/fa';
import { checkAuthStatus } from '../services/authService';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';
import LinearProgress from '@mui/material/LinearProgress';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import { Info, CheckCircle } from 'lucide-react';

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
const ErrorWithRetry = ({ error, onRetry, onBack }) => (
  <div className="flex flex-col items-center justify-center h-full">
    <div className="p-6 bg-red-50 dark:bg-red-900/20 rounded-lg shadow-md text-center max-w-xl w-full">
      <FaExclamationTriangle className="mx-auto text-red-500 text-4xl mb-4" />
      <h2 className="text-xl font-bold text-red-700 dark:text-red-400 mb-4">
        {error || "An error occurred during analysis"}
      </h2>
      <p className="mb-6 text-gray-700 dark:text-gray-300">
        We couldn't complete the analysis of your game. This could be due to server load or an 
        issue with the game data.
      </p>
      <div className="flex flex-col md:flex-row space-y-3 md:space-y-0 md:space-x-3 justify-center">
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium transition"
        >
          Try Again
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
  const { isDarkMode } = useTheme();
  
  // State variables
  const [analysisData, setAnalysisData] = useState(null);
    const [loading, setLoading] = useState(true);
  const [analysisError, setAnalysisError] = useState(null);
  const [authError, setAuthError] = useState(false);
  const [progress, setProgress] = useState(0);
  const [loadingMessage, setLoadingMessage] = useState('Starting analysis...');
  const [progressStatus, setProgressStatus] = useState('starting'); // starting, analyzing, complete
  const [pollingFailed, setPollingFailed] = useState(false);
  const [analysisStartTime, setAnalysisStartTime] = useState(Date.now());
  const [statusCheckCount, setStatusCheckCount] = useState(0);
  const [isCeleryRunning, setIsCeleryRunning] = useState(true);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [statusMessage, setStatusMessage] = useState("Initializing analysis...");
  const [overdueMessage, setOverdueMessage] = useState(null);
  
  // Use refs to keep track of intervals and state across renders
  const progressIntervalRef = useRef(null);
  const statusCheckIntervalRef = useRef(null);
    const hasStartedRef = useRef(false);
  const hasExceededMaxRetries = useRef(false);
  const hasAttemptedDirectFetch = useRef(false);
  const hasAttemptedRecovery = useRef(false);
  const pollingErrorCount = useRef(0);
  const analysisCompleted = useRef(false);
  const timeoutIds = useRef([]);
  const pollingIntervals = useRef([]);
  
  // Poll for analysis status
  const pollForAnalysisStatus = async () => {
    if (!gameId) return;
    
    try {
      setPollingFailed(false);
      const statusResponse = await checkAnalysisStatus(gameId);
      console.log(`Analysis status for game ${gameId}:`, statusResponse);

      // If we have a complete analysis, fetch it
      if (statusResponse.status === 'SUCCESS' || statusResponse.progress === 100) {
        clearAllIntervals();
        setProgressStatus('complete');
        setLoadingMessage('Analysis complete! Loading results...');
        analysisCompleted.current = true;
        await fetchAnalysisData();
        return;
      }

      // Update progress
      const progressValue = parseInt(statusResponse.progress) || 0;
      setProgress(progressValue);
      
      if (statusResponse.message) {
        setLoadingMessage(statusResponse.message);
        setStatusMessage(statusResponse.message);
      } else if (progressValue < 30) {
        setLoadingMessage('Analyzing game moves...');
        setStatusMessage('Analyzing each move with Stockfish engine');
      } else if (progressValue < 60) {
        setLoadingMessage('Calculating game metrics...');
        setStatusMessage('Calculating metrics and identifying patterns');
      } else if (progressValue < 90) {
        setLoadingMessage('Generating insights and recommendations...');
        setStatusMessage('Generating personalized feedback and improvement suggestions');
      } else {
        setLoadingMessage('Finalizing analysis...');
        setStatusMessage('Almost done! Putting everything together');
      }
      
      // If we get to a high progress value without completing, try to fetch analysis directly
      if (progressValue >= 90 && !hasAttemptedDirectFetch.current) {
        hasAttemptedDirectFetch.current = true;
        try {
          console.log('Progress is high, attempting direct fetch');
          await fetchAnalysisData();
        } catch (err) {
          console.log('Direct fetch failed, continuing to poll', err);
        }
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
    
    // Clear all polling intervals
    pollingIntervals.current.forEach(intervalId => {
      clearInterval(intervalId);
    });
    pollingIntervals.current = [];
    
    // Clear all timeout IDs
    timeoutIds.current.forEach(timeoutId => {
      clearTimeout(timeoutId);
    });
    timeoutIds.current = [];
  };

  // Handle analysis restart
  const handleRestartAnalysis = async () => {
    try {
      setLoading(true);
      setAnalysisError(null);
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
        
        // Start polling again
        setProgressStatus('analyzing');
        const pollInterval = setInterval(pollForAnalysisStatus, 3000);
        pollingIntervals.current.push(pollInterval);
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
    setLoadingMessage('Retrieving analysis results...');
    try {
      const data = await fetchGameAnalysis(gameId);
      
      // Check for error message in the data itself
      if (data.error) {
        console.warn('Error returned in analysis data:', data.error);
        setAnalysisError(data.error);
                setLoading(false);
        // Remove from localStorage to prevent future false "completed" states
        localStorage.removeItem(`analysis_complete_${gameId}`);
        return false;
      }
      
      // Verify we have valid data
      if (data && (
        (data.moves && data.moves.length > 0) || 
        (data.positions && data.positions.length > 0) || 
        (data.metrics && Object.keys(data.metrics).length > 0)
      )) {
        console.log('Analysis data retrieved successfully:', data);
        setAnalysisData(data);
                    setLoading(false);
        analysisCompleted.current = true;
        // Mark as complete in localStorage to avoid unnecessary API calls
        localStorage.setItem(`analysis_complete_${gameId}`, 'true');
        return true;
                } else {
        console.warn('Received empty or invalid analysis data:', data);
        // If data is empty but we haven't exceeded max retries, don't show error yet
        if (!hasExceededMaxRetries.current) {
          // Remove from localStorage to prevent future false "completed" states
          localStorage.removeItem(`analysis_complete_${gameId}`);
          return false;
        }
        // Remove from localStorage
        localStorage.removeItem(`analysis_complete_${gameId}`);
        throw new Error('No valid analysis data available. The analysis may have failed.');
            }
        } catch (error) {
      console.error('Error fetching game analysis:', error);
      
      // Check if it's an authentication error
      if (error.auth_error) {
        setAuthError(true);
        return false;
      }
      
      // If Redis is unavailable, the data might not be accessible yet
      // Continue polling rather than showing an error
      if (!hasExceededMaxRetries.current) {
        console.log('Fetch failed but continuing polling attempts');
        return false;
      }
      
      // Remove from localStorage to prevent future false "completed" states
      localStorage.removeItem(`analysis_complete_${gameId}`);
      setAnalysisError(error.message || 'We encountered an error fetching your analysis.');
            setLoading(false);
      return false;
    }
  };

  // Start the analysis process
  const startAnalysis = async () => {
    try {
      setLoading(true);
      setProgress(0);
      setAnalysisData(null);
      setAnalysisError(null);
      setAuthError(false);
      setPollingFailed(false);
      setProgressStatus('starting');
      setLoadingMessage('Starting analysis...');
      setStatusMessage('Initializing analysis...');
      
      // Reset refs
      hasAttemptedDirectFetch.current = false;
      hasAttemptedRecovery.current = false;
      pollingErrorCount.current = 0;
      hasExceededMaxRetries.current = false;
      analysisCompleted.current = false;
      
      // Clear all existing intervals and timeouts
      clearAllIntervals();
      
      // Reset localStorage flags
      localStorage.removeItem(`analysis_complete_${gameId}`);
      localStorage.removeItem(`last_known_progress_${gameId}`);
      localStorage.removeItem(`last_progress_update_${gameId}`);
      
      // Set the analysis start time for timing calculations
      setAnalysisStartTime(Date.now());

      console.log(`Starting analysis for game ${gameId}`);
      const response = await analyzeSpecificGame(gameId);
      console.log('Analysis started response:', response);
      
      if (response && response.success) {
        setProgressStatus('analyzing');
        setLoadingMessage('Analysis has started. Initializing...');
        
        // Set an initial delay before polling to give task time to register
        const initialDelayId = setTimeout(() => {
          // Start polling
          const pollInterval = setInterval(pollForAnalysisStatus, 3000);
          pollingIntervals.current.push(pollInterval);
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
      
      if (error.auth_error) {
        setAuthError(true);
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
  }, [gameId]);

  // If auth error, redirect to login
  useEffect(() => {
    if (authError) {
      navigate('/login?redirect=' + encodeURIComponent(window.location.pathname));
    }
  }, [authError, navigate]);

  // Update the component to handle error states
  useEffect(() => {
    // If the page is loaded directly and we have an error from localStorage,
    // we should clear it and try again
    const storedError = localStorage.getItem(`analysis_error_${gameId}`);
    if (storedError) {
      setAnalysisError(storedError);
      // Only remove the error when user manually retries
    }
  }, [gameId]);

  // Function to handle retry
  const handleRetry = () => {
    // Clear any stored error state
    localStorage.removeItem(`analysis_error_${gameId}`);
    localStorage.removeItem(`analysis_complete_${gameId}`);
    localStorage.removeItem(`last_known_progress_${gameId}`);
    localStorage.removeItem(`last_progress_update_${gameId}`);
    
    // Reset state
    setAnalysisError(null);
    setPollingFailed(false);
    setProgress(0);
    
    // Start fresh analysis
    startAnalysis();
  };

  // If there's an error, display it
  if (analysisError) {
    return (
      <ErrorWithRetry
        error={analysisError}
        onRetry={handleRetry}
        onBack={() => navigate('/games')}
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
              <p>Time elapsed: {formatTime(elapsedTime)}</p>
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
        
        {analysisData && (
          (analysisData.moves && analysisData.moves.length > 0) || 
          (analysisData.positions && analysisData.positions.length > 0) || 
          (analysisData.metrics && Object.keys(analysisData.metrics).length > 0)
        ) ? (
          <GameAnalysisResults analysis={analysisData} isDarkMode={isDarkMode} />
        ) : (
          <NoDataError 
            gameId={gameId}
            onRetry={handleRetry}
            onBack={() => navigate('/games')}
          />
        )}
      </div>
        </div>
    );
};

export default SingleGameAnalysis;