import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { Loader2 } from 'lucide-react';
import { analyzeBatchGames } from '../api';


// API Configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://3.133.97.72/api';


const BatchAnalysis = () => {
  const [numGames, setNumGames] = useState(10);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [results, setResults] = useState(null);
  const [estimatedTime, setEstimatedTime] = useState(0);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [startTime, setStartTime] = useState(null);

  // Listen for progress updates
  useEffect(() => {
    const handleProgress = (event) => {
      const { current, total } = event.detail;
      setProgress({ current, total });
    };

    window.addEventListener('analysisProgress', handleProgress);
    return () => window.removeEventListener('analysisProgress', handleProgress);
  }, []);

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
      
      if (response.results) {
        setResults(response.results);
        toast.success('Batch analysis completed!');
      }
    } catch (error) {
      console.error('Error during batch analysis:', error);
      toast.error(error.message || 'Failed to analyze games');
    } finally {
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
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-3xl font-bold text-gray-900">Batch Analysis</h1>
          <p className="mt-2 text-sm text-gray-700">
            Analyze multiple games at once to get insights into your playing patterns.
          </p>
        </div>
      </div>

      <div className="mt-8 max-w-xl">
        <div className="space-y-6">
          <div>
            <label htmlFor="numGames" className="block text-sm font-medium text-gray-700">
              Number of Games to Analyze
            </label>
            <div className="mt-1">
              <input
                type="number"
                name="numGames"
                id="numGames"
                min="1"
                max="50"
                value={numGames}
                onChange={(e) => setNumGames(Math.min(50, Math.max(1, parseInt(e.target.value) || 1)))}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                disabled={loading}
              />
            </div>
            <p className="mt-2 text-sm text-gray-500">Maximum 50 games can be analyzed at once.</p>
          </div>

          <button
            onClick={handleAnalysis}
            disabled={loading}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
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
            <div className="mt-4 space-y-4">
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div 
                  className="bg-indigo-600 h-2.5 rounded-full transition-all duration-500"
                  style={{ width: `${(progress.current / progress.total) * 100}%` }}
                ></div>
              </div>
              <div className="flex justify-between text-sm text-gray-600">
                <span>Progress: {progress.current}/{progress.total} games</span>
                <span>Elapsed Time: {formatTime(elapsedTime)}</span>
                {progress.current > 0 && (
                  <span>Estimated Time Remaining: {formatTime(estimatedTime)}</span>
                )}
              </div>
            </div>
          )}
        </div>

        {results && (
          <div className="mt-8 space-y-8">
            <h2 className="text-2xl font-bold text-gray-900">Analysis Results</h2>
            
            {/* Overall Stats */}
            <div className="bg-white shadow-lg rounded-lg overflow-hidden">
              <div className="px-6 py-4 bg-indigo-50">
                <h3 className="text-xl font-semibold text-indigo-900">Overall Statistics</h3>
              </div>
              <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="text-lg font-medium text-gray-900 mb-2">Games Summary</h4>
                  <dl className="space-y-2">
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Games Analyzed</dt>
                      <dd className="font-medium text-gray-900">{results.overall_stats.total_games}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Average Accuracy</dt>
                      <dd className="font-medium text-gray-900">{results.overall_stats.average_accuracy.toFixed(1)}%</dd>
                    </div>
                  </dl>
                </div>
                <div>
                  <h4 className="text-lg font-medium text-gray-900 mb-2">Results Distribution</h4>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div className="bg-green-50 rounded-lg p-3">
                      <div className="text-green-700 font-medium">Wins</div>
                      <div className="text-2xl font-bold text-green-800">{results.overall_stats.wins}</div>
                    </div>
                    <div className="bg-yellow-50 rounded-lg p-3">
                      <div className="text-yellow-700 font-medium">Draws</div>
                      <div className="text-2xl font-bold text-yellow-800">{results.overall_stats.draws}</div>
                    </div>
                    <div className="bg-red-50 rounded-lg p-3">
                      <div className="text-red-700 font-medium">Losses</div>
                      <div className="text-2xl font-bold text-red-800">{results.overall_stats.losses}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Resourcefulness Stats */}
            <div className="bg-white shadow-lg rounded-lg overflow-hidden">
              <div className="px-6 py-4 bg-blue-50">
                <h3 className="text-xl font-semibold text-blue-900">Resourcefulness Analysis</h3>
              </div>
              <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-600">Average Defensive Score</span>
                      <span className="text-lg font-medium text-gray-900">
                        {results.overall_stats.resourcefulness?.average_score?.toFixed(1) || 'N/A'}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full"
                        style={{ width: `${results.overall_stats.resourcefulness?.average_score || 0}%` }}
                      ></div>
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-600">Counter-Attack Success Rate</span>
                      <span className="text-lg font-medium text-gray-900">
                        {results.overall_stats.resourcefulness?.counter_success?.toFixed(1) || 'N/A'}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full"
                        style={{ width: `${results.overall_stats.resourcefulness?.counter_success || 0}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-600">Critical Defense Success</span>
                      <span className="text-lg font-medium text-gray-900">
                        {results.overall_stats.resourcefulness?.critical_defense_success?.toFixed(1) || 'N/A'}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full"
                        style={{ width: `${results.overall_stats.resourcefulness?.critical_defense_success || 0}%` }}
                      ></div>
                    </div>
                  </div>
                  <div className="bg-blue-50 rounded-lg p-4">
                    <h4 className="font-medium text-blue-900 mb-2">Total Defensive Saves</h4>
                    <div className="text-3xl font-bold text-blue-700">
                      {results.overall_stats.resourcefulness?.total_saves || 0}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Advantage Capitalization Stats */}
            <div className="bg-white shadow-lg rounded-lg overflow-hidden">
              <div className="px-6 py-4 bg-green-50">
                <h3 className="text-xl font-semibold text-green-900">Advantage Capitalization</h3>
              </div>
              <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-600">Average Conversion Rate</span>
                      <span className="text-lg font-medium text-gray-900">
                        {results.overall_stats.advantage?.average_conversion?.toFixed(1) || 'N/A'}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-green-600 h-2 rounded-full"
                        style={{ width: `${results.overall_stats.advantage?.average_conversion || 0}%` }}
                      ></div>
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-600">Winning Position Frequency</span>
                      <span className="text-lg font-medium text-gray-900">
                        {results.overall_stats.advantage?.winning_position_frequency?.toFixed(1) || 'N/A'}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-green-600 h-2 rounded-full"
                        style={{ width: `${results.overall_stats.advantage?.winning_position_frequency || 0}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
                <div className="space-y-4">
                  <div className="bg-red-50 rounded-lg p-4">
                    <h4 className="font-medium text-red-900 mb-2">Total Missed Wins</h4>
                    <div className="text-3xl font-bold text-red-700">
                      {results.overall_stats.advantage?.total_missed_wins || 0}
                    </div>
                  </div>
                  <div className="bg-green-50 rounded-lg p-4">
                    <h4 className="font-medium text-green-900 mb-2">Average Advantage Duration</h4>
                    <div className="text-3xl font-bold text-green-700">
                      {results.overall_stats.advantage?.average_duration?.toFixed(1) || 'N/A'} moves
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* AI Feedback Section */}
            {results && results.overall_stats.ai_feedback && (
              <div className="bg-white shadow-lg rounded-lg overflow-hidden mt-8">
                <div className="px-6 py-4 bg-purple-50">
                  <h3 className="text-xl font-semibold text-purple-900">AI Analysis Insights</h3>
                </div>
                <div className="p-6">
                  <div className="prose prose-indigo">
                    <p className="text-gray-800 whitespace-pre-line">
                      {results.overall_stats.ai_feedback}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Improvement Areas and Strengths */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {results.overall_stats.improvement_areas.length > 0 && (
                <div className="bg-white shadow-lg rounded-lg overflow-hidden">
                  <div className="px-6 py-4 bg-red-50">
                    <h3 className="text-xl font-semibold text-red-900">Areas for Improvement</h3>
                  </div>
                  <div className="p-6">
                    <ul className="space-y-4">
                      {results.overall_stats.improvement_areas.map((area, index) => (
                        <li key={index} className="flex items-start space-x-3">
                          <div className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-red-500 mt-2"></div>
                          <div>
                            <span className="font-medium text-gray-900">{area.area}:</span>
                            <p className="text-gray-600">{area.description}</p>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {results.overall_stats.strengths.length > 0 && (
                <div className="bg-white shadow-lg rounded-lg overflow-hidden">
                  <div className="px-6 py-4 bg-green-50">
                    <h3 className="text-xl font-semibold text-green-900">Your Strengths</h3>
                  </div>
                  <div className="p-6">
                    <ul className="space-y-4">
                      {results.overall_stats.strengths.map((strength, index) => (
                        <li key={index} className="flex items-start space-x-3">
                          <div className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-green-500 mt-2"></div>
                          <div>
                            <span className="font-medium text-gray-900">{strength.area}:</span>
                            <p className="text-gray-600">{strength.description}</p>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default BatchAnalysis;
