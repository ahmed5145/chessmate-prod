import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { analyzeSpecificGame, checkAnalysisStatus, fetchGameAnalysis } from '../services/gameAnalysisService';
import GameFeedback from './GameFeedback';
import LoadingSpinner from './LoadingSpinner';
import { debounce } from 'lodash';
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
  Cpu,
  Crosshair,
  AlertCircle,
  AlertOctagon,
  BookOpen,
  Swords,
  Flag,
  FileText,
  BarChart,
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
import { toast } from 'react-hot-toast';

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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const [progress, setProgress] = useState(null);
  const [pollingInterval, setPollingInterval] = useState(null);

  const checkStatus = async () => {
    try {
      console.log('Checking status for task:', taskId);
      const statusResponse = await checkAnalysisStatus(taskId);
      console.log('Status check response:', statusResponse);

      const status = statusResponse.status?.toUpperCase();
      
      if (status === 'COMPLETED') {
        if (statusResponse.analysis) {
          setAnalysis(statusResponse.analysis);
          setLoading(false);
          if (pollingInterval) {
            clearInterval(pollingInterval);
            setPollingInterval(null);
          }
        } else {
          console.error('Analysis completed but no analysis data received');
          setError('Analysis completed but results are missing');
          setLoading(false);
          if (pollingInterval) {
            clearInterval(pollingInterval);
            setPollingInterval(null);
          }
        }
      } else if (status === 'FAILED' || status === 'FAILURE') {
        setError(statusResponse.message || 'Analysis failed');
        setLoading(false);
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
      } else if (status === 'IN_PROGRESS' || status === 'PENDING') {
        // Update progress if available
        if (statusResponse.progress) {
          setProgress(statusResponse.progress);
        }
      } else {
        console.error('Unknown status received:', status);
        setError('Unknown analysis status');
        setLoading(false);
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
      }
    } catch (error) {
      console.error('Error checking analysis status:', error);
      setError(error.message || 'Failed to check analysis status');
      setLoading(false);
      if (pollingInterval) {
        clearInterval(pollingInterval);
        setPollingInterval(null);
      }
    }
  };

  const startAnalysis = async () => {
    try {
      setLoading(true);
      setError(null);
      setAnalysis(null);
      setProgress(null);
      
      const response = await analyzeSpecificGame(gameId);
      
      if (response.task_id) {
        setTaskId(response.task_id);
      } else if (response.analysis) {
        setAnalysis(response.analysis);
        setLoading(false);
      } else {
        throw new Error('Invalid response from analysis request');
      }
    } catch (error) {
      console.error('Error starting analysis:', error);
      setError(error.message || 'Failed to start analysis');
      setLoading(false);
    }
  };

  useEffect(() => {
    if (taskId) {
      const interval = setInterval(checkStatus, 5000);
      setPollingInterval(interval);
      return () => {
        if (interval) {
          clearInterval(interval);
        }
      };
    }
  }, [taskId]);

  if (loading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return (
      <div className="text-red-600 dark:text-red-400 p-4">
        {error}
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="text-gray-600 dark:text-gray-400 p-4">
        No analysis results available
      </div>
    );
  }

  const renderMetricCard = (title, value, description = '', icon = null) => {
    if (value === undefined || value === null) return null;

    return (
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
            {title}
          </h3>
          {icon && <span className="text-gray-500">{icon}</span>}
        </div>
        <div className="mt-2">
          <div className="text-3xl font-bold text-gray-900 dark:text-gray-100">
            {typeof value === 'number' ? value.toFixed(1) : value}
          </div>
          {description && (
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {description}
            </p>
          )}
        </div>
      </div>
    );
  };

  const renderFeedbackSection = (title, items) => {
    if (!items || items.length === 0) return null;

    return (
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm">
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
          {title}
        </h3>
        <ul className="space-y-2">
          {items.map((item, index) => (
            <li
              key={index}
              className="flex items-start text-gray-600 dark:text-gray-300"
            >
              <span className="mr-2">•</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>
    );
  };

  const renderSourceBadge = (source) => {
    const sourceConfig = {
      ai: {
        label: 'AI Analysis',
        color: 'bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100',
        icon: <Cpu className="w-4 h-4 mr-1" />
      },
      statistical: {
        label: 'Statistical',
        color: 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100',
        icon: <BarChart className="w-4 h-4 mr-1" />
      },
      default: {
        label: 'Basic',
        color: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100',
        icon: <FileText className="w-4 h-4 mr-1" />
      }
    };

    const config = sourceConfig[source] || sourceConfig.default;

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color}`}>
        {config.icon}
        {config.label}
      </span>
    );
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
              Game Analysis
            </h1>
            <p className="mt-2 text-gray-600 dark:text-gray-300">
              {analysis.summary}
            </p>
          </div>
          <div className="flex space-x-2">
            {analysis.source && renderSourceBadge(analysis.source)}
          </div>
        </div>

        {/* Overall Performance */}
        <section>
          <h2 className="text-2xl font-bold mb-4">Overall Performance</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {renderMetricCard(
              'Accuracy',
              analysis.metrics?.accuracy,
              'Overall playing accuracy',
              <Target className="w-6 h-6" />
            )}
            {renderMetricCard(
              'Critical Moves',
              analysis.metrics?.critical_moves,
              'Key decision points',
              <Crosshair className="w-6 h-6" />
            )}
            {renderMetricCard(
              'Time Management',
              analysis.metrics?.time_score,
              'Time usage efficiency',
              <Clock className="w-6 h-6" />
            )}
          </div>
        </section>

        {/* Mistakes Analysis */}
        <section>
          <h2 className="text-2xl font-bold mb-4">Mistakes Analysis</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {renderMetricCard(
              'Blunders',
              analysis.metrics?.blunders,
              'Serious mistakes',
              <AlertTriangle className="w-6 h-6" />
            )}
            {renderMetricCard(
              'Mistakes',
              analysis.metrics?.mistakes,
              'Regular mistakes',
              <AlertCircle className="w-6 h-6" />
            )}
            {renderMetricCard(
              'Inaccuracies',
              analysis.metrics?.inaccuracies,
              'Minor imprecisions',
              <AlertOctagon className="w-6 h-6" />
            )}
          </div>
        </section>

        {/* Game Phases */}
        <section>
          <h2 className="text-2xl font-bold mb-4">Game Phases</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {renderMetricCard(
              'Opening',
              analysis.phases?.opening?.accuracy,
              analysis.phases?.opening?.evaluation,
              <BookOpen className="w-6 h-6" />
            )}
            {renderMetricCard(
              'Middlegame',
              analysis.phases?.middlegame?.accuracy,
              analysis.phases?.middlegame?.evaluation,
              <Swords className="w-6 h-6" />
            )}
            {renderMetricCard(
              'Endgame',
              analysis.phases?.endgame?.accuracy,
              analysis.phases?.endgame?.evaluation,
              <Flag className="w-6 h-6" />
            )}
          </div>
        </section>

        {/* Feedback Sections */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {renderFeedbackSection('Tactical Analysis', analysis.tactical_feedback)}
          {renderFeedbackSection('Positional Analysis', analysis.positional_feedback)}
          {renderFeedbackSection('Time Management', analysis.time_management_feedback)}
          {renderFeedbackSection('Improvement Areas', analysis.improvement_areas)}
        </div>
      </div>
    </div>
  );
};

export default SingleGameAnalysis; 