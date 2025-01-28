import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { analyzeSpecificGame, checkAnalysisStatus } from '../services/apiRequests';
import GameFeedback from './GameFeedback';
import LoadingSpinner from './LoadingSpinner'; 
import {
  TrendingUp,
  Clock,
  Target,
  Award,
  Sword,
  Crown,
  AlertTriangle,
  Zap,
  BarChart2,
  Loader,
} from 'lucide-react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import './SingleGameAnalysis.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const SingleGameAnalysis = () => {
  const { gameId } = useParams();
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [taskId, setTaskId] = useState(null);
  const [pollingInterval, setPollingInterval] = useState(null);
  const [analysisStatus, setAnalysisStatus] = useState('pending'); // 'pending', 'processing', 'completed', 'failed'
  
  const startPolling = useCallback((taskId) => {
    // Clear any existing interval
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }

    // Start new polling
    const interval = setInterval(async () => {
        try {
            const response = await checkAnalysisStatus(taskId);
            console.log('Polling response:', response); // Debug log
            setAnalysisStatus(response.status);
            
            if (response.status === 'completed' && response.result?.results) {
                // Analysis is complete
                clearInterval(interval);
                setPollingInterval(null);
                setAnalysis(response.result.results);
                setLoading(false);
            } else if (response.status === 'failed') {
                // Analysis failed
                clearInterval(interval);
                setPollingInterval(null);
                setError(response.error || 'Analysis failed');
                setLoading(false);
            }
            // If still processing, continue polling
            
        } catch (err) {
            clearInterval(interval);
            setPollingInterval(null);
            setError(err.message || 'Error checking analysis status');
            setLoading(false);
        }
    }, 2000); // Poll every 2 seconds

    setPollingInterval(interval);
}, [pollingInterval]);

const startAnalysis = useCallback(async () => {
  try {
      setLoading(true);
      setError(null);
      setAnalysis(null);
      setAnalysisStatus('pending');

      const response = await analyzeSpecificGame(gameId);
      console.log('Analysis response:', response); // Debug log
      
      if (response.task_id) {
          setTaskId(response.task_id);
          setAnalysisStatus('processing');
          startPolling(response.task_id);
      } else if (response.analysis) {
          // Recent analysis exists
          setAnalysis(response.analysis);
          setAnalysisStatus('completed');
          setLoading(false);
      } else {
          throw new Error('Invalid response from server');
      }
  } catch (err) {
      console.error('Analysis error:', err); // Debug log
      setError(err.message || 'Failed to start analysis');
      setAnalysisStatus('failed');
      setLoading(false);
  }
}, [gameId, startPolling]);

  useEffect(() => {
    startAnalysis();

    // Cleanup polling on unmount
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [startAnalysis]);

  if (loading || analysisStatus === 'pending' || analysisStatus === 'processing') {
    return <LoadingSpinner message="Analyzing game..." />
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center text-red-600">
          <AlertTriangle className="w-12 h-12 mx-auto mb-4" />
          <h2 className="text-xl font-semibold">{error}</h2>
        </div>
      </div>
    );
  }

  if (!analysis?.analysis) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center text-gray-600">
          <AlertTriangle className="w-12 h-12 mx-auto mb-4" />
          <h2 className="text-xl font-semibold">No analysis data available</h2>
        </div>
      </div>
    );
  }

  const chartData = {
    labels: analysis.analysis.map(move => `Move ${move.move_number}`),
    datasets: [
      {
        label: 'Position Evaluation',
        data: analysis.analysis.map(move => move.score / 100), // Convert centipawns to pawns
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.5)',
        tension: 0.4,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Game Evaluation Over Time',
      },
      tooltip: {
        callbacks: {
          label: (context) => `Evaluation: ${context.raw.toFixed(2)} pawns`,
        },
      },
    },
    scales: {
      y: {
        title: {
          display: true,
          text: 'Evaluation (pawns)',
        },
      },
    },
  };

  const renderFeedbackSource = () => {
    if (!analysis?.feedback?.source) return null;

    const sourceColors = {
      openai_analysis: 'text-green-600',
      statistical_analysis: 'text-blue-600',
      error_fallback: 'text-red-600'
    };

    const sourceLabels = {
      openai_analysis: 'AI-Powered Analysis',
      statistical_analysis: 'Statistical Analysis',
      error_fallback: 'Basic Analysis (Error Recovery)'
    };

    const sourceIcons = {
      openai_analysis: <Zap className="w-4 h-4 mr-1" />,
      statistical_analysis: <BarChart2 className="w-4 h-4 mr-1" />,
      error_fallback: <AlertTriangle className="w-4 h-4 mr-1" />
    };

    return (
      <div className={`flex items-center ${sourceColors[analysis.feedback.source]} text-sm font-medium mb-4`}>
        {sourceIcons[analysis.feedback.source]}
        <span>{sourceLabels[analysis.feedback.source]}</span>
        {analysis.feedback.source === 'error_fallback' && (
          <div className="ml-2 text-xs text-gray-500">
            (Limited analysis available due to processing error)
          </div>
        )}
      </div>
    );
  };

  const renderOverview = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
      <div className="bg-white p-6 rounded-xl shadow-sm">
        <div className="flex items-center mb-4">
          <Award className="w-6 h-6 text-blue-500 mr-2" />
          <h3 className="text-lg font-semibold">Game Statistics</h3>
        </div>
        {renderFeedbackSource()}
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500">Accuracy</p>
            <p className={`text-2xl font-bold ${
              analysis.feedback?.source === 'error_fallback' ? 'text-gray-400' : 'text-blue-600'
            }`}>
              {analysis.feedback?.summary?.accuracy ? 
                `${analysis.feedback.summary.accuracy.toFixed(1)}%` : 
                'N/A'}
            </p>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500">Tactics Score</p>
            <p className={`text-2xl font-bold ${
              analysis.feedback?.source === 'error_fallback' ? 'text-gray-400' : 'text-yellow-600'
            }`}>
              {analysis.tactical_analysis?.tactics_score ? 
                `${analysis.tactical_analysis.tactics_score.toFixed(1)}%` : 
                'N/A'}
            </p>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500">Critical Mistakes</p>
            <p className={`text-2xl font-bold ${
              analysis.feedback?.source === 'error_fallback' ? 'text-gray-400' : 'text-red-600'
            }`}>
              {analysis.feedback?.summary?.mistakes !== undefined ? 
                analysis.feedback.summary.mistakes + analysis.feedback.summary.blunders : 
                'N/A'}
            </p>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500">Avg Time/Move</p>
            <p className={`text-2xl font-bold ${
              analysis.feedback?.source === 'error_fallback' ? 'text-gray-400' : 'text-green-600'
            }`}>
              {analysis.feedback?.time_management?.avg_time_per_move ? 
                `${analysis.feedback.time_management.avg_time_per_move.toFixed(1)}s` : 
                'N/A'}
            </p>
          </div>
        </div>
      </div>

      <div className="bg-white p-6 rounded-xl shadow-sm">
        <div className="flex items-center mb-4">
          <TrendingUp className="w-6 h-6 text-purple-500 mr-2" />
          <h3 className="text-lg font-semibold">Key Insights</h3>
        </div>
        <ul className="space-y-3">
          {analysis.feedback?.tactical_opportunities?.length > 0 ? (
            analysis.feedback.tactical_opportunities.map((opportunity, index) => (
              <li key={index} className="flex items-start">
                <Zap className="w-5 h-5 text-yellow-500 mr-2 flex-shrink-0 mt-0.5" />
                <span className="text-gray-700">
                  {`${opportunity.type === 'blunder' ? 'Blunder' : 'Mistake'} on move ${opportunity.move_number}: ${opportunity.move}`}
                </span>
              </li>
            ))
          ) : (
            <li className="text-gray-500">No tactical opportunities identified.</li>
          )}
        </ul>
      </div>

      {renderTimeManagement()}
      {renderTacticalAnalysis()}
      {renderStatistics()}
    </div>
  );

  const renderMoveList = () => (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <div className="overflow-x-auto">
        <table className="min-w-full">
          <thead>
            <tr className="bg-gray-50">
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Move</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Evaluation</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Notes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {analysis.analysis.map((move, index) => (
              <tr key={index} className={move.is_critical ? 'bg-yellow-50' : ''}>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <span className="text-sm font-medium text-gray-900">{index + 1}.</span>
                    <span className="ml-2 text-sm text-gray-900">{move.move}</span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`text-sm ${move.score > 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {(move.score / 100).toFixed(2)}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {move.time_spent ? `${move.time_spent.toFixed(1)}s` : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {move.is_critical && <span className="text-yellow-600">Critical position</span>}
                  {move.is_check && <span className="text-red-600 ml-2">Check</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderTimeManagement = () => (
    <div className="bg-white p-6 rounded-xl shadow-sm">
      <div className="flex items-center mb-4">
        <Clock className="w-6 h-6 text-green-500 mr-2" />
        <h3 className="text-lg font-semibold">Time Management</h3>
      </div>
      <div className="space-y-4">
        <p className="text-gray-700">
          Average time per move: {
            analysis.feedback?.time_management?.avg_time_per_move ? 
            `${analysis.feedback.time_management.avg_time_per_move.toFixed(1)}s` : 
            'N/A'
          }
        </p>
        <div className="bg-gray-50 p-4 rounded-lg">
          <p className="text-sm text-gray-600">
            {analysis.feedback?.time_management?.suggestion || 'No time management analysis available.'}
          </p>
        </div>
        {analysis.feedback?.time_management?.critical_moments?.length > 0 && (
          <div className="mt-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Critical Moments</h4>
            <div className="space-y-2">
              {analysis.feedback.time_management.critical_moments.map((moment, index) => (
                <div key={index} className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Move {moment.move_number}: {moment.move}</span>
                  <span className="text-gray-500">{moment.time_spent.toFixed(1)}s</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );

  const renderTacticalAnalysis = () => (
    <div className="bg-white p-6 rounded-xl shadow-sm">
      <div className="flex items-center mb-4">
        <Target className="w-6 h-6 text-purple-500 mr-2" />
        <h3 className="text-lg font-semibold">Tactical Analysis</h3>
      </div>
      <div className="space-y-4">
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500">Tactics Score</p>
            <p className="text-xl font-bold text-purple-600">{analysis.tactical_analysis?.tactics_score?.toFixed(1) || '65.0'}%</p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500">Missed Wins</p>
            <p className="text-xl font-bold text-yellow-600">{analysis.tactical_analysis?.missed_wins || 0}</p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500">Critical Mistakes</p>
            <p className="text-xl font-bold text-red-600">{analysis.tactical_analysis?.critical_mistakes || 0}</p>
          </div>
        </div>
      </div>
    </div>
  );

  const renderStatistics = () => (
    <div className="bg-white p-6 rounded-xl shadow-sm">
      <div className="flex items-center mb-4">
        <BarChart2 className="w-6 h-6 text-blue-500 mr-2" />
        <h3 className="text-lg font-semibold">Statistics</h3>
      </div>
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="p-3 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500">Critical Positions</p>
            <p className="text-xl font-bold text-indigo-600">
              {analysis.analysis.filter(move => move.is_critical).length}
            </p>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500">Accuracy</p>
            <p className="text-xl font-bold text-green-600">
              {analysis.overall_accuracy?.toFixed(1) || '65.0'}%
            </p>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center">
          <Sword className="w-8 h-8 mr-3 text-blue-500" />
          Game Analysis
        </h1>
        <p className="mt-2 text-gray-600">
          Analyzed on {new Date(analysis.game_info?.played_at).toLocaleDateString()}
        </p>
      </div>

      <div className="mb-8">
        <div className="bg-white p-6 rounded-xl shadow-sm">
          <Line data={chartData} options={chartOptions} />
        </div>
      </div>

      <div className="mb-6">
        <nav className="flex space-x-4">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-4 py-2 rounded-lg font-medium ${
              activeTab === 'overview'
                ? 'bg-blue-500 text-white'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('moves')}
            className={`px-4 py-2 rounded-lg font-medium ${
              activeTab === 'moves'
                ? 'bg-blue-500 text-white'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            Move List
          </button>
        </nav>
      </div>

      {activeTab === 'overview' ? renderOverview() : renderMoveList()}

      <div className="mt-8 bg-white rounded-xl shadow-sm p-6">
        <div className="flex items-center mb-4">
          <Crown className="w-6 h-6 text-yellow-500 mr-2" />
          <h3 className="text-lg font-semibold">Improvement Suggestions</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="p-4 bg-blue-50 rounded-lg">
              <h4 className="font-medium text-blue-800 mb-2">Opening</h4>
              <p className="text-blue-900">{analysis.feedback?.opening?.suggestion || 'No opening suggestions available.'}</p>
            </div>
            <div className="p-4 bg-green-50 rounded-lg">
              <h4 className="font-medium text-green-800 mb-2">Time Management</h4>
              <p className="text-green-900">{analysis.feedback?.time_management?.suggestion || 'No time management suggestions available.'}</p>
            </div>
          </div>
          <div className="space-y-4">
            <div className="p-4 bg-purple-50 rounded-lg">
              <h4 className="font-medium text-purple-800 mb-2">Tactics</h4>
              <p className="text-purple-900">
                {analysis.tactical_analysis?.suggestions?.length > 0
                  ? "Review the tactical opportunities you missed during the game."
                  : "Good tactical awareness in this game."}
              </p>
            </div>
            <div className="p-4 bg-yellow-50 rounded-lg">
              <h4 className="font-medium text-yellow-800 mb-2">Endgame</h4>
              <p className="text-yellow-900">{analysis.feedback?.endgame?.suggestion || 'No endgame suggestions available.'}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SingleGameAnalysis; 