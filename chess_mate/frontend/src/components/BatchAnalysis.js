import React, { useState, useEffect, useRef, useContext } from 'react';
import { toast } from 'react-hot-toast';
import { Loader2 } from 'lucide-react';
import { analyzeBatchGames, checkBatchAnalysisStatus, fetchUserGames } from '../services/apiRequests';
import { useTheme } from '../context/ThemeContext';
import { UserContext } from '../contexts/UserContext';

const BatchAnalysis = () => {
  const [numGames, setNumGames] = useState(10);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [results, setResults] = useState(null);
  const [estimatedTime, setEstimatedTime] = useState(0);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [startTime, setStartTime] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const [availableGames, setAvailableGames] = useState(0);
  const { isDarkMode } = useTheme();
  const { credits } = useContext(UserContext);

  // Fetch available games count when component mounts
  useEffect(() => {
    const fetchAvailableGames = async () => {
      try {
        const games = await fetchUserGames();
        setAvailableGames(games.length);
      } catch (error) {
        console.error('Error fetching games count:', error);
        toast.error('Failed to fetch available games count');
      }
    };
    fetchAvailableGames();
  }, []);

  // Poll for status updates when we have a task
  useEffect(() => {
    let pollInterval;
    
    const checkStatus = async () => {
      if (!taskId) return;
      
      try {
        const statusResponse = await checkBatchAnalysisStatus(taskId);
        
        if (statusResponse.status === 'completed') {
          setLoading(false);
          setResults(statusResponse.results);
          setTaskId(null);
          toast.success('Batch analysis completed!');
        } else if (statusResponse.status === 'failed') {
          setLoading(false);
          setTaskId(null);
          toast.error(statusResponse.error || 'Analysis failed');
        } else if (statusResponse.status === 'in_progress') {
          setProgress(statusResponse.progress);
        }
      } catch (error) {
        console.error('Error checking status:', error);
        // Don't stop polling on temporary errors
      }
    };
    
    if (taskId && loading) {
      pollInterval = setInterval(checkStatus, 5000); // Poll every 5 seconds
    }
    
    return () => {
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [taskId, loading]);

  useEffect(() => {
    let timer;
    if (startTime && loading) {
      timer = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        setElapsedTime(elapsed);
        
        // Update estimated time based on current progress
        if (progress.current > 0) {
          const timePerGame = elapsed / progress.current;
          const remainingGames = progress.total - progress.current;
          const newEstimate = Math.ceil(timePerGame * remainingGames);
          setEstimatedTime(newEstimate);
        }
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [startTime, loading, progress]);

  const handleAnalysis = async () => {
    if (!numGames) {
      toast.error('Please enter the number of games to analyze');
      return;
    }

    try {
      setLoading(true);
      setStartTime(Date.now());
      setProgress({ current: 0, total: parseInt(numGames) });
      
      const response = await analyzeBatchGames(numGames);
      
      if (response?.task_id) {
        setTaskId(response.task_id);
        toast.success('Analysis started! This may take a few minutes.');
      } else {
        throw new Error('No task ID received');
      }
    } catch (error) {
      console.error('Error during batch analysis:', error);
      toast.error(error.message || 'Failed to start analysis');
      setLoading(false);
      setStartTime(null);
      setEstimatedTime(0);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 ${isDarkMode ? 'bg-gray-900' : 'bg-white'}`}>
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className={`text-3xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Batch Analysis
          </h1>
          <p className={`mt-2 text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            Analyze multiple games at once to get insights into your playing patterns.
          </p>
        </div>
      </div>

      <div className={`mt-8 max-w-xl ${isDarkMode ? 'bg-gray-800' : 'bg-white'} p-6 rounded-lg shadow-sm`}>
        <div className="space-y-6">
          <div>
            <label htmlFor="numGames" className={`block text-sm font-medium ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>
              Number of Games to Analyze
            </label>
            <div className="mt-2">
              <input
                type="number"
                name="numGames"
                id="numGames"
                min="1"
                max={availableGames}
                className={`block w-full rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${
                  isDarkMode 
                    ? 'bg-gray-700 border-gray-600 text-white' 
                    : 'border-gray-300 text-gray-900'
                }`}
                value={numGames}
                onChange={(e) => setNumGames(parseInt(e.target.value) || '')}
              />
            </div>
          </div>

          <button
            onClick={handleAnalysis}
            disabled={loading}
            className={`inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white 
              ${loading 
                ? 'opacity-50 cursor-not-allowed' 
                : isDarkMode 
                  ? 'bg-indigo-600 hover:bg-indigo-700' 
                  : 'bg-indigo-600 hover:bg-indigo-700'} 
              focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500`}
          >
            {loading ? (
              <>
                <Loader2 className="animate-spin -ml-1 mr-2 h-4 w-4" />
                Analyzing...
              </>
            ) : (
              'Start Analysis'
            )}
          </button>

          {loading && (
            <div className={`mt-4 p-4 rounded-md ${isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
              <div className="flex justify-between items-center">
                <div>
                  <p className={`text-sm font-medium ${isDarkMode ? 'text-gray-200' : 'text-gray-900'}`}>
                    Progress: {progress.current} / {progress.total} games
                  </p>
                  <p className={`mt-1 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    Time elapsed: {formatTime(elapsedTime)}
                  </p>
                  {estimatedTime > 0 && (
                    <p className={`mt-1 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                      Estimated time remaining: {formatTime(estimatedTime)}
                    </p>
                  )}
                </div>
                <Loader2 className={`animate-spin h-5 w-5 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`} />
              </div>
            </div>
          )}

          {results && (
            <div className={`mt-4 p-4 rounded-md ${isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
              <h3 className={`text-lg font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                Analysis Complete
              </h3>
              <div className="mt-2">
                <p className={`text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  Successfully analyzed {results.total_games} games.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BatchAnalysis; 