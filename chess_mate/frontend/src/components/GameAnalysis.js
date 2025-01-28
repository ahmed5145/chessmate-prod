import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import { Loader2, TrendingUp, Target, Clock, Award, Crown, Shield, Zap, BarChart2, AlertTriangle } from "lucide-react";
import { analyzeSpecificGame } from "../services/apiRequests";
import { useTheme } from "../context/ThemeContext";
import { formatDate } from "../utils/dateUtils";
import { useUser } from '../contexts/UserContext';
import LoadingSpinner from './LoadingSpinner';

const GameAnalysis = () => {
  const { gameId } = useParams();
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const navigate = useNavigate();
  const { isDarkMode } = useTheme();
  const { updateCredits } = useUser();

  useEffect(() => {
    const fetchAnalysis = async () => {
      if (!gameId) {
        navigate('/games');
        return;
      }

      try {
        const data = await analyzeSpecificGame(gameId);
        setAnalysis(data);
        toast.success('Analysis loaded successfully!');
      } catch (error) {
        console.error('Error fetching analysis:', error);
        toast.error(error.message || 'Failed to load analysis');
      } finally {
        setLoading(false);
      }
    };

    fetchAnalysis();
  }, [gameId, navigate]);

  const renderSection = (title, content, icon = null) => (
    <div className={`p-6 rounded-lg shadow-md mb-6 ${
      isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'
    }`}>
      <div className="flex items-center gap-2 mb-4">
        {icon}
        <h2 className={`text-xl font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
          {title}
        </h2>
      </div>
      {content}
    </div>
  );

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

  const renderGameOverview = () => (
    <div className="space-y-6">
        {renderFeedbackSource()}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {renderStatistic('Overall Accuracy', 
                analysis.overall_accuracy || 65.0, 
                true,
                analysis.feedback?.source === 'error_fallback' ? 'gray' : 'primary'
            )}
            {renderStatistic('ELO Performance', 
                analysis.elo_performance || 1200,
                false,
                analysis.feedback?.source === 'error_fallback' ? 'gray' : 'primary'
            )}
            {renderStatistic('Game Length', 
                analysis.game_length || 0,
                false,
                analysis.feedback?.source === 'error_fallback' ? 'gray' : 'primary'
            )}
        </div>
        
        <div className="space-y-4">
            <h3 className={`font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                Performance Breakdown
            </h3>
            {renderProgressBar(
                analysis.performance_breakdown?.opening || 65.0, 
                'Opening',
                analysis.feedback?.source === 'error_fallback'
            )}
            {renderProgressBar(
                analysis.performance_breakdown?.middlegame || 65.0, 
                'Middle Game',
                analysis.feedback?.source === 'error_fallback'
            )}
            {renderProgressBar(
                analysis.performance_breakdown?.endgame || 65.0, 
                'End Game',
                analysis.feedback?.source === 'error_fallback'
            )}
        </div>
    </div>
  );

  const renderStatistic = (label, value, percentage = false, color = 'primary') => (
    <div className={`p-4 rounded-lg ${isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
        <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>{label}</p>
        <p className={`text-2xl font-semibold ${
            color === 'gray' 
                ? 'text-gray-400'
                : percentage 
                    ? `text-${color}-500` 
                    : isDarkMode 
                        ? 'text-white' 
                        : 'text-gray-900'
        }`}>
            {percentage ? `${value}%` : value}
        </p>
    </div>
  );

  const renderProgressBar = (value, label, isErrorFallback = false) => (
    <div className="mb-4">
        <div className="flex justify-between mb-1">
            <span className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>{label}</span>
            <span className={`text-sm font-medium ${
                isErrorFallback 
                    ? 'text-gray-400'
                    : isDarkMode 
                        ? 'text-white' 
                        : 'text-gray-900'
            }`}>
                {value}%
            </span>
        </div>
        <div className={`w-full h-2.5 rounded-full ${isDarkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
            <div 
                className={`h-2.5 rounded-full ${isErrorFallback ? 'bg-gray-400' : 'bg-primary-500'}`}
                style={{ width: `${value}%` }}
            ></div>
        </div>
    </div>
  );

  const renderFeedback = (title, score, feedback) => (
    <div className="mb-4">
      <div className="flex items-center justify-between mb-2">
        <span className={`font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>{title}</span>
        <span className={`text-sm ${score >= 70 ? 'text-green-500' : score >= 50 ? 'text-yellow-500' : 'text-red-500'}`}>
          {score}%
        </span>
      </div>
      <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>{feedback}</p>
    </div>
  );

  const renderOpeningAnalysis = () => (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {renderStatistic('Opening Accuracy', analysis.opening_analysis?.accuracy || 65.0, true)}
        {renderStatistic('Book Moves', analysis.opening_analysis?.book_moves || 0)}
      </div>
      {analysis.opening_analysis?.suggestions && (
        <div className="mt-4">
          <h3 className={`font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Opening Assessment
          </h3>
          <ul className={`space-y-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            {analysis.opening_analysis.suggestions.map((suggestion, index) => (
              <li key={index}>{suggestion}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );

  const renderTacticalAnalysis = () => (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {renderStatistic('Tactics Score', analysis.tactical_analysis?.tactics_score || 65.0, true)}
        {renderStatistic('Missed Wins', analysis.tactical_analysis?.missed_wins || 0)}
        {renderStatistic('Critical Mistakes', analysis.tactical_analysis?.critical_mistakes || 0)}
      </div>
      {analysis.tactical_analysis?.suggestions && (
        <div className="mt-4">
          <h3 className={`font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Tactical Assessment
          </h3>
          <ul className={`space-y-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            {analysis.tactical_analysis.suggestions.map((suggestion, index) => (
              <li key={index}>{suggestion}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );

  const renderResourcefulness = () => (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {renderStatistic('Overall Score', analysis.resourcefulness?.overall_score || 65.0, true)}
        {renderStatistic('Defensive Saves', analysis.resourcefulness?.defensive_saves || 0)}
        {renderStatistic('Counter Attacks', analysis.resourcefulness?.counter_attacks || 0)}
      </div>
      {analysis.resourcefulness?.suggestions && (
        <div className="mt-4">
          <h3 className={`font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Resourcefulness Assessment
          </h3>
          <ul className={`space-y-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            {analysis.resourcefulness.suggestions.map((suggestion, index) => (
              <li key={index}>{suggestion}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );

  const renderAdvantage = () => (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {renderStatistic('Conversion Rate', analysis.advantage?.conversion_rate || 65.0, true)}
        {renderStatistic('Missed Wins', analysis.advantage?.missed_wins || 0)}
        {renderStatistic('Winning Positions', analysis.advantage?.winning_positions || 0)}
      </div>
      {analysis.advantage?.suggestions && (
        <div className="mt-4">
          <h3 className={`font-medium mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Advantage Assessment
          </h3>
          <ul className={`space-y-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            {analysis.advantage.suggestions.map((suggestion, index) => (
              <li key={index}>{suggestion}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className={`p-6 text-center ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
        <p>Failed to load analysis. Please try again later.</p>
      </div>
    );
  }

  return (
    <div className={`p-6 ${isDarkMode ? 'bg-gray-900 text-white' : 'bg-white text-gray-900'}`}>
      <div className="max-w-4xl mx-auto">
        {renderSection('Game Overview', renderGameOverview(), <TrendingUp className="h-6 w-6 text-primary-500" />)}
        {renderSection('Opening Analysis', renderOpeningAnalysis(), <Crown className="h-6 w-6 text-primary-500" />)}
        {renderSection('Tactical Analysis', renderTacticalAnalysis(), <Target className="h-6 w-6 text-primary-500" />)}
        {renderSection('Resourcefulness', renderResourcefulness(), <Shield className="h-6 w-6 text-primary-500" />)}
        {renderSection('Advantage', renderAdvantage(), <Award className="h-6 w-6 text-primary-500" />)}
      </div>
    </div>
  );
};

export default GameAnalysis;
