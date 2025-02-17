import React, { useState, useContext, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { UserContext } from '../contexts/UserContext';
import { useTheme } from '../context/ThemeContext';
import { toast } from 'react-hot-toast';
import { fetchExternalGames, fetchProfileData } from '../services/apiRequests';
import { Coins, AlertCircle, UserCircle, Loader2 } from 'lucide-react';
import LoadingSpinner from './LoadingSpinner';

const FetchGames = () => {
  const [platform, setPlatform] = useState('chess.com');
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [gameMode, setGameMode] = useState('all');
  const [numGames, setNumGames] = useState(10);
  const { credits, refreshUserData } = useContext(UserContext);
  const { isDarkMode } = useTheme();
  const navigate = useNavigate();
  const [linkedAccounts, setLinkedAccounts] = useState(null);

  // Function to fetch user's profile data
  const loadProfileData = async () => {
    try {
      const data = await fetchProfileData();
      const accounts = {
        chesscom: data.chesscom_username,
        lichess: data.lichess_username
      };
      setLinkedAccounts(accounts);
      
      // Auto-fill username based on current platform
      const platformUsername = platform === 'chess.com' ? accounts.chesscom : accounts.lichess;
      if (platformUsername) {
        setUsername(platformUsername);
      }
    } catch (error) {
      console.error('Error fetching profile:', error);
      toast.error('Failed to load profile data');
    }
  };

  // Fetch profile data on mount and when platform changes
  useEffect(() => {
    loadProfileData();
  }, [platform]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetchExternalGames(platform, username, gameMode, numGames);
      
      if (response && response.message) {
        toast.success(response.message);
      } else if (response && typeof response.saved === 'number') {
        toast.success(`Successfully imported ${response.saved} ${gameMode} games`);
      } else {
        toast.success('Games imported successfully');
      }
      
      await loadProfileData();
      navigate('/games');
    } catch (error) {
      console.error('Error fetching games:', error);
      toast.error(error.message || 'Failed to fetch games');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 ${isDarkMode ? 'bg-gray-900' : 'bg-white'}`}>
      <div className="sm:flex sm:flex-col sm:align-center mb-8">
        <h2 className={`text-3xl font-extrabold ${isDarkMode ? 'text-white' : 'text-gray-900'} sm:text-center`}>
          Import Chess Games
        </h2>
        <p className={`mt-2 text-lg ${isDarkMode ? 'text-gray-300' : 'text-gray-500'} sm:text-center`}>
          Import your games from Chess.com or Lichess
        </p>
      </div>

      {/* Credits Display */}
      <div className={`mb-8 p-4 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-gray-50'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Coins className={`h-5 w-5 ${credits < numGames ? 'text-red-500' : 'text-green-500'}`} />
            <span className={`font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Available Credits: {credits}
            </span>
          </div>
          <div className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            Required Credits: {numGames}
          </div>
        </div>
        {credits < numGames && (
          <div className="mt-2 flex items-start space-x-2">
            <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm text-red-500">
                Insufficient credits. You need {numGames - credits} more credits to import {numGames} games.
              </p>
              <Link
                to="/credits"
                className="mt-2 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                Purchase Credits
              </Link>
            </div>
          </div>
        )}
      </div>

      {/* Main Form */}
      <div className={`p-6 rounded-lg ${isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'} shadow-lg`}>
        <form onSubmit={handleSubmit} className={`space-y-6 p-6 rounded-lg shadow-lg ${
              isDarkMode 
                ? 'bg-gray-800 border border-gray-700' 
                : 'bg-white border border-gray-200'
            }`}>
          {/* Platform Selection */}
          <div>
            <label className={`block text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Platform
            </label>
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className={`mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md ${
                isDarkMode ? 'bg-gray-700 text-white border-gray-600' : 'bg-white'
              }`}
            >
              <option value="chess.com">Chess.com</option>
              <option value="lichess">Lichess</option>
            </select>
          </div>

          {/* Username Input */}
          <div>
            <label className={`block text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Username
            </label>
            <div className="mt-1 relative rounded-md shadow-sm">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <UserCircle className={`h-5 w-5 ${isDarkMode ? 'text-gray-400' : 'text-gray-400'}`} />
              </div>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className={`block w-full pl-10 sm:text-sm rounded-md ${
                  isDarkMode
                    ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                    : 'border-gray-300 placeholder-gray-400'
                } focus:ring-indigo-500 focus:border-indigo-500`}
                placeholder={`Enter your ${platform} username`}
              />
            </div>
          </div>

          {/* Game Mode Selection */}
          <div>
            <label className={`block text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Game Mode
            </label>
            <select
              value={gameMode}
              onChange={(e) => setGameMode(e.target.value)}
              className={`mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md ${
                isDarkMode ? 'bg-gray-700 text-white border-gray-600' : 'bg-white'
              }`}
            >
              <option value="all">All Games</option>
              <option value="bullet">Bullet</option>
              <option value="blitz">Blitz</option>
              <option value="rapid">Rapid</option>
              <option value="classical">Classical</option>
            </select>
          </div>

          {/* Number of Games Input */}
          <div>
            <label className={`block text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Number of Games
            </label>
            <input
              type="number"
              min="1"
              max="100"
              value={numGames}
              onChange={(e) => setNumGames(parseInt(e.target.value))}
              className={`mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md ${
                isDarkMode ? 'bg-gray-700 text-white border-gray-600' : 'bg-white'
              }`}
            />
          </div>

          {/* Submit Button */}
          <div>
            <button
              type="submit"
              disabled={loading || credits < numGames}
              className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
                loading || credits < numGames
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500'
              }`}
            >
              {loading ? (
                <>
                  <Loader2 className="animate-spin -ml-1 mr-2 h-5 w-5" />
                  Importing Games...
                </>
              ) : (
                'Import Games'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default FetchGames;
