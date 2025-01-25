import React, { useState, useEffect, useContext } from 'react';
import { Link } from 'react-router-dom';
import { UserContext } from '../contexts/UserContext';
import { ChevronRight, PieChart, Clock, Target, Award } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { useTheme } from '../context/ThemeContext';
import { formatDate, getRelativeTime } from '../utils/dateUtils';
import { fetchUserGames } from '../api';


// API Configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://3.133.97.72/api';


const Dashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const { credits } = useContext(UserContext);
  const { isDarkMode } = useTheme();

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const accessToken = localStorage.getItem('tokens') ? JSON.parse(localStorage.getItem('tokens')).access : null;
      if (!accessToken) {
        toast.error('Please log in to view your dashboard');
        return;
      }

      const response = await fetch(`${API_BASE_URL}/dashboard/`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch dashboard data');
      }

      const data = await response.json();
      setDashboardData(data);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className={`p-6 ${isDarkMode ? 'bg-gray-900 text-white' : 'bg-white text-gray-900'}`}>
      <h1 className={`text-3xl font-bold mb-8 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
        Dashboard
      </h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className={`p-6 rounded-lg shadow-md ${
          isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'
        }`}>
          <h2 className={`text-xl font-semibold mb-4 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Recent Games
          </h2>
          {dashboardData?.recent_games?.length === 0 ? (
            <p className={`text-center py-4 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              No games analyzed yet
            </p>
          ) : (
            <div className="space-y-4">
              {dashboardData.recent_games.map((game) => (
                <Link
                  key={game.id}
                  to={`/game/${game.id}/analysis`}
                  className={`block p-4 rounded-lg transition-colors ${
                    isDarkMode
                      ? 'bg-gray-700 hover:bg-gray-600'
                      : 'bg-gray-50 hover:bg-gray-100'
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className={`font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                        Game #{game.id}
                      </h3>
                      <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        Analyzed {getRelativeTime(game.played_at)}
                      </p>
                    </div>
                    <div className={`text-right ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      <p className="text-sm">
                        Accuracy: {game.accuracy ? `${game.accuracy}%` : 'N/A'}
                      </p>
                      <p className="text-sm">
                        {game.mistakes} mistakes, {game.blunders} blunders
                      </p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className={`p-6 rounded-lg shadow-md ${
          isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'
        }`}>
          <h2 className={`text-xl font-semibold mb-4 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Statistics
          </h2>
          <div className="space-y-4">
            <div className={`p-4 rounded-lg ${
              isDarkMode ? 'bg-gray-700' : 'bg-gray-50'
            }`}>
              <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Total Games Analyzed
              </p>
              <p className={`text-2xl font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                {dashboardData?.total_games || 0}
              </p>
            </div>
            <div className={`p-4 rounded-lg ${
              isDarkMode ? 'bg-gray-700' : 'bg-gray-50'
            }`}>
              <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Average Accuracy
              </p>
              <p className={`text-2xl font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                {dashboardData?.statistics?.win_rate ? `${dashboardData.statistics.win_rate}%` : 'N/A'}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="text-center">
        <Link
          to="/games"
          className={`inline-flex items-center px-6 py-3 rounded-lg font-medium transition-colors ${
            isDarkMode
              ? 'bg-primary-600 hover:bg-primary-700 text-white'
              : 'bg-primary-500 hover:bg-primary-600 text-white'
          }`}
        >
          View All Games
        </Link>
      </div>
    </div>
  );
};

export default Dashboard;
