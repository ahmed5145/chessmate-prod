import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Filter, Search } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { analyzeSpecificGame, checkAnalysisStatus, fetchGameAnalysis, fetchUserGames } from '../services/apiRequests';
import { useTheme } from '../context/ThemeContext';

// API Configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://3.133.97.72/api';

const Games = () => {
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [analysisStatus, setAnalysisStatus] = useState({});
  const [selectedGame, setSelectedGame] = useState(null);
  const [showAnalysisModal, setShowAnalysisModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: 'date', direction: 'desc' });
  const [filters, setFilters] = useState({
    result: 'all',
    timeRange: 'all',
    analyzed: 'all'
  });
  const { isDarkMode } = useTheme();

  // Polling interval for analysis status (5 seconds)
  const POLLING_INTERVAL = 5000;

  useEffect(() => {
    fetchGamesData();
  }, []);

  useEffect(() => {
    // Set up polling for games with pending analysis
    const pollingIntervals = {};

    games.forEach(game => {
      if (game.analysis_status === 'pending' && !pollingIntervals[game.id]) {
        pollingIntervals[game.id] = setInterval(async () => {
          try {
            const status = await checkAnalysisStatus(game.id);
            
            setAnalysisStatus(prev => ({
              ...prev,
              [game.id]: status
            }));

            if (status === 'completed') {
              // Clear the polling interval
              clearInterval(pollingIntervals[game.id]);
              delete pollingIntervals[game.id];

              // Fetch the analysis results
              const analysis = await fetchGameAnalysis(game.id);
              setGames(prev => prev.map(g => 
                g.id === game.id ? { ...g, analysis } : g
              ));

              toast.success('Analysis completed!');
            } else if (status === 'failed') {
              // Clear the polling interval
              clearInterval(pollingIntervals[game.id]);
              delete pollingIntervals[game.id];

              toast.error('Analysis failed. Please try again.');
            }
          } catch (error) {
            console.error(`Error checking analysis status for game ${game.id}:`, error);
            // Don't clear the interval on network errors, let it retry
            if (error.response?.status === 404 || error.response?.status === 400) {
              clearInterval(pollingIntervals[game.id]);
              delete pollingIntervals[game.id];
              toast.error('Analysis failed. Please try again.');
            }
          }
        }, POLLING_INTERVAL);
      }
    });

    // Cleanup intervals
    return () => {
      Object.values(pollingIntervals).forEach(interval => clearInterval(interval));
    };
  }, [games]);

  const fetchGamesData = async () => {
    try {
      const gamesData = await fetchUserGames();
      const cleanedGames = gamesData.map(game => ({
        ...game,
        opponent: game.opponent.replace(/^vs\s+/, '')
      }));
      setGames(cleanedGames);
    } catch (error) {
      console.error('Error fetching games:', error);
      toast.error(error.message || 'Failed to load games. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeGame = async (gameId) => {
    try {
      setAnalysisStatus(prev => ({
        ...prev,
        [gameId]: 'pending'
      }));

      const toastId = `analysis-${gameId}`;
      toast.loading('Starting analysis...', { id: toastId });

      await analyzeSpecificGame(gameId);
      
      toast.success('Analysis started!', { id: toastId });

      // The polling effect will handle the status updates
    } catch (error) {
      console.error('Error starting analysis:', error);
      
      setAnalysisStatus(prev => ({
        ...prev,
        [gameId]: 'failed'
      }));

      toast.error(error.message || 'Failed to start analysis');
    }
  };

  // Filter and sort games
  const filteredAndSortedGames = games
    .filter(game => {
      // First apply search filter
      if (searchTerm) {
        const searchLower = searchTerm.toLowerCase();
        return (
          game.opponent.toLowerCase().includes(searchLower) ||
          game.opening_name?.toLowerCase().includes(searchLower) ||
          game.result.toLowerCase().includes(searchLower)
        );
      }
      // Then apply analysis filter
      if (filters.analyzed === 'analyzed') return game.analysis;
      if (filters.analyzed === 'unanalyzed') return !game.analysis;
      return true;
    })
    .sort((a, b) => {
      if (sortConfig.key === 'date') {
        return new Date(b.played_at) - new Date(a.played_at);
      }
      if (sortConfig.key === 'result') {
        const resultOrder = { win: 0, draw: 1, loss: 2 };
        return resultOrder[a.result.toLowerCase()] - resultOrder[b.result.toLowerCase()];
      }
      return 0;
    });

  const getResultBadgeColor = (result, isDarkMode) => {
    const lowerResult = result.toLowerCase();
    switch (lowerResult) {
      case 'win':
        return isDarkMode ? 'bg-green-900 text-green-200' : 'bg-green-100 text-green-800';
      case 'loss':
        return isDarkMode ? 'bg-red-900 text-red-200' : 'bg-red-100 text-red-800';
      case 'draw':
        return isDarkMode ? 'bg-yellow-900 text-yellow-200' : 'bg-yellow-100 text-yellow-800';
      default:
        return isDarkMode ? 'bg-gray-700 text-gray-200' : 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (played_at) => {
    const date = new Date(played_at);
    return date.toLocaleDateString();
  };

  return (
    <div className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 ${isDarkMode ? 'bg-gray-900' : 'bg-white'}`}>
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className={`text-3xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>My Games</h1>
          <p className={`mt-2 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-700'}`}>
            A list of all your chess games, including their results and analysis status.
            {games.length > 0 && ` Total games: ${games.length}`}
          </p>
        </div>
        <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
          <Link
            to="/fetch-games"
            className={`inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white
              ${isDarkMode 
                ? 'bg-indigo-600 hover:bg-indigo-700' 
                : 'bg-indigo-600 hover:bg-indigo-700'}`}
          >
            Import Games
          </Link>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="mt-8 flex flex-col sm:flex-row items-center gap-4">
        <div className="relative flex-1">
          <Search className={`absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`} />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search games..."
            className={`pl-10 block w-full rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm h-10
              ${isDarkMode 
                ? 'bg-gray-800 border-gray-700 text-white placeholder-gray-400' 
                : 'border-gray-300 text-gray-900 placeholder-gray-500'}`}
          />
        </div>
        <div className="relative w-full sm:w-48">
          <Filter className={`absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`} />
          <select
            value={filters.analyzed}
            onChange={(e) => setFilters({ ...filters, analyzed: e.target.value })}
            className={`pl-10 block w-full rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm h-10
              ${isDarkMode 
                ? 'bg-gray-800 border-gray-700 text-white' 
                : 'border-gray-300 text-gray-900'}`}
          >
            <option value="all">All Games</option>
            <option value="analyzed">Analyzed Games</option>
            <option value="unanalyzed">Unanalyzed Games</option>
          </select>
        </div>
        <div className="relative w-full sm:w-48">
          <select
            value={sortConfig.key}
            onChange={(e) => setSortConfig({ ...sortConfig, key: e.target.value })}
            className={`block w-full rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm h-10
              ${isDarkMode
                ? 'bg-gray-800 border-gray-700 text-white'
                : 'border-gray-300 text-gray-900'}`}
          >
            <option value="date">Sort by Date</option>
            <option value="result">Sort by Result</option>
          </select>
        </div>
      </div>

      <div className="mt-8 flex flex-col">
        <div className="-my-2 -mx-4 overflow-x-auto sm:-mx-6 lg:-mx-8">
          <div className="inline-block min-w-full py-2 align-middle md:px-6 lg:px-8">
            {loading ? (
              <div className="text-center py-12">
                <div className="spinner"></div>
                <p className={`mt-4 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>Loading games...</p>
              </div>
            ) : filteredAndSortedGames.length > 0 ? (
              <div className={`overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg
                ${isDarkMode ? 'bg-gray-800' : 'bg-white'}`}>
                <table className="min-w-full divide-y divide-gray-300">
                  <thead className={isDarkMode ? 'bg-gray-700' : 'bg-gray-50'}>
                    <tr>
                      <th scope="col" className={`py-3.5 pl-4 pr-3 text-left text-sm font-semibold ${isDarkMode ? 'text-gray-200' : 'text-gray-900'} sm:pl-6`}>
                        Opponent
                      </th>
                      <th scope="col" className={`px-3 py-3.5 text-left text-sm font-semibold ${isDarkMode ? 'text-gray-200' : 'text-gray-900'}`}>
                        Opening
                      </th>
                      <th scope="col" className={`px-3 py-3.5 text-left text-sm font-semibold ${isDarkMode ? 'text-gray-200' : 'text-gray-900'}`}>
                        Date
                      </th>
                      <th scope="col" className={`px-3 py-3.5 text-left text-sm font-semibold ${isDarkMode ? 'text-gray-200' : 'text-gray-900'}`}>
                        Result
                      </th>
                      <th scope="col" className={`px-3 py-3.5 text-left text-sm font-semibold ${isDarkMode ? 'text-gray-200' : 'text-gray-900'}`}>
                        Status
                      </th>
                      <th scope="col" className="relative py-3.5 pl-3 pr-4 sm:pr-6">
                        <span className="sr-only">Actions</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody className={`divide-y ${isDarkMode ? 'divide-gray-700 bg-gray-800' : 'divide-gray-200 bg-white'}`}>
                    {filteredAndSortedGames.map((game) => (
                      <tr key={`${game.id}-${game.played_at}`} className={isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-50'}>
                        <td className={`whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'} sm:pl-6`}>
                          {game.opponent}
                        </td>
                        <td className={`whitespace-nowrap px-3 py-4 text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-500'}`}>
                          {game.opening_name || 'Unknown Opening'}
                        </td>
                        <td className={`whitespace-nowrap px-3 py-4 text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-500'}`}>
                          {formatDate(game.played_at)}
                        </td>
                        <td className="whitespace-nowrap px-3 py-4 text-sm">
                          <span className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${getResultBadgeColor(game.result, isDarkMode)}`}>
                            {game.result}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-3 py-4 text-sm">
                          {game.analysis ? (
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                              ${isDarkMode ? 'bg-green-900 text-green-200' : 'bg-green-100 text-green-800'}`}>
                              Analyzed
                            </span>
                          ) : (
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                              ${isDarkMode ? 'bg-gray-700 text-gray-200' : 'bg-gray-100 text-gray-800'}`}>
                              Not Analyzed
                            </span>
                          )}
                        </td>
                        <td className="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                          <Link
                            to={`/analysis/${game.id}`}
                            className={`text-indigo-600 hover:text-indigo-900 ${isDarkMode ? 'text-indigo-400 hover:text-indigo-300' : ''}`}
                          >
                            View Analysis
                            <span className="sr-only">, game {game.id}</span>
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-12">
                <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                  No games found. Try adjusting your filters or import some games.
                </p>
                <Link
                  to="/fetch-games"
                  className={`mt-3 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white
                    ${isDarkMode 
                      ? 'bg-indigo-600 hover:bg-indigo-700' 
                      : 'bg-indigo-600 hover:bg-indigo-700'}`}
                >
                  Import Games
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Games; 
