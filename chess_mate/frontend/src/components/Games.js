import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Filter, Search, ChevronLeft, ChevronRight, Swords, CheckCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { checkAnalysisStatus, fetchGameAnalysis, fetchUserGames } from '../services/apiRequests';
import { checkMultipleAnalysisStatuses, analyzeSpecificGame } from '../services/gameAnalysisService';
import { useTheme } from '../context/ThemeContext';
import { Box, CircularProgress, Typography, Card, CardContent, Grid } from '@mui/material';
import { formatDate } from '../utils/dateUtils';
import { checkAuthStatus } from '../services/authService';

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
  const [currentPage, setCurrentPage] = useState(1);
  const [gamesPerPage] = useState(10);
  const { isDarkMode, isAuthenticated } = useTheme();
  const navigate = useNavigate();

  // Filter and sort games
  const filteredAndSortedGames = games
    .filter(game => {
      // First apply search filter
      if (searchTerm) {
        const searchLower = searchTerm.toLowerCase();
        return (
          (game.opponent || '').toLowerCase().includes(searchLower) ||
          (game.opening_name || '').toLowerCase().includes(searchLower) ||
          (game.result || '').toLowerCase().includes(searchLower)
        );
      }
      // Then apply analysis filter
      if (filters.analyzed === 'analyzed') return !!game.analysis;
      if (filters.analyzed === 'unanalyzed') return !game.analysis;
      return true;
    })
    .sort((a, b) => {
      if (sortConfig.key === 'date') {
        const dateA = new Date(a.played_at || a.date_played || 0);
        const dateB = new Date(b.played_at || b.date_played || 0);
        return sortConfig.direction === 'desc' ? dateB - dateA : dateA - dateB;
      }
      if (sortConfig.key === 'result') {
        const resultOrder = { win: 0, draw: 1, loss: 2 };
        const resultA = resultOrder[(a.result || '').toLowerCase()] ?? 3;
        const resultB = resultOrder[(b.result || '').toLowerCase()] ?? 3;
        return sortConfig.direction === 'desc' ? resultB - resultA : resultA - resultB;
      }
      return 0;
    });

  // Calculate pagination values
  const totalGames = filteredAndSortedGames.length;
  const totalPages = Math.ceil(totalGames / gamesPerPage);
  const startIndex = (currentPage - 1) * gamesPerPage;
  const endIndex = startIndex + gamesPerPage;
  const currentGames = filteredAndSortedGames.slice(startIndex, endIndex);

  // Generate page numbers array
  const pageNumbers = [];
  for (let i = 1; i <= totalPages; i++) {
    pageNumbers.push(i);
  }

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, filters, sortConfig]);

  // Polling interval for analysis status (10 seconds)
  const POLLING_INTERVAL = 10000;

  useEffect(() => {
    loadGames();
  }, []);

  // Helper function to determine if a game should be polled
  const shouldPollGame = (game) => {
    // Don't poll if we don't have a game ID
    if (!game.id) return false;
    
    // Only poll games that are explicitly marked for analysis and in a pending state
    const isPending = game.analysis_status === 'pending' || game.status === 'pending';
    
    // Don't poll games that are already analyzed, have errors, or marked as not_analyzed
    const isAnalyzedOrError = game.analysis_status === 'analyzed' || 
                             game.analysis_status === 'error' ||
                             game.analysis_status === 'not_analyzed' ||
                             game.status === 'analyzed' ||
                             game.status === 'error' ||
                             game.status === 'not_analyzed';
                             
    return isPending && !isAnalyzedOrError;
  };

  // Set up polling for games with pending analysis
  useEffect(() => {
    // Clear any existing polling intervals
    if (window._batchPollingInterval) {
      clearInterval(window._batchPollingInterval);
      window._batchPollingInterval = null;
    }
    
    // Get all games that need polling
    const gamesToPoll = games.filter(shouldPollGame);
    
    if (gamesToPoll.length === 0) {
      console.log('No games need polling');
      return;
    }
    
    console.log(`Setting up batch polling for ${gamesToPoll.length} games`);
    
    // Set error count tracking
    const errorCounts = {};
    gamesToPoll.forEach(game => {
      errorCounts[game.id] = 0;
    });
    
    // Set up a single interval to check all games at once
    window._batchPollingInterval = setInterval(async () => {
      try {
        // Get all game IDs that still need polling
        // Re-filter the games array to check if state has been updated
        const currentGamesToCheck = games.filter(shouldPollGame).map(game => game.id);
        
        if (currentGamesToCheck.length === 0) {
          console.log('No more games need polling, clearing interval');
          clearInterval(window._batchPollingInterval);
          window._batchPollingInterval = null;
          return;
        }
        
        // Check all games at once
        const statuses = await checkMultipleAnalysisStatuses(currentGamesToCheck);
        
        // Track if any game state was updated
        let stateUpdated = false;
        
        // Process each status
        Object.entries(statuses).forEach(([gameId, status]) => {
          gameId = parseInt(gameId); // Convert string ID to number if needed
          
          // Update status in state
            setAnalysisStatus(prev => ({
              ...prev,
            [gameId]: status
          }));
          
          // Process status and update games accordingly
          if (status.status === 'COMPLETED' || status.status === 'ERROR' || 
              status.status === 'AUTH_ERROR' || status.status === 'FAILED') {
            
            if (status.status === 'COMPLETED') {
              toast.success(`Analysis completed for game ${gameId}`);
              
              // Update the games list with the completed analysis
              setGames(prev => prev.map(g =>
                g.id === gameId ? { ...g, analysis_status: 'analyzed', analysis: status.analysis } : g
              ));
              stateUpdated = true;
            } else if (status.status === 'ERROR' || status.status === 'FAILED') {
              // Don't show error toast for every game
              console.warn(`Analysis failed for game ${gameId}: ${status.message}`);
              
              // Update game status to reflect failure
              setGames(prev => prev.map(g => 
                g.id === gameId ? { ...g, analysis_status: 'error' } : g
              ));
              stateUpdated = true;
            }
            
            // Reset error count
            errorCounts[gameId] = 0;
          } else if (status.status === 'PENDING' && status.message?.includes('not started')) {
            // Increment error count for games with no analysis
            errorCounts[gameId] = (errorCounts[gameId] || 0) + 1;
            
            if (errorCounts[gameId] >= 3) {
              console.log(`Game ${gameId} has no analysis after 3 checks, marking as not_analyzed`);
              
              // Update game status to prevent future polling
              setGames(prev => {
                const updatedGames = prev.map(g => 
                  g.id === gameId ? { ...g, analysis_status: 'not_analyzed' } : g
                );
                return updatedGames;
              });
              stateUpdated = true;
              
              // Also remove from error counts to avoid processing it again
              delete errorCounts[gameId];
            }
          }
        });
        
        // If state was updated, make sure we check if we should still be polling at all
        if (stateUpdated) {
          // Re-check if any games still need polling
          setTimeout(() => {
            const remainingGames = games.filter(shouldPollGame);
            if (remainingGames.length === 0) {
              console.log('No more games need polling after state update, clearing interval');
              clearInterval(window._batchPollingInterval);
              window._batchPollingInterval = null;
            }
          }, 100); // Small delay to ensure state has updated
        }
      } catch (error) {
        console.error('Error in batch polling:', error);
      }
    }, POLLING_INTERVAL);
    
    // Cleanup on unmount
    return () => {
      if (window._batchPollingInterval) {
        clearInterval(window._batchPollingInterval);
        window._batchPollingInterval = null;
      }
    };
  }, [games]);

  const loadGames = async () => {
    setLoading(true);
    try {
      const gamesResponse = await fetchUserGames();
      // Handle ViewSet response format which has results array
      if (gamesResponse.results) {
        console.log('Games response:', gamesResponse.results);
        setGames(gamesResponse.results);
      } else if (Array.isArray(gamesResponse)) {
        console.log('Games response:', gamesResponse);
        setGames(gamesResponse);
      } else {
        console.log('Games response:', []);
        setGames([]);
      }
    } catch (error) {
      console.error('Error loading games:', error);
      toast.error(error.message || 'Failed to load games');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeGame = async (gameId) => {
    try {
      // Check authentication
      const isLoggedIn = await checkAuthStatus();
      if (!isLoggedIn) {
        toast.error('Please login to analyze games');
        navigate('/login');
        return;
      }
      
      // Create unique toast ID for this analysis
      const toastId = `analyze-game-${gameId}`;
      
      // Show loading toast with more descriptive message
      toast.loading('Starting game analysis...', {
        id: toastId,
        position: 'top-center',
        closeOnClick: false,
        draggable: false,
        duration: 3000, // Auto close after 3 seconds as we're navigating away
      });

      // Start the analysis in the background and navigate immediately
      try {
        // Fire and forget the analysis request - we'll navigate to analysis page regardless
        analyzeSpecificGame(gameId)
          .then(() => {
            // If successful, dismiss the loading toast and show success toast
            toast.dismiss(toastId);
            toast.success('Analysis started! Redirecting to analysis page...', {
              id: `${toastId}-success`,
              duration: 2000
            });
          })
          .catch(error => {
            console.error('Error starting analysis (background):', error);
            // Only show error if we haven't navigated away yet
            toast.dismiss(toastId);
            toast.error('Error starting analysis. Please try again.', {
              id: `${toastId}-error`,
              duration: 3000
            });
          });
        
        // Navigate to the analysis page immediately
        console.log(`Navigating to analysis page for game ${gameId}`);
        navigate(`/game/${gameId}/analysis`);
      } catch (error) {
        console.error('Error starting analysis:', error);
        toast.dismiss(toastId);
        toast.error('Failed to start analysis. Please try again.', {
          id: `${toastId}-error`,
          duration: 3000
        });
      }
    } catch (error) {
      console.error('Error in handleAnalyzeGame:', error);
      toast.error('An unexpected error occurred. Please try again.');
    }
  };

  const getResultBadgeColor = (result, isDarkMode) => {
    if (!result) return isDarkMode ? 'bg-gray-700 text-gray-200' : 'bg-gray-100 text-gray-800';
    
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

  const formatGameResult = (result) => {
    if (!result) return 'UNKNOWN';
    return result.toUpperCase();
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress />
      </Box>
    );
  }

  if (games.length === 0) {
    return (
      <div className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 ${isDarkMode ? 'bg-gray-900' : 'bg-white'}`}>
        <div className="text-center">
          <div className={`p-8 rounded-xl ${isDarkMode ? 'bg-gray-800' : 'bg-gray-50'} max-w-2xl mx-auto`}>
            <div className="mb-6">
              <Swords className={`h-12 w-12 mx-auto ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`} />
            </div>
            <h2 className={`text-2xl font-bold mb-4 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Welcome to Your Games
            </h2>
            <p className={`mb-6 ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
              Start by importing your games from Chess.com or Lichess. Once imported, you'll be able to:
            </p>
            <ul className={`text-left mb-8 space-y-3 ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
              <li className="flex items-center">
                <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
                Analyze your games with our advanced AI
              </li>
              <li className="flex items-center">
                <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
                Track your progress and improvement
              </li>
              <li className="flex items-center">
                <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
                Get personalized insights and recommendations
              </li>
            </ul>
            <div className="space-y-4">
              <Link
                to="/fetch-games"
                className={`inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 w-full justify-center`}
              >
                Import Your Games
              </Link>
              <Link
                to="/profile"
                className={`inline-flex items-center px-6 py-3 border text-base font-medium rounded-md w-full justify-center ${
                  isDarkMode
                    ? 'border-gray-700 text-gray-300 hover:bg-gray-700'
                    : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
              >
                Link Chess Platforms
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

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
            {filteredAndSortedGames.length > 0 ? (
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
                    {currentGames.map((game) => (
                      <tr key={`${game.id}-${game.played_at}`} className={isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-50'}>
                        <td className={`whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'} sm:pl-6`}>
                          {game.opponent}
                        </td>
                        <td className={`whitespace-nowrap px-3 py-4 text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-500'}`}>
                          {game.opening_name || 'Unknown Opening'}
                        </td>
                        <td className={`whitespace-nowrap px-3 py-4 text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-500'}`}>
                          {new Date(game.date_played).toLocaleDateString()}
                        </td>
                        <td className="whitespace-nowrap px-3 py-4 text-sm">
                          <span className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${getResultBadgeColor(game.result || 'unknown', isDarkMode)}`}>
                            {formatGameResult(game.result)}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-3 py-4 text-sm">
                          {(game.status === 'analyzed' || game.analysis_status === 'analyzed') ? (
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                              ${isDarkMode ? 'bg-green-900 text-green-200' : 'bg-green-100 text-green-800'}`}>
                              Analyzed
                            </span>
                          ) : (
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                              ${isDarkMode ? 'bg-gray-700 text-gray-200' : 'bg-gray-100 text-gray-800'}`}>
                              {game.analysis_status || game.status || 'Pending'}
                            </span>
                          )}
                        </td>
                        <td className="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                          <button
                            onClick={() => handleAnalyzeGame(game.id)}
                            className={`text-indigo-600 hover:text-indigo-900 ${isDarkMode ? 'text-indigo-400 hover:text-indigo-300' : ''}`}
                          >
                            {game.status === 'analyzed' ? 'Reanalyze' : 'Analyze'} Game
                            <span className="sr-only">, game {game.id}</span>
                          </button>
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

      <div className={`flex items-center justify-between border-t ${
        isDarkMode ? 'border-gray-700' : 'border-gray-200'
      } px-4 py-3 sm:px-6`}>
        <div className={`flex flex-1 justify-between sm:hidden`}>
          <button
            onClick={() => setCurrentPage(currentPage - 1)}
            disabled={currentPage === 1}
            className={`relative inline-flex items-center px-4 py-2 text-sm font-medium rounded-md ${
              isDarkMode
                ? 'bg-gray-800 text-gray-300 border-gray-700 hover:bg-gray-700'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            } ${
              currentPage === 1
                ? isDarkMode
                  ? 'cursor-not-allowed opacity-50'
                  : 'cursor-not-allowed opacity-50'
                : ''
            }`}
          >
            Previous
          </button>
          <button
            onClick={() => setCurrentPage(currentPage + 1)}
            disabled={currentPage === totalPages}
            className={`relative ml-3 inline-flex items-center px-4 py-2 text-sm font-medium rounded-md ${
              isDarkMode
                ? 'bg-gray-800 text-gray-300 border-gray-700 hover:bg-gray-700'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            } ${
              currentPage === totalPages
                ? isDarkMode
                  ? 'cursor-not-allowed opacity-50'
                  : 'cursor-not-allowed opacity-50'
                : ''
            }`}
          >
            Next
          </button>
        </div>
        <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
          <div>
            <p className={`text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Showing <span className="font-medium">{startIndex + 1}</span> to{' '}
              <span className="font-medium">{Math.min(endIndex, totalGames)}</span> of{' '}
              <span className="font-medium">{totalGames}</span> results
            </p>
          </div>
          <div>
            <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
              <button
                onClick={() => setCurrentPage(currentPage - 1)}
                disabled={currentPage === 1}
                className={`relative inline-flex items-center rounded-l-md px-2 py-2 ${
                  isDarkMode
                    ? 'bg-gray-800 text-gray-400 border-gray-700 hover:bg-gray-700'
                    : 'bg-white text-gray-500 border-gray-300 hover:bg-gray-50'
                } ${
                  currentPage === 1
                    ? isDarkMode
                      ? 'cursor-not-allowed opacity-50'
                      : 'cursor-not-allowed opacity-50'
                    : ''
                }`}
              >
                <span className="sr-only">Previous</span>
                <ChevronLeft className="h-5 w-5" aria-hidden="true" />
              </button>
              {/* Page numbers */}
              {pageNumbers.map((number) => (
                <button
                  key={number}
                  onClick={() => setCurrentPage(number)}
                  className={`relative inline-flex items-center px-4 py-2 text-sm font-semibold ${
                    number === currentPage
                      ? isDarkMode
                        ? 'bg-gray-700 text-white'
                        : 'bg-indigo-600 text-white'
                      : isDarkMode
                        ? 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                        : 'bg-white text-gray-900 hover:bg-gray-50'
                  } ${
                    isDarkMode
                      ? 'border-gray-700'
                      : 'border-gray-300'
                  }`}
                >
                  {number}
                </button>
              ))}
              <button
                onClick={() => setCurrentPage(currentPage + 1)}
                disabled={currentPage === totalPages}
                className={`relative inline-flex items-center rounded-r-md px-2 py-2 ${
                  isDarkMode
                    ? 'bg-gray-800 text-gray-400 border-gray-700 hover:bg-gray-700'
                    : 'bg-white text-gray-500 border-gray-300 hover:bg-gray-50'
                } ${
                  currentPage === totalPages
                    ? isDarkMode
                      ? 'cursor-not-allowed opacity-50'
                      : 'cursor-not-allowed opacity-50'
                    : ''
                }`}
              >
                <span className="sr-only">Next</span>
                <ChevronRight className="h-5 w-5" aria-hidden="true" />
              </button>
            </nav>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Games;
