import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ChevronRight,
  PieChart,
  Clock,
  Target,
  Award,
  TrendingUp,
  Brain,
  Zap,
  Crown,
  BarChart2,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Swords,
  BookOpen,
  BarChart,
  Timer,
  Clock4,
  Layout,
  Trophy,
  Coins
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { useTheme } from '../context/ThemeContext';
import { useUser } from '../contexts/UserContext';
import { formatDate, getRelativeTime } from '../utils/dateUtils';
import { fetchDashboardData } from '../services/apiRequests';
import LoadingSpinner from './LoadingSpinner';

const StatCard = ({ title, value, icon: Icon, trend, color = 'indigo' }) => {
  const { isDarkMode } = useTheme();
  const trendColor = trend > 0 ? 'text-green-500' : trend < 0 ? 'text-red-500' : 'text-gray-500';

  return (
    <div className={`p-4 rounded-xl transition-all duration-200 hover:scale-[1.02] ${
      isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'
    } shadow-lg h-full`}>
      <div className="flex items-center justify-between">
        <div className={`p-2 rounded-lg ${isDarkMode ? `bg-${color}-900/30` : `bg-${color}-100`}`}>
          <Icon className={`h-5 w-5 ${isDarkMode ? `text-${color}-400` : `text-${color}-600`}`} />
        </div>
        {trend !== undefined && (
          <div className={`flex items-center ${trendColor}`}>
            <TrendingUp className={`h-4 w-4 ${trend > 0 ? '' : 'rotate-180'} mr-1`} />
            <span className="text-sm font-medium">{Math.abs(trend)}%</span>
          </div>
        )}
      </div>
      <div className="mt-3">
        <h3 className={`text-lg font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>{value}</h3>
        <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>{title}</p>
      </div>
    </div>
  );
};

const QuickAction = ({ title, icon: Icon, description, to, color }) => {
  const { isDarkMode } = useTheme();

  return (
    <Link
      to={to}
      className={`block p-4 rounded-xl transition-all duration-200 hover:scale-[1.02] ${
        isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'
      } shadow-lg h-full`}
    >
      <div className="flex items-center space-x-4">
        <div className={`p-2 rounded-lg ${isDarkMode ? 'bg-gray-700' : 'bg-gray-100'}`}>
          <Icon className={`h-5 w-5 ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`} />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className={`text-sm font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            {title}
          </h3>
          <p className={`text-xs mt-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            {description}
          </p>
        </div>
        <ChevronRight className={`h-4 w-4 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`} />
      </div>
    </Link>
  );
};

const InsightCard = ({ title, insights, icon: Icon }) => {
  const { isDarkMode } = useTheme();

  return (
    <div className={`p-6 rounded-xl ${
      isDarkMode ? 'bg-gray-800' : 'bg-white'
    } shadow-lg`}>
      <div className="flex items-center gap-3 mb-4">
        <Icon className={`h-5 w-5 ${
          isDarkMode ? 'text-indigo-400' : 'text-indigo-600'
        }`} />
        <h3 className={`font-semibold ${
          isDarkMode ? 'text-white' : 'text-gray-900'
        }`}>{title}</h3>
      </div>
      <ul className="space-y-3">
        {insights.map((insight, index) => (
          <li key={index} className="flex items-start gap-2">
            {insight.type === 'success' ? (
              <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 flex-shrink-0" />
            ) : insight.type === 'warning' ? (
              <AlertTriangle className="h-5 w-5 text-yellow-500 mt-0.5 flex-shrink-0" />
            ) : (
              <XCircle className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />
            )}
            <span className={`text-sm ${
              isDarkMode ? 'text-gray-300' : 'text-gray-600'
            }`}>{insight.text}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};

const RecentGameCard = ({ game }) => {
  const { isDarkMode } = useTheme();
  const { user } = useUser();

  return (
    <Link
      to={`/game/${game.id}/analysis`}
      className={`block p-4 rounded-xl transition-all duration-200 hover:scale-[1.01] ${
        isDarkMode
          ? 'bg-gray-700 hover:bg-gray-600'
          : 'bg-gray-50 hover:bg-gray-100'
      }`}
    >
      <div className="flex justify-between items-center">
        <div>
          <div className="flex items-center gap-2">
            <h3 className={`font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              vs {game.opponent || (game.white === user?.username ? game.black : game.white) || 'Unknown'}
            </h3>
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${
              game.result === 'win'
                ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                : game.result === 'loss'
                ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
            }`}>
              {game.result ? game.result.toUpperCase() : 'UNKNOWN'}
            </span>
          </div>
          <p className={`text-sm mt-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            {game.date_played ? (
              <>
                {formatDate(game.date_played)}
                {game.analysis && (
                  <span className="ml-2 text-xs">
                    (Analyzed)
                  </span>
                )}
              </>
            ) : (
              'Date not available'
            )}
          </p>
          <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            {game.opening_name || 'Unknown Opening'}
          </p>
        </div>
        {game.analysis && (
          <div className={`text-right ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            <p className="text-sm font-medium">
              Accuracy: {typeof game.analysis.average_accuracy === 'number' ? (
                <span className={
                  game.analysis.average_accuracy >= 90 ? 'text-green-500' :
                  game.analysis.average_accuracy >= 70 ? 'text-yellow-500' :
                  'text-red-500'
                }>
                  {game.analysis.average_accuracy.toFixed(1)}%
                </span>
              ) : 'N/A'}
            </p>
            <p className="text-xs mt-1">
              {typeof game.analysis.mistakes === 'number' && (
                <span className="mr-2">
                  {game.analysis.mistakes} mistake{game.analysis.mistakes !== 1 ? 's' : ''}
                </span>
              )}
              {typeof game.analysis.blunders === 'number' && (
                <span>
                  {game.analysis.blunders} blunder{game.analysis.blunders !== 1 ? 's' : ''}
                </span>
              )}
            </p>
          </div>
        )}
      </div>
    </Link>
  );
};

// Commenting out RatingsSection for now as ratings are not supported
/*
const RatingsSection = ({ ratings }) => {
  const { isDarkMode } = useTheme();

  const ratingCards = [
    { title: 'Bullet', value: ratings?.bullet || 1200, icon: Timer, color: 'red' },
    { title: 'Blitz', value: ratings?.blitz || 1200, icon: Zap, color: 'orange' },
    { title: 'Rapid', value: ratings?.rapid || 1200, icon: Clock, color: 'green' },
    { title: 'Classical', value: ratings?.classical || 1200, icon: Brain, color: 'blue' }
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {ratingCards.map(({ title, value, icon: Icon, color }) => (
        <StatCard
          key={title}
          title={title}
          value={value}
          icon={Icon}
          color={color}
        />
      ))}
    </div>
  );
};
*/

const Dashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isDarkMode } = useTheme();
  const { user } = useUser();
  const [lastUpdate, setLastUpdate] = useState(Date.now());

  useEffect(() => {
    loadDashboardData();
  }, [lastUpdate]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const data = await fetchDashboardData();
      setDashboardData(data);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const refreshDashboardData = () => {
    setLastUpdate(Date.now());
  };

  useEffect(() => {
    // Listen for game imports and credit updates
    const handleGameImported = () => {
      refreshDashboardData();
    };

    const handleCreditUpdate = () => {
      refreshDashboardData();
    };

    window.addEventListener('game-imported', handleGameImported);
    window.addEventListener('credits-updated', handleCreditUpdate);

    return () => {
      window.removeEventListener('game-imported', handleGameImported);
      window.removeEventListener('credits-updated', handleCreditUpdate);
    };
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <div className={`min-h-screen ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'} flex items-center justify-center`}>
        <div className={`p-6 rounded-xl ${isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'} shadow-lg`}>
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <p className={`text-center ${isDarkMode ? 'text-red-400' : 'text-red-600'}`}>
            {error}
          </p>
          <button
            onClick={loadDashboardData}
            className="mt-4 w-full px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!dashboardData) {
    return null;
  }

  const quickActions = [
    {
      title: 'Analyze Game',
      icon: Crown,
      description: 'Upload and analyze your latest chess game',
      to: '/games',
      color: 'primary'
    },
    {
      title: 'Batch Analysis',
      icon: BarChart,
      description: 'Analyze multiple games for patterns',
      to: '/batch-analysis',
      color: 'violet'
    },
    {
      title: 'View Progress',
      icon: TrendingUp,
      description: 'Check your improvement over time',
      to: '/profile',
      color: 'emerald'
    },
    {
      title: 'Get Credits',
      icon: Award,
      description: 'Purchase credits for game analysis',
      to: '/credits',
      color: 'amber'
    }
  ];

  const insights = [
    {
      title: 'Performance Insights',
      icon: Target,
      insights: [
        {
          type: 'success',
          text: 'Your endgame accuracy has improved by 12% in the last 10 games'
        },
        {
          type: 'warning',
          text: 'Consider working on your opening preparation - recent games show early mistakes'
        },
        {
          type: 'error',
          text: 'Time management needs attention, especially in complex positions'
        }
      ]
    },
    {
      title: 'Recent Achievements',
      icon: Award,
      insights: [
        {
          type: 'success',
          text: 'New personal best: 95% accuracy in your last game!'
        },
        {
          type: 'success',
          text: 'Analyzed 50 games - Keep up the great work!'
        },
        {
          type: 'warning',
          text: 'You\'re close to reaching the next rating milestone'
        }
      ]
    }
  ];

  return (
    <div className={`min-h-screen ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'} py-8`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className={`text-3xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Dashboard
          </h1>
          <p className={`mt-2 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Welcome back, {user?.username}! Here's your chess overview.
          </p>
        </div>

        {/* Commenting out Ratings Section as it's not supported yet */}
        {/*
        <div className="mb-8">
          <h2 className={`text-lg font-semibold mb-4 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Your Ratings
          </h2>
          <RatingsSection ratings={dashboardData?.current_ratings} />
        </div>
        */}

        {/* Quick Actions */}
        <div className="mb-8">
          <h2 className={`text-lg font-semibold mb-4 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Quick Actions
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <QuickAction
              title="Import Games"
              description="Import your games from Chess.com or Lichess"
              icon={BookOpen}
              to="/fetch-games"
            />
            <QuickAction
              title="Game Analysis"
              description="Review your analyzed games"
              icon={Brain}
              to="/games"
            />
            <QuickAction
              title="Performance"
              description="Check your detailed statistics"
              icon={BarChart}
              to="/profile"
            />
            <QuickAction
              title="Achievements"
              description="View your chess achievements"
              icon={Award}
              to="/profile"
            />
          </div>
        </div>

        {/* Stats Overview */}
        <div className="mb-8">
          <h2 className={`text-lg font-semibold mb-4 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Stats Overview
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Total Games"
              value={dashboardData?.total_games || 0}
              icon={Layout}
              color="purple"
            />
            <StatCard
              title="Win Rate"
              value={`${dashboardData?.win_rate || 0}%`}
              icon={Trophy}
              color="green"
            />
            <StatCard
              title="Average Accuracy"
              value={`${dashboardData?.average_accuracy || 0}%`}
              icon={Target}
              color="blue"
            />
            <StatCard
              title="Credits"
              value={dashboardData?.credits || 0}
              icon={Coins}
              color="yellow"
            />
          </div>
        </div>

        {/* Recent Games and Insights */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Recent Games */}
          <div>
            <h2 className={`text-lg font-semibold mb-4 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Recent Games
            </h2>
            <div className="space-y-4">
              {dashboardData?.recent_games?.length > 0 ? (
                dashboardData.recent_games.map((game, index) => (
                  <RecentGameCard key={game.id || index} game={game} />
                ))
              ) : (
                <div className={`p-4 rounded-xl ${isDarkMode ? 'bg-gray-800' : 'bg-gray-100'} text-center`}>
                  <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    No recent games found.{' '}
                    <Link to="/fetch-games" className="text-indigo-500 hover:text-indigo-400">
                      Import your games
                    </Link>
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Insights */}
          <div>
            <h2 className={`text-lg font-semibold mb-4 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Insights
            </h2>
            <InsightCard
              title="Performance Insights"
              icon={PieChart}
              insights={dashboardData?.insights || []}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
