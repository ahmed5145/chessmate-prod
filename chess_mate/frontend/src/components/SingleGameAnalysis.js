import React, { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { analyzeSpecificGame, checkAnalysisStatus, fetchGameAnalysis } from '../services/gameAnalysisService';
import GameAnalysisResults from './GameAnalysisResults';
import LoadingSpinner from './LoadingSpinner';
import './SingleGameAnalysis.css';
import { useTheme } from '../context/ThemeContext';
import { FaChess } from 'react-icons/fa';

const ProgressBar = ({ progress, isDarkMode, startTime }) => {
    const [timeElapsed, setTimeElapsed] = useState(0);
    
    useEffect(() => {
        const timer = setInterval(() => {
            if (startTime) {
                setTimeElapsed(Math.floor((Date.now() - startTime) / 1000));
            }
        }, 1000);
        
        return () => clearInterval(timer);
    }, [startTime]);
    
    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };
    
    return (
        <div className={`p-6 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'} shadow-sm`}>
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center">
                    <FaChess className={`mr-2 ${isDarkMode ? 'text-blue-400' : 'text-blue-600'}`} />
                    <span className={`font-medium ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>
                        Analyzing Game
                    </span>
                </div>
                <span className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    {formatTime(timeElapsed)}
                </span>
            </div>
            <div className="relative pt-1">
                <div className="flex mb-2 items-center justify-between">
                    <div>
                        <span className={`text-xs font-semibold inline-block py-1 px-2 uppercase rounded-full ${
                            isDarkMode ? 'text-blue-400 bg-blue-900' : 'text-blue-600 bg-blue-200'
                        }`}>
                            {progress}% Complete
                        </span>
                    </div>
                </div>
                <div className={`overflow-hidden h-2 mb-4 text-xs flex rounded ${
                    isDarkMode ? 'bg-gray-700' : 'bg-gray-200'
                }`}>
                    <div
                        style={{ width: `${progress}%`, transition: 'width 0.5s ease-in-out' }}
                        className={`shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center ${
                            isDarkMode ? 'bg-blue-500' : 'bg-blue-600'
                        }`}
                    ></div>
                </div>
                <div className="text-center">
                    <span className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        {progress < 100 ? 'Analyzing moves and generating feedback...' : 'Analysis complete!'}
                    </span>
                </div>
            </div>
        </div>
    );
};

const SingleGameAnalysis = () => {
  const { gameId } = useParams();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
    const [analysisData, setAnalysisData] = useState(null);
    const pollingIntervalRef = useRef(null);
    const hasStartedRef = useRef(false);
    const [isDarkMode, setIsDarkMode] = useState(false);
    const [progress, setProgress] = useState(0);
    const [analysisStartTime, setAnalysisStartTime] = useState(null);

    // Validate analysis data structure
    const validateAnalysisData = (data) => {
        if (!data) {
            console.warn('No data received');
            return false;
        }
        
        // Handle polling status response
        if (data.status) {
            // This is a status response, validate accordingly
            if (['completed', 'in_progress', 'PENDING', 'started'].includes(data.status)) {
                return true;
            }
            if (data.status === 'error' || data.status === 'failed') {
                console.warn('Error status in response:', data.message);
                return false;
            }
        }
        
        // Handle final analysis response
        // First, try to get the analysis results from the correct path
        const analysisResults = data.analysis_results || 
                              (data.analysis && data.analysis.analysis_results) || 
                              data.analysis;
                              
        if (!analysisResults) {
            console.warn('No analysis results found:', data);
            return false;
        }
        
        // Check for required structures
        const hasAnalysisData = analysisResults.summary || analysisResults.moves;
        const hasFeedback = data.feedback && 
                           (data.feedback.feedback || 
                            (typeof data.feedback === 'object' && Object.keys(data.feedback).length > 0));
                            
        if (!hasAnalysisData && !hasFeedback) {
            console.warn('Missing both analysis data and feedback:', data);
            return false;
        }

        return true;
    };

    const mergeAnalysisData = (results, statusResponse) => {
        // Extract analysis data from both responses
        const analysisResults = results.analysis_results || results.analysis || {};
        const statusAnalysis = statusResponse.analysis || {};
        const statusFeedback = statusResponse.feedback || {};
        
        // Normalize the data structure
        const normalizedResults = {
            analysis_results: {
                summary: {
                    overall: {
                        ...statusAnalysis.summary?.overall,
                        ...analysisResults.summary?.overall
                    },
                    phases: {
                        ...statusAnalysis.summary?.phases,
                        ...analysisResults.summary?.phases
                    },
                    time_management: {
                        ...statusAnalysis.summary?.time_management,
                        ...analysisResults.summary?.time_management
                    },
                    tactics: {
                        ...statusAnalysis.summary?.tactics,
                        ...analysisResults.summary?.tactics
                    },
                    resourcefulness: {
                        ...statusAnalysis.summary?.resourcefulness,
                        ...analysisResults.summary?.resourcefulness
                    }
                },
                moves: analysisResults.moves || statusAnalysis.moves || []
            },
            feedback: {
                source: statusFeedback.source || 'statistical',
                strengths: statusFeedback.strengths || [],
                weaknesses: statusFeedback.weaknesses || [],
                critical_moments: statusFeedback.critical_moments || [],
                opening: statusFeedback.opening || {},
                middlegame: statusFeedback.middlegame || {},
                endgame: statusFeedback.endgame || {},
                suggestions: statusFeedback.suggestions || []
            }
        };

        // Ensure we have valid metrics
        if (normalizedResults.analysis_results.summary.overall.accuracy === undefined) {
            normalizedResults.analysis_results.summary.overall.accuracy = 0;
        }

        // Ensure phase metrics are properly populated
        ['opening', 'middlegame', 'endgame'].forEach(phase => {
            if (!normalizedResults.analysis_results.summary.phases[phase]) {
                normalizedResults.analysis_results.summary.phases[phase] = {
                    accuracy: normalizedResults.analysis_results.summary.overall.accuracy || 0,
                    mistakes: 0,
                    opportunities: 0,
                    best_moves: 0
                };
            }
        });

        return normalizedResults;
    };

    // Update the polling status function
    const pollStatus = async (taskId) => {
        try {
            const statusResponse = await checkAnalysisStatus(taskId);
            console.log('Status check response:', statusResponse);

            if (!statusResponse) {
                throw new Error('No response received from status check');
            }

            // Update progress
            if (statusResponse.progress !== undefined) {
                setProgress(Math.min(95, statusResponse.progress));
            } else if (statusResponse.status === 'in_progress') {
                setProgress((prev) => Math.min(95, prev + 5));
            }

            if (statusResponse.status === 'FAILURE' || statusResponse.status === 'failed' || statusResponse.status === 'error') {
                clearInterval(pollingIntervalRef.current);
                const errorMessage = statusResponse.message || 'Analysis failed. Please try again.';
                setError(errorMessage);
                setLoading(false);
                setAnalysisStartTime(null);
                return;
            }

            if (statusResponse.status === 'SUCCESS' || statusResponse.status === 'completed') {
                clearInterval(pollingIntervalRef.current);
                setProgress(100);
                
                // Get the complete analysis results
                const results = await fetchGameAnalysis(gameId);
                console.log('Final analysis results:', results);
                
                // Merge data properly
                const mergedResults = mergeAnalysisData(results, statusResponse);
                
                if (validateAnalysisData(mergedResults)) {
                    setAnalysisData(mergedResults);
                    setLoading(false);
                } else {
                    console.warn('Invalid analysis results format:', mergedResults);
                    setError('Error processing analysis results. Please try again.');
                    setLoading(false);
                }
                setAnalysisStartTime(null);
            }
        } catch (error) {
            console.error('Error during polling:', error);
            clearInterval(pollingIntervalRef.current);
            setError('Error checking analysis status. Please try again.');
            setLoading(false);
            setAnalysisStartTime(null);
        }
    };

    useEffect(() => {
        // Check system dark mode preference
        const darkModePreference = window.matchMedia('(prefers-color-scheme: dark)');
        setIsDarkMode(darkModePreference.matches);

        // Listen for changes in system dark mode
        const handleDarkModeChange = (e) => setIsDarkMode(e.matches);
        darkModePreference.addEventListener('change', handleDarkModeChange);

        return () => {
            darkModePreference.removeEventListener('change', handleDarkModeChange);
        };
    }, []);

    useEffect(() => {
  const startAnalysis = async () => {
    try {
      setLoading(true);
      setError(null);
      setAnalysisStartTime(Date.now());
      setProgress(0);
      
      // Start the analysis
      const response = await analyzeSpecificGame(gameId);
      console.log('Initial analysis response:', response);

      if (!response) {
        throw new Error('No response received from analysis request');
      }

      if (response.status === 'completed' || response.status === 'already_analyzed') {
        // Analysis is already complete, fetch the results
        const results = await fetchGameAnalysis(gameId);
        console.log('Fetched analysis results:', results);
        if (validateAnalysisData(results)) {
          setAnalysisData(results);
        } else {
          throw new Error('Invalid analysis results format');
        }
        setLoading(false);
      } else if (response.status === 'started' || response.status === 'PENDING' || response.status === 'in_progress') {
        // Start polling for status
        const pollStatus = async (taskId) => {
          try {
            const statusResponse = await checkAnalysisStatus(taskId);
            console.log('Status check response:', statusResponse);

            if (!statusResponse) {
              throw new Error('No response received from status check');
            }

            if (statusResponse.status === 'FAILURE' || statusResponse.status === 'failed' || statusResponse.status === 'error') {
              clearInterval(pollingIntervalRef.current);
              const errorMessage = statusResponse.message || 'Analysis failed. Please try again.';
              setError(errorMessage);
              setLoading(false);
              setAnalysisStartTime(null);
              return;
            }

            if (statusResponse.status === 'SUCCESS' || statusResponse.status === 'completed') {
              clearInterval(pollingIntervalRef.current);
              setProgress(100);
              
              // Get the complete analysis results
              const results = await fetchGameAnalysis(gameId);
              console.log('Final analysis results:', results);
              
              // Merge data properly
              const mergedResults = mergeAnalysisData(results, statusResponse);
              
              if (validateAnalysisData(mergedResults)) {
                setAnalysisData(mergedResults);
                setLoading(false);
              } else {
                console.warn('Invalid analysis results format:', mergedResults);
                setError('Error processing analysis results. Please try again.');
                setLoading(false);
              }
              setAnalysisStartTime(null);
            }
          } catch (error) {
            console.error('Error during polling:', error);
            clearInterval(pollingIntervalRef.current);
            setError('Error checking analysis status. Please try again.');
            setLoading(false);
            setAnalysisStartTime(null);
          }
        };

        // Start polling every 4 seconds
        pollingIntervalRef.current = setInterval(() => pollStatus(response.task_id), 4000);
      } else {
        throw new Error(`Unexpected status: ${response.status}`);
      }
    } catch (error) {
      console.error('Error starting analysis:', error);
      setError(error.message || 'Error starting analysis. Please try again.');
      setLoading(false);
      setAnalysisStartTime(null);
    }
  };

        if (!hasStartedRef.current) {
            hasStartedRef.current = true;
            startAnalysis();
        }

      return () => {
            if (pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current);
            }
        };
    }, [gameId, navigate]);

    const handleRetry = () => {
        hasStartedRef.current = false;
        if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
        }
        setError(null);
        setLoading(true);
        setAnalysisData(null);
    };

  if (loading) {
        return <LoadingSpinner message="Analyzing game..." />;
  }

  if (error) {
    return (
            <div className="error-container">
                <p className="error-message">{error}</p>
                <button onClick={handleRetry} className="retry-button">
                    Retry Analysis
                </button>
      </div>
    );
  }

    if (!analysisData) {
    return (
            <div className="error-container">
                <p className="error-message">No analysis data available</p>
                <button onClick={handleRetry} className="retry-button">
                    Retry Analysis
                </button>
      </div>
    );
  }

    return (
        <div className="container mx-auto px-4 py-8">
            {error ? (
                <div className={`p-4 rounded-lg ${isDarkMode ? 'bg-red-900 text-red-200' : 'bg-red-100 text-red-700'} mb-4`}>
                    {error}
                </div>
            ) : loading ? (
                <ProgressBar 
                    progress={progress} 
                    isDarkMode={isDarkMode} 
                    startTime={analysisStartTime}
                />
            ) : (
                <GameAnalysisResults analysisData={analysisData} isDarkMode={isDarkMode} />
            )}
        </div>
    );
};

export default SingleGameAnalysis; 