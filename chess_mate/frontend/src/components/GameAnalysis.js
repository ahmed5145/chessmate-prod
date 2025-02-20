import React, { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import { TrendingUp, Target, Award, Crown, Shield, Zap, BarChart2, AlertTriangle, Layout, Brain, Clock, CheckCircle, XCircle, Info, ChevronDown, ChevronUp, ArrowUpCircle, Flag, Lightbulb, BookOpen, GraduationCap, AlertCircle } from "lucide-react";
import { analyzeSpecificGame, checkAnalysisStatus, fetchGameAnalysis } from "../services/apiRequests";
import { useTheme } from "../context/ThemeContext";
import { useUser } from '../contexts/UserContext';
import { Loader } from './Loader';
import LoadingSpinner from './LoadingSpinner';

const GameAnalysis = ({ onComplete }) => {
  const { gameId } = useParams();
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const [progress, setProgress] = useState(0);
  const [analysisStarted, setAnalysisStarted] = useState(false);
  const navigate = useNavigate();
  const { isDarkMode } = useTheme();
  const { updateCredits } = useUser();
  const [expandedSections, setExpandedSections] = useState({});

  // Add refs to track polling state
  const pollingIntervalRef = useRef(null);
  const isPollingRef = useRef(false);

  const renderStatistic = (label, value, isPercentage = false, tooltip = '', color = 'primary') => (
    <div className={`p-4 rounded-lg bg-${color}-800/50 hover:bg-${color}-800/70 transition-all duration-200 group relative`}>
      <h3 className="text-sm font-medium text-gray-400">{label}</h3>
      <p className={`mt-2 text-3xl font-semibold text-${color}-100`}>
        {isPercentage ? `${value.toFixed(1)}%` : value}
      </p>
      {tooltip && (
        <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
          <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-1 bg-gray-900 text-white text-sm rounded-md whitespace-nowrap">
            {tooltip}
          </div>
        </div>
      )}
    </div>
  );

  const renderStrengthsAndWeaknesses = (summary) => {
    if (!summary || (!summary.strengths && !summary.weaknesses)) return null;

    return (
      <div className="mt-6 space-y-6">
        {summary.strengths && summary.strengths.length > 0 && (
          <div>
            <h4 className="text-lg font-semibold text-green-500 dark:text-green-400 mb-2">Strengths</h4>
            <ul className="list-disc list-inside space-y-2">
              {summary.strengths.map((strength, index) => (
                <li key={index} className="text-gray-700 dark:text-gray-300">{strength}</li>
              ))}
            </ul>
          </div>
        )}
        {summary.weaknesses && summary.weaknesses.length > 0 && (
          <div>
            <h4 className="text-lg font-semibold text-red-500 dark:text-red-400 mb-2">Areas for Improvement</h4>
            <ul className="list-disc list-inside space-y-2">
              {summary.weaknesses.map((weakness, index) => (
                <li key={index} className="text-gray-700 dark:text-gray-300">{weakness}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  const renderFeedbackSection = (title, content, icon = null) => {
    const isExpanded = expandedSections[title] ?? true;
    return (
      <div className={`mb-6 rounded-lg border ${isDarkMode ? 'border-gray-700 bg-gray-800/50' : 'border-gray-200 bg-white'} overflow-hidden transition-all duration-300`}>
        <button
          onClick={() => toggleSection(title)}
          className={`w-full px-6 py-4 flex items-center justify-between ${isDarkMode ? 'hover:bg-gray-700/50' : 'hover:bg-gray-50'}`}
        >
          <div className="flex items-center space-x-3">
            {icon}
            <h3 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              {title}
            </h3>
          </div>
          <ChevronDown
            className={`w-5 h-5 transform transition-transform ${isExpanded ? 'rotate-180' : ''} ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}
          />
        </button>
        {isExpanded && (
          <div className="px-6 py-4 border-t border-gray-700">
            {content}
          </div>
        )}
      </div>
    );
  };

  const renderOverallPerformance = () => {
    const feedback = analysis?.feedback;
    const metrics = feedback?.metrics;

    if (!feedback || !metrics) return null;

    const overallContent = (
      <div className="space-y-6">
        {/* Overall Evaluation */}
        {feedback.overall_performance?.evaluation && (
          <div className={`p-4 rounded-lg ${isDarkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
            <p className={`text-lg ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              {feedback.overall_performance.evaluation}
            </p>
          </div>
        )}

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {renderStatistic('Accuracy', metrics.accuracy, true)}
          {renderStatistic('Tactical Success', metrics.tactical_success_rate, true)}
          {renderStatistic('Position Score', metrics.positional_score, true)}
          {renderStatistic('Time Management', metrics.time_management_score, true)}
        </div>

        {/* Strengths and Weaknesses */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Strengths */}
          <div className={`p-4 rounded-lg ${isDarkMode ? 'bg-green-900/20' : 'bg-green-50'}`}>
            <h4 className={`text-lg font-semibold mb-3 ${isDarkMode ? 'text-green-400' : 'text-green-700'}`}>
              Strengths
            </h4>
            <ul className="space-y-2">
              {feedback.overall_performance.strengths.map((strength, index) => (
                <li key={index} className={`flex items-start ${isDarkMode ? 'text-green-300' : 'text-green-600'}`}>
                  <CheckCircle className="w-5 h-5 mr-2 mt-0.5 flex-shrink-0" />
                  <span>{strength}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Weaknesses */}
          <div className={`p-4 rounded-lg ${isDarkMode ? 'bg-red-900/20' : 'bg-red-50'}`}>
            <h4 className={`text-lg font-semibold mb-3 ${isDarkMode ? 'text-red-400' : 'text-red-700'}`}>
              Areas for Improvement
            </h4>
            <ul className="space-y-2">
              {feedback.overall_performance.weaknesses.map((weakness, index) => (
                <li key={index} className={`flex items-start ${isDarkMode ? 'text-red-300' : 'text-red-600'}`}>
                  <AlertCircle className="w-5 h-5 mr-2 mt-0.5 flex-shrink-0" />
                  <span>{weakness}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Key Moments */}
        {feedback.overall_performance.key_moments?.length > 0 && (
          <div className={`p-4 rounded-lg ${isDarkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
            <h4 className={`text-lg font-semibold mb-3 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Key Moments
            </h4>
            <ul className="space-y-2">
              {feedback.overall_performance.key_moments.map((moment, index) => (
                <li key={index} className={`flex items-start ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                  <Flag className="w-5 h-5 mr-2 mt-0.5 flex-shrink-0" />
                  <span>{moment}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );

    return renderFeedbackSection('Overall Performance', overallContent, <Target className="w-6 h-6" />);
  };

  const renderPhaseAnalysis = (phase, icon) => {
    const feedback = analysis?.feedback;
    if (!feedback || !feedback[phase]) return null;

    const phaseData = feedback[phase];
    const content = (
      <div className="space-y-4">
        {/* Analysis */}
        {phaseData.analysis && (
          <div className={`p-4 rounded-lg ${isDarkMode ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
            <p className={`${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              {phaseData.analysis}
            </p>
          </div>
        )}

        {/* Suggestions */}
        {phaseData.suggestions?.length > 0 && (
          <div className="mt-4">
            <h4 className={`text-lg font-semibold mb-3 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Suggestions
            </h4>
            <ul className="space-y-2">
              {phaseData.suggestions.map((suggestion, index) => (
                <li key={index} className={`flex items-start ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                  <Lightbulb className="w-5 h-5 mr-2 mt-0.5 flex-shrink-0" />
                  <span>{suggestion}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );

    return renderFeedbackSection(
      phase.charAt(0).toUpperCase() + phase.slice(1),
      content,
      icon
    );
  };

  const renderStudyPlan = () => {
    const feedback = analysis?.feedback;
    if (!feedback?.study_plan) return null;

    const content = (
      <div className="space-y-6">
        {/* Focus Areas */}
        <div>
          <h4 className={`text-lg font-semibold mb-3 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Focus Areas
          </h4>
          <ul className="space-y-2">
            {feedback.study_plan.focus_areas.map((area, index) => (
              <li key={index} className={`flex items-start ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                <Target className="w-5 h-5 mr-2 mt-0.5 flex-shrink-0" />
                <span>{area}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Exercises */}
        <div>
          <h4 className={`text-lg font-semibold mb-3 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Recommended Exercises
          </h4>
          <ul className="space-y-2">
            {feedback.study_plan.exercises.map((exercise, index) => (
              <li key={index} className={`flex items-start ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                <BookOpen className="w-5 h-5 mr-2 mt-0.5 flex-shrink-0" />
                <span>{exercise}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    );

    return renderFeedbackSection('Study Plan', content, <GraduationCap className="w-6 h-6" />);
  };

  const pollStatus = async (taskId) => {
    try {
      console.log('Polling for status of task:', taskId);
      const response = await checkAnalysisStatus(taskId);
      console.log('Poll response:', response);

      // Normalize status to uppercase for consistent comparison
      const status = response.status.toUpperCase();
      console.log('Normalized status:', status);

      if (status === 'COMPLETED' || status === 'SUCCESS') {
        console.log('Analysis completed, fetching results');
        clearInterval(pollingIntervalRef.current);
        
        try {
          const analysisData = await fetchGameAnalysis(gameId);
          if (analysisData) {
            setAnalysis(analysisData);
            setLoading(false);
            toast.success('Analysis completed!', { id: 'analysis-progress' });
            navigate(`/game/${gameId}/analysis/results`);
          } else {
            throw new Error('No analysis data received');
          }
        } catch (error) {
          console.error('Error fetching analysis data:', error);
          setError('Failed to fetch analysis results');
          setLoading(false);
          toast.error('Failed to fetch analysis results', { id: 'analysis-progress' });
        }
      } else if (status === 'FAILED' || status === 'FAILURE') {
        console.error('Analysis failed:', response.message);
        clearInterval(pollingIntervalRef.current);
        setError(response.message || 'Analysis failed');
        setLoading(false);
        toast.error('Analysis failed', { id: 'analysis-progress' });
      } else {
        // Continue polling for pending/in-progress status
        console.log('Analysis in progress, continuing to poll');
        if (response.progress) {
          toast.loading(`Analysis in progress: ${response.progress}%`, { id: 'analysis-progress' });
        }
      }
    } catch (error) {
      console.error('Error polling status:', error);
      clearInterval(pollingIntervalRef.current);
      setError('Failed to check analysis status');
      setLoading(false);
      toast.error('Failed to check analysis status', { id: 'analysis-progress' });
    }
  };

  const setupPolling = (taskId) => {
    console.log('Setting up polling for task:', taskId);
    
    // Clear any existing polling interval
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    // Start polling immediately
    pollStatus(taskId);

    // Then continue polling every 5 seconds
    pollingIntervalRef.current = setInterval(() => pollStatus(taskId), 5000);
  };

  const startAnalysis = async () => {
    try {
      setLoading(true);
      setAnalysisStarted(true);
      console.log('Starting analysis for game:', gameId);

      const response = await analyzeSpecificGame(gameId);
      console.log('Analysis response:', response);

      // Extract taskId from response, handling both new and existing tasks
      const taskId = response.taskId;
      
      if (!taskId) {
        throw new Error('No task ID received from server');
      }

      // Show appropriate toast message based on whether it's an existing task
      if (response.isExistingTask) {
        toast.loading('Resuming existing analysis...', { id: 'analysis-progress' });
      } else {
        toast.loading('Starting new analysis...', { id: 'analysis-progress' });
      }

      // Start polling with the task ID
      setupPolling(taskId);

    } catch (error) {
      console.error('Error starting analysis:', error);
      setError(error.message || 'Failed to start analysis');
      setLoading(false);
      setAnalysisStarted(false);
      toast.error(error.message || 'Failed to start analysis', { id: 'analysis-progress' });
    }
  };

  // Start analysis when component mounts
  useEffect(() => {
    if (gameId && !analysisStarted) {
      startAnalysis();
    }
  }, [gameId, analysisStarted]);

  // Add simulated progress
  useEffect(() => {
    let progressInterval;
    if (loading && progress < 90) {
      progressInterval = setInterval(() => {
        setProgress(prev => {
          // Simulate different phases of analysis
          if (prev < 30) return prev + 2; // Opening analysis (faster)
          if (prev < 60) return prev + 1; // Middlegame analysis (medium)
          if (prev < 90) return prev + 0.5; // Endgame analysis (slower)
          return prev;
        });
      }, 500);
    }
    return () => clearInterval(progressInterval);
  }, [loading, progress]);

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const renderSection = (title, content, icon = null) => {
    const isExpanded = expandedSections[title] ?? true;
    return (
      <div className={`mb-6 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg overflow-hidden transition-all duration-200`}>
        <button
          onClick={() => toggleSection(title)}
          className={`w-full px-6 py-4 flex items-center justify-between ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-50'}`}
        >
          <div className="flex items-center space-x-3">
            {icon}
            <h3 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              {title}
            </h3>
          </div>
          {isExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
        </button>
        {isExpanded && (
          <div className={`px-6 py-4 ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            {content}
          </div>
        )}
      </div>
    );
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

  const renderGameOverview = () => {
    if (!analysis?.feedback?.summary) return null;
    const summary = analysis.feedback.summary;

    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Target className="h-5 w-5" />
            Game Overview
          </h3>
        </div>
        <div className="prose dark:prose-invert max-w-none">
          <p className="text-gray-700 dark:text-gray-300 text-lg mb-6">{summary.evaluation}</p>
          {renderStrengthsAndWeaknesses(summary)}
          </div>
      </div>
    );
  };

  const renderOpeningAnalysis = () => {
    const feedback = analysis?.feedback || {};
    const metrics = feedback?.metrics?.phases?.opening || {};

    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {renderStatistic('Opening Accuracy', metrics.accuracy || 0, true)}
          {renderStatistic('Critical Moves', metrics.critical_moves || 0)}
        </div>
        
        {metrics?.moves?.length > 0 && (
          <div className="mt-4">
            <h3 className={`font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Opening Moves
            </h3>
            <div className={`flex flex-wrap gap-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              {metrics.moves.map((move, index) => (
                <span key={index} className={`px-2 py-1 rounded ${isDarkMode ? 'bg-gray-700' : 'bg-gray-100'}`}>
                  {move}
                </span>
              ))}
            </div>
          </div>
        )}
        
        {feedback.opening?.suggestion && (
          <div className="mt-4">
            <h3 className={`font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Opening Assessment
            </h3>
            <p className={`${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              {feedback.opening.suggestion}
            </p>
          </div>
        )}
      </div>
    );
  };

  const renderTacticalAnalysis = () => {
    const feedback = analysis?.feedback;
    const tactics = feedback?.tactics;

    if (!feedback || !tactics) return null;

    const tacticalStats = [
      {
        label: 'Opportunities',
        value: tactics.opportunities,
        tooltip: 'Total number of tactical opportunities in the game'
      },
      {
        label: 'Successful',
        value: tactics.successful,
        tooltip: 'Number of successfully executed tactical moves'
      },
      {
        label: 'Brilliant Moves',
        value: tactics.brilliant_moves || 0,
        tooltip: 'Exceptional moves that significantly improve the position'
      },
      {
        label: 'Success Rate',
        value: `${tactics.success_rate}%`,
        tooltip: 'Percentage of tactical opportunities successfully executed'
      },
      {
        label: 'Tactical Score',
        value: `${tactics.tactical_score}%`,
        tooltip: 'Overall tactical performance score'
      },
      {
        label: 'Pattern Recognition',
        value: `${tactics.pattern_recognition || 0}%`,
        tooltip: 'Score based on recognizing and executing tactical patterns'
      }
    ];

    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {tacticalStats.map((stat, index) => (
            <div key={index}>
              {renderStatistic(stat.label, stat.value, false, stat.tooltip)}
        </div>
          ))}
        </div>

        {tactics.analysis && (
          <div className={`mt-4 p-4 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-gray-50'}`}>
            <h3 className={`font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Tactical Analysis
            </h3>
            <p className={`${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              {tactics.analysis}
            </p>
    </div>
        )}

        {tactics.suggestions?.length > 0 && (
          <div className="mt-4">
            <h3 className={`font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Tactical Suggestions
            </h3>
            <ul className={`list-disc list-inside space-y-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              {tactics.suggestions.map((suggestion, index) => (
                <li key={index} className="ml-4">{suggestion}</li>
        ))}
      </ul>
    </div>
        )}

        {tactics.critical_moments?.length > 0 && (
          <div className="mt-4">
            <h3 className={`font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Critical Tactical Moments
            </h3>
            <div className="space-y-2">
              {tactics.critical_moments.map((moment, index) => (
                <div key={index} className={`p-3 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'}`}>
                  <p className={`font-medium ${isDarkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                    Move {moment.move_number}
                  </p>
                  <p className={`mt-1 ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                    {moment.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderEndgameAnalysis = () => {
    const feedback = analysis?.feedback || {};
    const metrics = feedback?.metrics?.phases?.endgame || {};

    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {renderStatistic('Endgame Accuracy', metrics.accuracy || 0, true)}
          {renderStatistic('Critical Moves', metrics.critical_moves || 0)}
          {renderStatistic('Conversion Rate', metrics.moves_count || 0, true)}
        </div>
        
        {feedback.endgame?.suggestion && (
          <div className="mt-4">
            <h3 className={`font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Endgame Assessment
            </h3>
            <p className={`${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              {feedback.endgame.suggestion}
            </p>
          </div>
        )}
      </div>
    );
  };

  const renderTimeManagement = () => {
    const feedback = analysis?.feedback;
    const timeMetrics = feedback?.time_management;

    if (!feedback || !timeMetrics) return null;

    const timeStats = [
      {
        label: 'Average Time',
        value: `${(timeMetrics.average_time || 0).toFixed(1)}s`,
        tooltip: 'Average time spent per move'
      },
      {
        label: 'Time Pressure',
        value: `${(timeMetrics.time_pressure_percentage || 0)}%`,
        tooltip: 'Percentage of moves made under time pressure'
      },
      {
        label: 'Time Consistency',
        value: `${(timeMetrics.time_consistency || 0)}%`,
        tooltip: 'How consistently time was managed throughout the game'
      },
      {
        label: 'Critical Time Average',
        value: `${(timeMetrics.critical_time_average || 0).toFixed(1)}s`,
        tooltip: 'Average time spent on critical moves'
      },
      {
        label: 'Management Score',
        value: `${(timeMetrics.time_management_score || 0)}%`,
        tooltip: 'Overall time management performance score'
      }
    ];

    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {timeStats.map((stat, index) => (
            <div key={index}>
              {renderStatistic(stat.label, stat.value, false, stat.tooltip)}
        </div>
          ))}
        </div>

        {timeMetrics.analysis && (
          <div className={`mt-4 p-4 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-gray-50'}`}>
            <h3 className={`font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Time Management Analysis
            </h3>
            <p className={`${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              {timeMetrics.analysis}
            </p>
          </div>
        )}

        {feedback.phases && (
          <div className="mt-6">
            <h4 className={`text-lg font-medium mb-4 ${isDarkMode ? 'text-gray-200' : 'text-gray-800'}`}>
              Time Management by Phase
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(feedback.phases).map(([phase, data]) => (
                <div key={phase} className={`p-4 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'}`}>
                  <h4 className={`text-md font-medium mb-2 capitalize ${isDarkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                    {phase}
                  </h4>
                  <div className="space-y-2">
                    {renderStatistic('Avg Time', `${((data.time_management?.average_time) || 0).toFixed(1)}s`, false, 'Average time per move in this phase', 'sm')}
                    {renderStatistic('Pressure %', `${(data.time_management?.time_pressure_percentage || 0)}%`, false, 'Percentage of moves under time pressure in this phase', 'sm')}
                    {renderStatistic('Consistency', `${(data.time_management?.time_consistency || 0)}%`, false, 'Time management consistency in this phase', 'sm')}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {timeMetrics.suggestions?.length > 0 && (
          <div className="mt-4">
            <h3 className={`font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Time Management Suggestions
            </h3>
            <ul className={`list-disc list-inside space-y-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              {timeMetrics.suggestions.map((suggestion, index) => (
                <li key={index} className="ml-4">{suggestion}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  const renderResourcefulness = () => {
    const feedback = analysis?.feedback;
    const metrics = feedback?.resourcefulness;

    if (!feedback || !metrics) return null;

    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {renderStatistic('Defensive Score', `${metrics.defensive_score}%`)}
          {renderStatistic('Counter Play', `${metrics.counter_play}%`)}
          {renderStatistic('Recovery Rate', `${metrics.recovery_rate}%`)}
          {renderStatistic('Critical Defense', `${metrics.critical_defense}%`)}
          {renderStatistic('Best Move Finding', `${metrics.best_move_finding}%`)}
        </div>
      </div>
    );
  };

  const renderAdvantageMetrics = () => {
    const feedback = analysis?.feedback;
    const advantage = feedback?.advantage;

    if (!feedback || !advantage) return null;

    const advantageStats = [
      {
        label: 'Max Advantage',
        value: `${(advantage.max_advantage || 0).toFixed(1)}`,
        tooltip: 'Maximum advantage achieved in pawn units'
      },
      {
        label: 'Avg Advantage',
        value: `${(advantage.average_advantage || 0).toFixed(1)}`,
        tooltip: 'Average advantage maintained throughout the game'
      },
      {
        label: 'Winning Positions',
        value: advantage.winning_positions || 0,
        tooltip: 'Number of positions with significant advantage (>2 pawns)'
      },
      {
        label: 'Advantage Retention',
        value: `${(advantage.advantage_retention || 0)}%`,
        tooltip: 'Percentage of advantage maintained in winning positions'
      },
      {
        label: 'Conversion Rate',
        value: `${(advantage.advantage_conversion || 0)}%`,
        tooltip: 'Success rate in converting advantages into concrete gains'
      },
      {
        label: 'Pressure Handling',
        value: `${(advantage.pressure_handling || 0)}%`,
        tooltip: 'Effectiveness in handling positions under pressure'
      }
    ];

    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {advantageStats.map((stat, index) => (
            <div key={index}>
              {renderStatistic(stat.label, stat.value, false, stat.tooltip)}
        </div>
          ))}
        </div>

        {advantage.analysis && (
          <div className={`mt-4 p-4 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-gray-50'}`}>
            <h3 className={`font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Advantage Analysis
            </h3>
            <p className={`${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              {advantage.analysis}
            </p>
          </div>
        )}

        {advantage.critical_positions?.length > 0 && (
          <div className="mt-4">
            <h3 className={`font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Critical Advantage Positions
            </h3>
            <div className="space-y-2">
              {advantage.critical_positions.map((position, index) => (
                <div key={index} className={`p-3 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'}`}>
                  <p className={`font-medium ${isDarkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                    Move {position.move_number}
                  </p>
                  <p className={`mt-1 ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                    Advantage: {position.advantage.toFixed(1)} pawns
                  </p>
                  <p className={`mt-1 ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                    {position.description}
          </p>
        </div>
              ))}
            </div>
          </div>
        )}

        {advantage.trend_analysis && (
          <div className={`mt-4 p-4 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-gray-50'}`}>
            <h3 className={`font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Advantage Trend
            </h3>
            <p className={`${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              {advantage.trend_analysis}
            </p>
        </div>
        )}
        
        {advantage.improvement_areas?.length > 0 && (
        <div className="mt-4">
            <h3 className={`font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Areas for Improvement
            </h3>
            <ul className={`list-disc list-inside space-y-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              {advantage.improvement_areas.map((area, index) => (
                <li key={index} className="ml-4">{area}</li>
              ))}
            </ul>
        </div>
        )}
      </div>
    );
  };

  const renderImprovementAreas = () => {
    const feedback = analysis?.feedback || {};
    
    return (
      <div className="space-y-4">
        {feedback.improvement_areas?.map((area, index) => (
          <div key={index} className="space-y-2">
            <h3 className={`font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              {area.title}
            </h3>
            <p className={`${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              {area.details}
            </p>
          </div>
        ))}
      </div>
    );
  };

  if (loading) {
    return (
      <div className={`min-h-screen ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'} py-12`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className={`text-center ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            <LoadingSpinner size="large" />
            <h2 className="mt-4 text-xl font-semibold">Analyzing your game...</h2>
            <p className={`mt-2 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              This may take a few moments
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`min-h-screen ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'} py-12`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className={`text-center ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            <XCircle className="mx-auto h-12 w-12 text-red-500" />
            <h2 className="mt-4 text-xl font-semibold">Analysis Failed</h2>
            <p className={`mt-2 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              {error}
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className={`min-h-screen ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'} py-12`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className={`text-center ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            <Info className="mx-auto h-12 w-12 text-yellow-500" />
            <h2 className="mt-4 text-xl font-semibold">No Analysis Available</h2>
            <p className={`mt-2 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Analysis data is not available for this game
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'} py-12`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className={`text-3xl font-bold mb-8 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
          Game Analysis
        </h1>

        {renderFeedbackSource()}

        {renderFeedbackSection('Game Overview', renderGameOverview(), 
          <Layout className={`h-6 w-6 ${isDarkMode ? 'text-primary-400' : 'text-primary-500'}`} />
        )}

        {renderFeedbackSection('Opening Analysis', renderOpeningAnalysis(),
          <Crown className={`h-6 w-6 ${isDarkMode ? 'text-emerald-400' : 'text-emerald-500'}`} />
        )}

        {renderFeedbackSection('Tactical Analysis', renderTacticalAnalysis(),
          <Target className={`h-6 w-6 ${isDarkMode ? 'text-red-400' : 'text-red-500'}`} />
        )}

        {renderFeedbackSection('Endgame Analysis', renderEndgameAnalysis(),
          <Award className={`h-6 w-6 ${isDarkMode ? 'text-yellow-400' : 'text-yellow-500'}`} />
        )}

        {renderFeedbackSection('Resourcefulness', renderResourcefulness(),
          <Shield className={`h-6 w-6 ${isDarkMode ? 'text-violet-400' : 'text-violet-500'}`} />
        )}

        {renderFeedbackSection('Advantage', renderAdvantageMetrics(),
          <Award className={`h-6 w-6 ${isDarkMode ? 'text-pink-400' : 'text-pink-500'}`} />
        )}

        {renderFeedbackSection('Time Management', renderTimeManagement(),
          <Clock className={`h-6 w-6 ${isDarkMode ? 'text-yellow-400' : 'text-yellow-500'}`} />
        )}

        {renderFeedbackSection('Improvement Areas', renderImprovementAreas(),
          <TrendingUp className={`h-6 w-6 ${isDarkMode ? 'text-violet-400' : 'text-violet-500'}`} />
        )}

        {renderFeedbackSection('Study Plan', renderStudyPlan(),
          <GraduationCap className={`h-6 w-6 ${isDarkMode ? 'text-pink-400' : 'text-pink-500'}`} />
        )}
      </div>
    </div>
  );
};

export default GameAnalysis;