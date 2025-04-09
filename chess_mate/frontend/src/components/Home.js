import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Crown, BarChart, TrendingUp, Award } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useUser } from '../contexts/UserContext';

const Home = () => {
  const { isDarkMode } = useTheme();
  const { user } = useUser();
  const navigate = useNavigate();

  const quickActions = [
    {
      title: 'Analyze Game',
      icon: <Crown className="h-6 w-6 text-primary-500" />,
      description: 'Upload and analyze your latest chess game',
      action: () => navigate('/games'),
    },
    {
      title: 'Batch Analysis',
      icon: <BarChart className="h-6 w-6 text-violet-500" />,
      description: 'Analyze multiple games for patterns and trends',
      action: () => navigate('/batch-analysis'),
    },
    {
      title: 'View Progress',
      icon: <TrendingUp className="h-6 w-6 text-emerald-500" />,
      description: 'Check your improvement over time',
      action: () => navigate('/profile'),
    },
    {
      title: 'Get Credits',
      icon: <Award className="h-6 w-6 text-amber-500" />,
      description: 'Purchase credits for game analysis',
      action: () => navigate('/credits'),
    },
  ];

  return (
    <div className={`min-h-screen ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className={`mb-8 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
          <h1 className="text-3xl font-bold">Welcome back, {user?.username || 'Player'}!</h1>
          <p className={`mt-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            Ready to improve your chess game?
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {quickActions.map((action, index) => (
            <button
              key={index}
              onClick={action.action}
              className={`p-6 rounded-xl text-left transition-all duration-200 transform hover:scale-102 hover:shadow-lg
                ${isDarkMode
                  ? 'bg-gray-800 hover:bg-gray-750 text-white'
                  : 'bg-white hover:bg-gray-50 text-gray-900'}
                border ${isDarkMode ? 'border-gray-700' : 'border-gray-200'}`}
            >
              <div className="flex items-center space-x-4">
                <div className={`p-3 rounded-lg ${isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
                  {action.icon}
                </div>
                <div>
                  <h3 className="font-semibold text-lg">{action.title}</h3>
                  <p className={`text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                    {action.description}
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>

        <div className={`rounded-xl p-8 ${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} border`}>
          <h2 className={`text-2xl font-bold mb-4 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Recent Activity
          </h2>
          <div className={`text-center py-8 ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            <p>Start analyzing games to see your activity here!</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;
