import React, { useEffect, useState } from "react";
import { fetchGameFeedback } from "../services/apiRequests";
import {
  AlertCircle,
  CheckCircle,
  Clock,
  Info,
  Play,
  Target,
  TrendingUp,
  Award,
  Loader,
  AlertTriangle,
  BarChart2,
  Zap,
  ChevronDown,
  ChevronUp,
  XCircle,
  Cpu,
  FileText,
  Flag,
  Swords
} from "lucide-react";
import "./GameFeedback.css";
import { Line } from 'react-chartjs-2';
import { useTheme } from '../context/ThemeContext';

const GameFeedback = ({ gameId }) => {
  const { isDarkMode } = useTheme();
  const [feedback, setFeedback] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState('overview');
  const [chartData, setChartData] = useState(null);

  useEffect(() => {
    const fetchFeedback = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchGameFeedback(gameId);
        
        if (!data) {
          setError("No feedback data available");
          return;
        }
        
        setFeedback(data);
      } catch (err) {
        console.error("Feedback fetch error:", err);
        if (err.response?.status === 429) {
          setError("Analysis is temporarily unavailable due to high demand. Please try again in a few minutes.");
        } else {
          setError("Failed to fetch feedback. Please try again.");
        }
      } finally {
        setLoading(false);
      }
    };

    if (gameId) {
      fetchFeedback();
    }
  }, [gameId]);

  useEffect(() => {
    if (feedback?.moves) {
      const data = {
        labels: feedback.moves.map((_, index) => `Move ${index + 1}`),
        datasets: [
          {
            label: 'Position Evaluation',
            data: feedback.moves.map(move => move.score / 100), // Convert centipawns to pawns
            borderColor: isDarkMode ? 'rgb(96, 165, 250)' : 'rgb(59, 130, 246)',
            backgroundColor: isDarkMode ? 'rgba(96, 165, 250, 0.5)' : 'rgba(59, 130, 246, 0.5)',
            tension: 0.4,
          },
        ],
      };
      setChartData(data);
    }
  }, [feedback, isDarkMode]);

  const renderFeedbackSource = () => {
    const source = feedback?.source;
    if (!source) return null;

    const sourceConfig = {
        'ai': {
            label: 'AI-Generated Analysis',
            color: 'text-blue-600',
            icon: <Cpu className="w-4 h-4 mr-1" />
        },
        'statistical': {
            label: 'Statistical Analysis',
            color: 'text-green-600',
            icon: <BarChart2 className="w-4 h-4 mr-1" />
        },
        'basic': {
            label: 'Basic Analysis',
            color: 'text-gray-600',
            icon: <Info className="w-4 h-4 mr-1" />
        }
    };

    const config = sourceConfig[source] || sourceConfig.basic;

    return (
        <div className="mb-4">
            <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${config.color} bg-opacity-10`}>
                {config.icon}
                {config.label}
            </div>
        </div>
    );
  };

  const renderFeedbackSection = (title, content, icon = null) => {
    if (!content || Object.keys(content).length === 0) {
        return null;
    }

    return (
        <div className="mb-6">
            <h3 className="text-lg font-semibold mb-3 flex items-center">
                {icon && <span className="mr-2">{icon}</span>}
                {title}
            </h3>
            <div className="space-y-3">
                {content.analysis && (
                    <p className="text-gray-700 dark:text-gray-300">{content.analysis}</p>
                )}
                {content.suggestions && content.suggestions.length > 0 && (
                    <ul className="list-disc list-inside space-y-1">
                        {content.suggestions.map((suggestion, index) => (
                            <li key={index} className="text-gray-600 dark:text-gray-400">
                                {suggestion}
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
  };

  if (loading) {
    return (
      <div className="loading-feedback flex items-center justify-center p-8">
        <Loader className="w-6 h-6 animate-spin text-blue-500 mr-3" />
        <span className="text-gray-600">Analyzing your game...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="feedback-error bg-red-50 p-4 rounded-lg flex items-center text-red-800">
        <AlertCircle className="w-5 h-5 mr-2" />
        <div>
          <p className="font-medium">Analysis Error</p>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (!feedback) {
    return (
      <div className="feedback-error bg-yellow-50 p-4 rounded-lg flex items-center text-yellow-800">
        <Info className="w-5 h-5 mr-2" />
        <div>
          <p className="font-medium">No Analysis Available</p>
          <p className="text-sm">Analysis data is not available for this game.</p>
        </div>
      </div>
    );
  }

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: isDarkMode ? '#e5e7eb' : '#374151',
        },
      },
      title: {
        display: true,
        text: 'Game Evaluation Over Time',
        color: isDarkMode ? '#e5e7eb' : '#374151',
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
          color: isDarkMode ? '#e5e7eb' : '#374151',
        },
        grid: {
          color: isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
        },
        ticks: {
          color: isDarkMode ? '#e5e7eb' : '#374151',
        },
      },
      x: {
        grid: {
          color: isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
        },
        ticks: {
          color: isDarkMode ? '#e5e7eb' : '#374151',
        },
      },
    },
  };

  const sections = [
    {
      id: 'overview',
      title: 'Overview',
      icon: TrendingUp,
      content: (
        <div className="space-y-4">
          {renderFeedbackSource()}
          <div className={`p-4 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'} border ${isDarkMode ? 'border-gray-700' : 'border-gray-200'}`}>
            <h3 className={`text-lg font-semibold mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>Summary</h3>
            <p className={`${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>{feedback.summary}</p>
          </div>
          {feedback.key_moments?.length > 0 && (
            <div className={`p-4 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'} border ${isDarkMode ? 'border-gray-700' : 'border-gray-200'}`}>
              <h3 className={`text-lg font-semibold mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>Key Moments</h3>
              <ul className={`list-disc pl-5 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                {feedback.key_moments.map((moment, index) => (
                  <li key={index}>{moment}</li>
                ))}
              </ul>
            </div>
          )}
          {feedback.improvement_areas?.length > 0 && (
            <div className={`p-4 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'} border ${isDarkMode ? 'border-gray-700' : 'border-gray-200'}`}>
              <h3 className={`text-lg font-semibold mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>Areas for Improvement</h3>
              <ul className={`list-disc pl-5 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                {feedback.improvement_areas.map((area, index) => (
                  <li key={index}>{area}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {chartData && (
              <div className={`p-4 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'} border ${isDarkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                <Line data={chartData} options={chartOptions} />
              </div>
            )}
            <div className="space-y-4">
              <div className={`p-4 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'} border ${isDarkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                <h3 className={`text-lg font-semibold mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>Key Statistics</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>Accuracy</p>
                    <p className={`text-xl font-bold ${isDarkMode ? 'text-green-400' : 'text-green-600'}`}>
                      {feedback.overall_accuracy?.toFixed(1) || '0.0'}%
                    </p>
                  </div>
                  <div>
                    <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>Critical Moments</p>
                    <p className={`text-xl font-bold ${isDarkMode ? 'text-blue-400' : 'text-blue-600'}`}>
                      {feedback.moves?.filter(move => move.is_critical).length || 0}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: 'moves',
      title: 'Move Analysis',
      icon: BarChart2,
      content: (
        <div className={`overflow-x-auto ${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-lg border ${isDarkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className={isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}>
              <tr>
                <th scope="col" className={`px-6 py-3 text-left text-xs font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-500'} uppercase tracking-wider`}>Move</th>
                <th scope="col" className={`px-6 py-3 text-left text-xs font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-500'} uppercase tracking-wider`}>Evaluation</th>
                <th scope="col" className={`px-6 py-3 text-left text-xs font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-500'} uppercase tracking-wider`}>Analysis</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDarkMode ? 'divide-gray-700' : 'divide-gray-200'}`}>
              {feedback.moves?.map((move, index) => (
                <tr key={index} className={`${move.is_critical ? (isDarkMode ? 'bg-yellow-900' : 'bg-yellow-50') : ''} hover:bg-opacity-50`}>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-900'}`}>
                    {index + 1}. {move.move}
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm`}>
                    <span className={move.score > 0 ? (isDarkMode ? 'text-green-400' : 'text-green-600') : (isDarkMode ? 'text-red-400' : 'text-red-600')}>
                      {(move.score / 100).toFixed(2)}
                    </span>
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-500'}`}>
                    {move.is_critical && (
                      <span className={`inline-flex items-center ${isDarkMode ? 'text-yellow-400' : 'text-yellow-600'}`}>
                        <AlertTriangle className="w-4 h-4 mr-1" />
                        Critical Position
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ),
    },
    {
      id: 'feedback',
      title: 'AI Feedback',
      icon: Zap,
      content: (
        <div className={`space-y-4 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          {feedback.feedback?.sections?.map((section, index) => (
            <div key={index} className={`p-4 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'} border ${isDarkMode ? 'border-gray-700' : 'border-gray-200'}`}>
              <h3 className={`text-lg font-semibold mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>{section.title}</h3>
              <p>{section.content}</p>
            </div>
          ))}
        </div>
      ),
    },
  ];

  return (
    <div className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <div className="space-y-4">
        {sections.map((section) => (
          <div key={section.id} className={`rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'} overflow-hidden`}>
            <button
              onClick={() => setActiveSection(activeSection === section.id ? null : section.id)}
              className={`w-full px-4 py-3 flex items-center justify-between ${isDarkMode ? 'text-white hover:bg-gray-700' : 'text-gray-900 hover:bg-gray-50'}`}
            >
              <div className="flex items-center space-x-2">
                <section.icon className={`w-5 h-5 ${isDarkMode ? 'text-blue-400' : 'text-blue-600'}`} />
                <span className="font-medium">{section.title}</span>
              </div>
              {activeSection === section.id ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
            </button>
            {activeSection === section.id && (
              <div className="p-4 border-t dark:border-gray-700">
                {section.content}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default GameFeedback;
