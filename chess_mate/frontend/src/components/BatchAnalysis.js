import React, { useState, useEffect, useContext } from 'react';
import { toast } from 'react-hot-toast';
import { analyzeBatchGames, checkBatchAnalysisStatus, fetchUserGames } from '../services/apiRequests';
import { useTheme } from '../context/ThemeContext';
import { UserContext } from '../contexts/UserContext';
import { useNavigate } from 'react-router-dom';
import { 
  BarChart2, 
  AlertCircle, 
  Clock, 
  CheckCircle,
  Coins,
  Filter,
  RefreshCw
} from 'lucide-react';
import LoadingSpinner from './LoadingSpinner';

const BatchAnalysis = () => {
  const [numGames, setNumGames] = useState(10);
  const [loading, setLoading] = useState(false);
  const [progressPercent, setProgressPercent] = useState(0);
  const [currentProgress, setCurrentProgress] = useState(0);
  const [totalGames, setTotalGames] = useState(0);
  const [estimatedTime, setEstimatedTime] = useState(0);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [startTime, setStartTime] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const [availableGames, setAvailableGames] = useState([]);
  const [selectedTimeControl, setSelectedTimeControl] = useState('all');
  const [includeAnalyzed, setIncludeAnalyzed] = useState(false);
  const { isDarkMode } = useTheme();
  const { credits } = useContext(UserContext);
  const navigate = useNavigate();
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Fetch available games when component mounts
  useEffect(() => {
    const fetchAvailableGames = async () => {
      try {
        const games = await fetchUserGames();
        setAvailableGames(games);
      } catch (error) {
        console.error('Error fetching games:', error);
        toast.error('Failed to fetch available games');
      }
    };
    fetchAvailableGames();
  }, []);

  useEffect(() => {
    let intervalId;
    let toastId;

    const checkProgress = async () => {
      if (!taskId) return;

      try {
        const response = await checkBatchAnalysisStatus(taskId);
        console.log('Status response:', response);

        // Get the state and meta information
        const state = response?.state?.toUpperCase();
        const meta = response?.meta || {};
        
        switch (state) {
          case 'SUCCESS':
            setIsAnalyzing(false);
            clearInterval(intervalId);
            setProgressPercent(100);
            if (toastId) toast.dismiss(toastId);
            toast.success('Analysis completed!');
            navigate(`/batch-analysis/results/${taskId}`, { 
              replace: true,
              state: { 
                taskId,
                results: response.completed_games,
                failedGames: response.failed_games,
                aggregateMetrics: response.aggregate_metrics
              }
            });
            return true;
            
          case 'FAILURE':
            setIsAnalyzing(false);
            clearInterval(intervalId);
            setProgressPercent(0);
            if (toastId) toast.dismiss(toastId);
            // Display detailed error message from backend
            const errorMessage = meta.error || meta.message || 'Batch analysis failed';
            toast.error(errorMessage);
            // Update progress information
            setCurrentProgress(meta.current || 0);
            setTotalGames(meta.total || 0);
            return true;
            
          case 'PROGRESS':
          case 'STARTED':
          case 'PENDING':
            if (meta) {
              const current = meta.current || 0;
              const total = meta.total || totalGames;
              if (total > 0) {
                setCurrentProgress(current);
                setTotalGames(total);
                const percent = Math.round((current / total) * 100);
                setProgressPercent(isNaN(percent) ? 0 : percent);
                
                // Update loading toast with current progress message
                const progressMessage = meta.message || `Analyzing game ${current} of ${total}`;
                if (toastId) {
                  toast.loading(progressMessage, { id: toastId });
                } else {
                  toastId = toast.loading(progressMessage);
                }
              }
            }
            return false;
            
          default:
            console.warn('Unknown state:', state);
            if (meta) {
              const current = meta.current || 0;
              const total = meta.total || totalGames;
              if (total > 0) {
                setCurrentProgress(current);
                setTotalGames(total);
                const percent = Math.round((current / total) * 100);
                setProgressPercent(isNaN(percent) ? 0 : percent);
              }
            }
            return false;
        }
      } catch (error) {
        console.error('Error checking progress:', error);
        setIsAnalyzing(false);
        if (toastId) toast.dismiss(toastId);
        toast.error('Error checking analysis progress');
        clearInterval(intervalId);
        return true;
      }
    };

    if (isAnalyzing && taskId) {
      // Initial check
      checkProgress();
      // Then start polling
      intervalId = setInterval(checkProgress, 2000);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
      if (toastId) {
        toast.dismiss(toastId);
      }
    };
  }, [isAnalyzing, taskId, navigate, totalGames]);

  useEffect(() => {
    let timer;
    if (startTime && isAnalyzing) {
      timer = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        setElapsedTime(elapsed);
        
        // Update estimated time based on current progress
        if (currentProgress > 0) {
          const timePerGame = elapsed / currentProgress;
          const remainingGames = totalGames - currentProgress;
          const newEstimate = Math.ceil(timePerGame * remainingGames);
          setEstimatedTime(newEstimate);
        }
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [startTime, isAnalyzing, currentProgress, totalGames]);

  const startBatchAnalysis = async () => {
    if (!numGames) {
      toast.error('Please enter the number of games to analyze');
      return;
    }

    if (numGames > 50) {
      toast.error('Maximum number of games for batch analysis is 50');
      return;
    }

    try {
      setIsAnalyzing(true);
      setProgressPercent(0);
      setCurrentProgress(0);
      setStartTime(Date.now());
      
      const response = await analyzeBatchGames(numGames, selectedTimeControl, includeAnalyzed);
      
      if (response?.task_id) {
        setTaskId(response.task_id);
        setTotalGames(response.total_games || numGames);
        setEstimatedTime(response.estimated_time || numGames * 2);
        toast.success('Analysis started! This may take a few minutes.');
      } else {
        throw new Error('No task ID received');
      }
    } catch (error) {
      console.error('Error starting batch analysis:', error);
      toast.error(error.message || 'Failed to start analysis');
      setIsAnalyzing(false);
      setStartTime(null);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const filteredGames = availableGames.filter(game => {
    // Get time control category from the game's time control
    const getTimeControlCategory = (timeControl) => {
      if (!timeControl) return null;
      try {
        // Parse time control format (e.g., "180" or "180+2" or "180+2+45")
        const parts = timeControl.split('+');
        const baseTime = parseInt(parts[0]);
        const increment = parts.length > 1 ? parseInt(parts[1]) : 0;
        
        // Calculate total time for first 40 moves
        const totalTime = baseTime + (increment * 40);
        
        // Categorize based on total time
        if (totalTime < 180) return 'bullet';  // 3 minutes
        if (totalTime < 600) return 'blitz';   // 10 minutes
        if (totalTime < 1800) return 'rapid';  // 30 minutes
        return 'classical';
      } catch (error) {
        // Try to categorize based on platform-specific formats
        if (timeControl.toLowerCase().includes('bullet')) return 'bullet';
        if (timeControl.toLowerCase().includes('blitz')) return 'blitz';
        if (timeControl.toLowerCase().includes('rapid')) return 'rapid';
        if (timeControl.toLowerCase().includes('classical')) return 'classical';
        return null;
      }
    };

    const gameTimeControl = getTimeControlCategory(game.time_control);
    
    // Filter by time control if not 'all'
    if (selectedTimeControl !== 'all' && gameTimeControl !== selectedTimeControl) {
      return false;
    }
    
    // Filter by analysis status if needed
    if (!includeAnalyzed && game.analysis) {
      return false;
    }
    
    return true;
  });

  // Update numGames if it's more than available games
  useEffect(() => {
    if (numGames > filteredGames.length) {
      setNumGames(filteredGames.length || 1);
    }
  }, [filteredGames.length, numGames]);

  return (
    <div className={`min-h-screen ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header Section */}
        <div className="mb-8">
          <h1 className={`text-3xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Batch Analysis
          </h1>
          <p className={`mt-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            Analyze multiple games at once to get insights into your playing patterns (maximum 50 games).
          </p>
        </div>
        
        {/* Credits Info */}
        {/*
        <div className={`mb-8 p-4 rounded-lg ${
          isDarkMode ? 'bg-gray-800' : 'bg-white'
        } shadow-sm`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Coins className={`h-5 w-5 ${credits < numGames ? 'text-red-500' : 'text-green-500'}`} />
              <span className={`font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                Available Credits: {credits}
              </span>
            </div>
            <div className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              Required Credits: {numGames}
            </div>
          </div>
          {credits < numGames && (
            <div className="mt-2 flex items-start space-x-2">
              <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
              <p className="text-sm text-red-500">
                Insufficient credits. You need {numGames - credits} more credits to analyze {numGames} games.
              </p>
            </div>
          )}
        </div>
        */}

        {/* Analysis Options */}
        <div className={`mb-8 p-6 rounded-lg ${
          isDarkMode ? 'bg-gray-800' : 'bg-white'
        } shadow-sm`}>
          <h2 className={`text-lg font-medium mb-4 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Analysis Options
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Number of Games */}
            <div>
              <label htmlFor="numGames" className={`block text-sm font-medium ${
                isDarkMode ? 'text-gray-200' : 'text-gray-700'
              }`}>
                Number of Games (max 50)
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <input
                  type="number"
                  name="numGames"
                  id="numGames"
                  min="1"
                  max="50"
                  className={`block w-full rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${
                    isDarkMode 
                      ? 'bg-gray-700 border-gray-600 text-white' 
                      : 'border-gray-300 text-gray-900'
                  }`}
                  value={numGames}
                  onChange={(e) => {
                    const value = parseInt(e.target.value) || '';
                    if (value > 50) {
                      toast.error('Maximum number of games for batch analysis is 50');
                      setNumGames(50);
                    } else {
                      setNumGames(value);
                    }
                  }}
                />
                <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                  <span className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    / 50
                  </span>
                </div>
              </div>
            </div>

            {/* Time Control Filter */}
            <div>
              <label htmlFor="timeControl" className={`block text-sm font-medium ${
                isDarkMode ? 'text-gray-200' : 'text-gray-700'
              }`}>
                Time Control
              </label>
              <select
                id="timeControl"
                className={`mt-1 block w-full rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${
                  isDarkMode 
                    ? 'bg-gray-700 border-gray-600 text-white' 
                    : 'border-gray-300 text-gray-900'
                }`}
                value={selectedTimeControl}
                onChange={(e) => setSelectedTimeControl(e.target.value)}
              >
                <option value="all">All Time Controls</option>
                <option value="bullet">Bullet</option>
                <option value="blitz">Blitz</option>
                <option value="rapid">Rapid</option>
                <option value="classical">Classical</option>
              </select>
            </div>
          </div>

          {/* Include Already Analyzed Games */}
          <div className="mt-4">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                className="rounded border-gray-300 text-indigo-600 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
                checked={includeAnalyzed}
                onChange={(e) => setIncludeAnalyzed(e.target.checked)}
              />
              <span className={`text-sm ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>
                Include already analyzed games
              </span>
            </label>
          </div>
        </div>

        {/* Progress Section */}
        {isAnalyzing ? (
          <div className={`p-6 rounded-lg ${
            isDarkMode ? 'bg-gray-800' : 'bg-white'
          } shadow-sm`}>
            <div className="space-y-4">
              {/* Progress Bar */}
              <div className="relative pt-1">
                <div className="flex mb-2 items-center justify-between">
                  <div>
                    <span className={`text-xs font-semibold inline-block py-1 px-2 uppercase rounded-full ${
                      isDarkMode ? 'bg-gray-700 text-gray-200' : 'bg-gray-200 text-gray-800'
                    }`}>
                      Progress
                    </span>
                  </div>
                  <div className={`text-right ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                    <span className="text-xs font-semibold">
                      {progressPercent}%
                    </span>
                  </div>
                </div>
                <div className={`overflow-hidden h-2 mb-4 text-xs flex rounded ${
                  isDarkMode ? 'bg-gray-700' : 'bg-gray-200'
                }`}>
                  <div
                    style={{ width: `${progressPercent}%` }}
                    className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-indigo-500"
                  />
                </div>
              </div>

              {/* Status Information */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className={`p-4 rounded-lg ${
                  isDarkMode ? 'bg-gray-700' : 'bg-gray-100'
                }`}>
                  <div className="flex items-center space-x-2">
                    <BarChart2 className="h-5 w-5 text-indigo-500" />
                    <span className={`font-medium ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>
                      {currentProgress} of {totalGames} games
                    </span>
                  </div>
                </div>

                <div className={`p-4 rounded-lg ${
                  isDarkMode ? 'bg-gray-700' : 'bg-gray-100'
                }`}>
                  <div className="flex items-center space-x-2">
                    <Clock className="h-5 w-5 text-indigo-500" />
                    <span className={`font-medium ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>
                      Time Elapsed: {formatTime(elapsedTime)}
                    </span>
                  </div>
                </div>

                <div className={`p-4 rounded-lg ${
                  isDarkMode ? 'bg-gray-700' : 'bg-gray-100'
                }`}>
                  <div className="flex items-center space-x-2">
                    <Clock className="h-5 w-5 text-indigo-500" />
                    <span className={`font-medium ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>
                      Estimated: {formatTime(estimatedTime)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <button
            onClick={startBatchAnalysis}
            disabled={isAnalyzing}
            className={`w-full py-3 px-4 rounded-lg font-medium transition-colors ${
              isAnalyzing ? 'bg-gray-400 cursor-not-allowed' : isDarkMode ? 'bg-indigo-600 hover:bg-indigo-700 text-white' : 'bg-indigo-600 hover:bg-indigo-700 text-white'
            }`}
          >
            {isAnalyzing ? (
              <div className="flex items-center justify-center space-x-2">
                <LoadingSpinner size="small" />
                <span>Analyzing...</span>
              </div>
            ) : (
              'Start Batch Analysis'
            )}
          </button>
        )}
      </div>
    </div>
  );
};

export default BatchAnalysis;