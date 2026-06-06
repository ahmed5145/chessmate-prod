import React, { useState, useEffect, useContext, useRef, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import {
  createBatch,
  getBatchStatus,
  fetchBatchReportHistory,
  fetchUserGames
} from '../services/apiRequests';
import { useTheme } from '../context/ThemeContext';
import { UserContext } from '../contexts/UserContext';
import { useNavigate } from 'react-router-dom';
import {
  BarChart2,
  Clock,
  Coins
} from 'lucide-react';
import LoadingSpinner from './LoadingSpinner';
import { getTimeControlCategory } from '../utils/timeControlCategory';
import {
  estimateBatchDurationSeconds,
  formatBatchDurationRange,
} from '../utils/batchTimeEstimate';
import api from '../services/api';

const BATCH_SIZE_OPTIONS = [5, 10, 15, 20, 25, 30];
const clampBatchSize = (value, maxAvailable) => {
  const numeric = Number(value) || 10;
  return Math.min(Math.max(numeric, 5), Math.min(30, maxAvailable || 30));
};

const BatchAnalysis = () => {
  const [numGames, setNumGames] = useState(10);
  const [selectedGameIds, setSelectedGameIds] = useState([]);
  const [progressPercent, setProgressPercent] = useState(0);
  const [currentProgress, setCurrentProgress] = useState(0);
  const [totalGames, setTotalGames] = useState(0);
  const [estimatedTime, setEstimatedTime] = useState(0);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [startTime, setStartTime] = useState(null);
  const [batchId, setBatchId] = useState(null);
  const [availableGames, setAvailableGames] = useState([]);
  const [selectedTimeControl, setSelectedTimeControl] = useState('all');
  const [gameSelectionFilter, setGameSelectionFilter] = useState('unanalyzed');
  const [reportHistory, setReportHistory] = useState([]);
  const { isDarkMode } = useTheme();
  const userContext = useContext(UserContext);
  const credits = userContext?.credits ?? 0;
  const navigate = useNavigate();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [batchSendsEmail, setBatchSendsEmail] = useState(true);
  const [batchEtaOptions, setBatchEtaOptions] = useState({});
  const pollingErrorCountRef = useRef(0);

  useEffect(() => {
    let cancelled = false;
    api.get('/api/v1/public/site-config/')
      .then((response) => {
        if (!cancelled && response?.data) {
          const data = response.data;
          setBatchSendsEmail(data.batch_sends_completion_email !== false);
          setBatchEtaOptions({
            minutesPerGameLow: data.batch_eta_minutes_per_game_low,
            minutesPerGameHigh: data.batch_eta_minutes_per_game_high,
            coachingBufferMinutes: data.batch_eta_coaching_buffer_minutes,
          });
        }
      })
      .catch(() => {
        /* keep defaults */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const navigateReliably = useCallback((targetPath, options = {}) => {
    navigate(targetPath, options);

    // Router occasionally updates URL before rendering target route; force fallback.
    window.setTimeout(() => {
      if (window.location.pathname !== targetPath) {
        window.location.assign(targetPath);
      }
    }, 250);
  }, [navigate]);

  // Fetch available games when component mounts
  useEffect(() => {
    const fetchAvailableGames = async () => {
      try {
        const gamesResponse = await fetchUserGames();
        const games = Array.isArray(gamesResponse)
          ? gamesResponse
          : (Array.isArray(gamesResponse?.results) ? gamesResponse.results : []);
        setAvailableGames(games);
      } catch (error) {
        console.error('Error fetching games:', error);
        toast.error('Failed to fetch available games');
      }
    };
    fetchAvailableGames();
  }, []);

  useEffect(() => {
    const loadReportHistory = async () => {
      try {
        const reports = await fetchBatchReportHistory(12);
        setReportHistory(Array.isArray(reports) ? reports : []);
      } catch (error) {
        console.error('Error fetching batch report history:', error);
      }
    };

    loadReportHistory();
  }, []);

  useEffect(() => {
    let intervalId;
    let toastId;

    const checkProgress = async () => {
      if (!batchId) return;

      try {
        const response = await getBatchStatus(batchId);
        console.log('Status response:', response);
        pollingErrorCountRef.current = 0;

        const status = String(response?.status || '').toUpperCase();
        const completed = Number(response?.completed_games || 0);
        const total = Number(response?.games_count || totalGames || 0);
        const progressValue = total > 0 ? Math.round((completed / total) * 100) : 0;
        const errors = Array.isArray(response?.errors) ? response.errors : [];

        switch (status) {
          case 'SUCCESS':
          case 'COMPLETED':
          case 'PARTIAL':
            setIsAnalyzing(false);
            clearInterval(intervalId);
            setProgressPercent(100);
            setCurrentProgress(total);
            setTotalGames(total);
            if (toastId) toast.dismiss(toastId);
            toast.success('Analysis completed!');
            navigateReliably(`/batch-report/${batchId}`, { replace: true });
            return true;

          case 'FAILED':
          case 'FAILURE':
            setIsAnalyzing(false);
            clearInterval(intervalId);
            setProgressPercent(progressValue);
            setCurrentProgress(completed);
            setTotalGames(total);
            if (toastId) toast.dismiss(toastId);
            toast.error(errors[0]?.message || 'Batch analysis failed');
            navigateReliably(`/batch-report/${batchId}`, { replace: true });
            return true;

          case 'PROGRESS':
          case 'STARTED':
          case 'PENDING':
          case 'IN_PROGRESS':
            if (total > 0) {
              setCurrentProgress(completed);
              setTotalGames(total);
              setProgressPercent(isNaN(progressValue) ? 0 : progressValue);

              const progressMessage = response?.progress || response?.message || `Analyzing game ${completed} of ${total}`;
              if (toastId) {
                toast.loading(progressMessage, { id: toastId });
              } else {
                toastId = toast.loading(progressMessage);
              }
            }
            return false;

          default:
            console.warn('Unknown state:', status);
            if (total > 0) {
              setCurrentProgress(completed);
              setTotalGames(total);
              setProgressPercent(isNaN(progressValue) ? 0 : progressValue);
            }
            return false;
        }
      } catch (error) {
        console.error('Error checking progress:', error);
        pollingErrorCountRef.current += 1;
        if (pollingErrorCountRef.current >= 3) {
          setIsAnalyzing(false);
          if (toastId) toast.dismiss(toastId);
          toast.error('Error checking analysis progress');
          clearInterval(intervalId);
          return true;
        }

        if (pollingErrorCountRef.current === 1) {
          toast('Temporary issue checking progress. Retrying...');
        }

        return false;
      }
    };

    if (isAnalyzing && batchId) {
      // Initial check
      checkProgress();
      // Then start polling
      intervalId = setInterval(checkProgress, 2000);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
      if (toastId) {
        toast.dismiss(toastId);
      }
    };
  }, [isAnalyzing, batchId, navigate, navigateReliably, totalGames]);

  useEffect(() => {
    let timer;
    if (startTime && isAnalyzing) {
      timer = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        setElapsedTime(elapsed);

        // Update estimated time based on current progress
        if (currentProgress > 0) {
          const timePerGame = elapsed / currentProgress;
          const remainingGames = totalGames - currentProgress;
          const newEstimate = Math.ceil(timePerGame * remainingGames);
          setEstimatedTime(newEstimate);
        }
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [startTime, isAnalyzing, currentProgress, totalGames]);

  const startBatchAnalysis = async () => {
    const hasManualSelection = selectedGameIds.length > 0;
    const gamesToAnalyze = hasManualSelection
      ? selectedGameIds
      : sortedFilteredGames.slice(0, numGames).map((game) => game.id);

    if (!gamesToAnalyze.length) {
      toast.error('Please select at least 5 games to analyze');
      return;
    }

    if (gamesToAnalyze.length < 5) {
      toast.error('Batch analysis requires at least 5 games');
      return;
    }

    if (gamesToAnalyze.length > 30) {
      toast.error('Maximum number of games for batch analysis is 30');
      return;
    }

    try {
      setIsAnalyzing(true);
      setProgressPercent(0);
      setCurrentProgress(0);
      setStartTime(Date.now());

      const response = await createBatch({ gameIds: gamesToAnalyze });

      if (response?.batch_id) {
        setBatchId(response.batch_id);
        const totalRequested = gamesToAnalyze.length;
        setTotalGames(response.games_count || totalRequested);
        setEstimatedTime(estimateBatchDurationSeconds(totalRequested, batchEtaOptions));
        const etaLabel = formatBatchDurationRange(totalRequested, batchEtaOptions);
        toast.success(
          batchSendsEmail
            ? `Analysis started (${etaLabel}). You can close this page — we'll email you when it's ready.`
            : `Analysis started (${etaLabel}). You can leave this page and check Saved Batch Reports later.`,
          { duration: 6000 }
        );
      } else {
        throw new Error('No batch ID received');
      }
    } catch (error) {
      console.error('Error starting batch analysis:', error);
      toast.error(error.message || 'Failed to start analysis');
      setIsAnalyzing(false);
      setStartTime(null);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const normalizedAvailableGames = Array.isArray(availableGames) ? availableGames : [];

  const filteredGames = normalizedAvailableGames.filter(game => {
    const gameTimeControl = getTimeControlCategory(game);

    if (selectedTimeControl !== 'all' && gameTimeControl !== selectedTimeControl) {
      return false;
    }

    // Filter by analysis status if needed
    const analysisStatus = String(game.analysis_status || game.status || '').toLowerCase();
    const analyzedStatuses = new Set([
      'analyzed',
      'completed',
      'success',
      'failed',
      'analyzing',
      'in_progress',
      'processing'
    ]);
    const isAnalyzed = Boolean(game.analysis) || analyzedStatuses.has(analysisStatus);
    if (gameSelectionFilter === 'unanalyzed' && isAnalyzed) {
      return false;
    }

    return true;
  });

  const sortedFilteredGames = [...filteredGames].sort((a, b) => {
    const aDate = new Date(a?.date_played || 0).getTime();
    const bDate = new Date(b?.date_played || 0).getTime();
    return bDate - aDate;
  });

  const requiredCredits =
    selectedGameIds.length > 0
      ? selectedGameIds.length
      : Math.min(Math.max(Number(numGames) || 10, 0), sortedFilteredGames.length);

  const gamesForEstimate =
    selectedGameIds.length > 0
      ? selectedGameIds.length
      : clampBatchSize(numGames, sortedFilteredGames.length);

  const batchEtaLabel = gamesForEstimate >= 5
    ? formatBatchDurationRange(gamesForEstimate, batchEtaOptions)
    : null;

  const toggleSelectedGame = (gameId) => {
    setSelectedGameIds((prev) => {
      if (prev.includes(gameId)) {
        return prev.filter((id) => id !== gameId);
      }
      if (prev.length >= 30) {
        toast.error('Maximum number of games for batch analysis is 30');
        return prev;
      }
      return [...prev, gameId];
    });
  };

  const selectRecentGames = (count) => {
    const batchSize = clampBatchSize(count, sortedFilteredGames.length);
    const ids = sortedFilteredGames.slice(0, batchSize).map((game) => game.id);
    setSelectedGameIds(ids);
    setNumGames(batchSize);
  };

  const clearManualSelection = () => {
    setSelectedGameIds([]);
  };

  // Keep batch size in 5–30 when filters change; never drop to 1.
  useEffect(() => {
    const available = sortedFilteredGames.length;
    if (available < 5) {
      return;
    }
    const clamped = clampBatchSize(numGames, available);
    if (clamped !== numGames) {
      setNumGames(clamped);
    }
  }, [sortedFilteredGames.length, numGames]);

  useEffect(() => {
    const availableIds = new Set(filteredGames.map((game) => game.id));
    setSelectedGameIds((prev) => prev.filter((id) => availableIds.has(id)));
  }, [filteredGames]);

  return (
    <div className={`min-h-screen ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header Section */}
        <div className="mb-8">
          <h1 className={`text-3xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Batch Analysis
          </h1>
          <p className={`mt-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            Batch coach analysis finds patterns across your recent games (default 10, min 5, max 30).
          </p>
        </div>

        <div className={`mb-6 p-4 rounded-lg border ${
          isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-indigo-50 border-indigo-100'
        }`}>
          <h2 className={`text-sm font-semibold mb-2 ${isDarkMode ? 'text-white' : 'text-indigo-900'}`}>
            What to expect
          </h2>
          <ul className={`text-sm space-y-1 list-disc pl-5 ${isDarkMode ? 'text-gray-300' : 'text-indigo-900'}`}>
            <li>Batch coach analysis is included for games already on your account (credits are used when you import games).</li>
            <li>Engine depth is fixed internally (depth 14) for consistent metrics — not configurable.</li>
            <li>Typical runtime: about 3–5 minutes per game, analyzed one at a time; larger batches can take 30+ minutes.</li>
            <li>
              {batchSendsEmail
                ? 'After you start, you can close this tab — we\'ll email you when your report is ready.'
                : 'After you start, you can leave this page and open the report from Saved Batch Reports.'}
            </li>
            <li>At least 5 games must analyze successfully or the batch fails.</li>
          </ul>
        </div>

        <div className={`mb-8 p-4 rounded-lg ${
          isDarkMode ? 'bg-gray-800' : 'bg-white'
        } shadow-sm`}>
          <div className="flex items-center space-x-2">
            <Coins className="h-5 w-5 text-indigo-500" />
            <span className={`font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Available credits: {credits}
            </span>
            <span className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              (used when importing games from Lichess/Chess.com)
            </span>
          </div>
        </div>

        {/* Analysis Options */}
        <div className={`mb-8 p-6 rounded-lg ${
          isDarkMode ? 'bg-gray-800' : 'bg-white'
        } shadow-sm`}>
          <h2 className={`text-lg font-medium mb-4 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Analysis Options
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Batch size: 5–30 when auto-selecting recent games */}
            <div>
              <label htmlFor="numGames" className={`block text-sm font-medium ${
                isDarkMode ? 'text-gray-200' : 'text-gray-700'
              }`}>
                Games per batch
              </label>
              <select
                id="numGames"
                name="numGames"
                disabled={sortedFilteredGames.length < 5 || selectedGameIds.length > 0}
                className={`mt-1 block w-full rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${
                  isDarkMode
                    ? 'bg-gray-700 border-gray-600 text-white'
                    : 'border-gray-300 text-gray-900'
                }`}
                value={clampBatchSize(numGames, sortedFilteredGames.length)}
                onChange={(e) => setNumGames(clampBatchSize(Number(e.target.value), sortedFilteredGames.length))}
              >
                {BATCH_SIZE_OPTIONS.filter((size) => size <= sortedFilteredGames.length || size === 5).map((size) => (
                  <option key={size} value={size} disabled={sortedFilteredGames.length < size}>
                    {size} games{size === 10 ? ' (recommended)' : size === 5 ? ' (minimum)' : ''}
                  </option>
                ))}
              </select>
              <p className={`mt-1 text-xs ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                {selectedGameIds.length > 0
                  ? `Using ${selectedGameIds.length} checked games below (5–30). Clear selection to auto-pick recent.`
                  : 'Uses your most recent matching games, or check specific games below (5–30).'}
              </p>
            </div>

            {/* Time Control Filter */}
            <div>
              <label htmlFor="timeControl" className={`block text-sm font-medium ${
                isDarkMode ? 'text-gray-200' : 'text-gray-700'
              }`}>
                Time Control
              </label>
              <select
                id="timeControl"
                className={`mt-1 block w-full rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${
                  isDarkMode
                    ? 'bg-gray-700 border-gray-600 text-white'
                    : 'border-gray-300 text-gray-900'
                }`}
                value={selectedTimeControl}
                onChange={(e) => setSelectedTimeControl(e.target.value)}
              >
                <option value="all">All Time Controls</option>
                <option value="bullet">Bullet</option>
                <option value="blitz">Blitz</option>
                <option value="rapid">Rapid</option>
                <option value="classical">Classical</option>
              </select>
            </div>
          </div>

          {/* Game selection filter */}
          <div className="mt-4">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div>
                <label htmlFor="gameSelectionFilter" className={`block text-sm font-medium ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>
                  Game Selection Filter
                </label>
                <p className={`text-xs mt-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                  Hide analyzed games by default so the table focuses on unrated material.
                </p>
              </div>
              <select
                id="gameSelectionFilter"
                className={`mt-1 block w-full md:w-72 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${
                  isDarkMode
                    ? 'bg-gray-700 border-gray-600 text-white'
                    : 'border-gray-300 text-gray-900'
                }`}
                value={gameSelectionFilter}
                onChange={(e) => setGameSelectionFilter(e.target.value)}
              >
                <option value="unanalyzed">Unanalyzed games only</option>
                <option value="all">All games</option>
              </select>
            </div>
          </div>

          {/* Selection Shortcuts */}
          <div className="mt-6">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`text-sm font-medium ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>
                Quick select recent:
              </span>
              {[5, 10, 15, 20].map((count) => (
                <button
                  key={count}
                  type="button"
                  disabled={sortedFilteredGames.length < count}
                  onClick={() => selectRecentGames(count)}
                  className={`px-3 py-1.5 text-sm rounded-md border disabled:opacity-40 ${
                    isDarkMode
                      ? 'border-gray-600 text-gray-200 hover:bg-gray-700'
                      : 'border-gray-300 text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  Select {count} recent
                </button>
              ))}
              <button
                type="button"
                onClick={clearManualSelection}
                className={`px-3 py-1.5 text-sm rounded-md border ${
                  isDarkMode
                    ? 'border-gray-600 text-gray-200 hover:bg-gray-700'
                    : 'border-gray-300 text-gray-700 hover:bg-gray-100'
                }`}
              >
                Clear Selection
              </button>
            </div>
          </div>

          {/* Manual Selection List */}
          <div className="mt-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className={`text-sm font-medium ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>
                Select imported games ({selectedGameIds.length} selected)
              </h3>
              <span className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                If none selected, we use Number of Games + the filter above
              </span>
            </div>
            <div className={`max-h-64 overflow-y-auto rounded-md border ${isDarkMode ? 'border-gray-700' : 'border-gray-200'}`}>
              {sortedFilteredGames.length === 0 ? (
                <div className={`p-3 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                  No games available for the current filters.
                </div>
              ) : (
                sortedFilteredGames.map((game) => {
                  const checked = selectedGameIds.includes(game.id);
                  return (
                    <label
                      key={game.id}
                      className={`flex items-center gap-3 px-3 py-2 cursor-pointer border-b last:border-b-0 ${
                        isDarkMode ? 'border-gray-700 hover:bg-gray-700/50' : 'border-gray-100 hover:bg-gray-50'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleSelectedGame(game.id)}
                        className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                      />
                      <div className="min-w-0">
                        <div className={`text-sm font-medium truncate ${isDarkMode ? 'text-gray-100' : 'text-gray-900'}`}>
                          {game.white || 'White'} vs {game.black || 'Black'}
                        </div>
                        <div className={`text-xs truncate ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                          {game.opening_name || 'Unknown Opening'}
                          {getTimeControlCategory(game) ? ` • ${getTimeControlCategory(game)}` : ''}
                          {' • '}
                          {new Date(game.date_played).toLocaleDateString()}
                        </div>
                      </div>
                    </label>
                  );
                })
              )}
            </div>
          </div>

          {/* Saved Reports */}
          <div className="mt-8">
            <h3 className={`text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>
              Saved Batch Reports
            </h3>
            <div className={`rounded-md border ${isDarkMode ? 'border-gray-700' : 'border-gray-200'}`}>
              {reportHistory.length === 0 ? (
                <div className={`p-3 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                  No saved reports yet. Run a batch analysis to create your first report.
                </div>
              ) : (
                reportHistory.map((report) => {
                  const statusLabel = report.status || 'completed';
                  const statusColors = {
                    completed: isDarkMode ? 'bg-green-900/40 text-green-300' : 'bg-green-100 text-green-800',
                    partial: isDarkMode ? 'bg-amber-900/40 text-amber-300' : 'bg-amber-100 text-amber-800',
                    failed: isDarkMode ? 'bg-red-900/40 text-red-300' : 'bg-red-100 text-red-800',
                    in_progress: isDarkMode ? 'bg-blue-900/40 text-blue-300' : 'bg-blue-100 text-blue-800',
                    pending: isDarkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-700',
                  };
                  const statusClass = statusColors[statusLabel] || statusColors.completed;

                  return (
                  <div
                    key={report.id}
                    className={`px-3 py-3 border-b last:border-b-0 ${
                      isDarkMode ? 'border-gray-700' : 'border-gray-100'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <div className={`text-sm font-medium truncate ${isDarkMode ? 'text-gray-100' : 'text-gray-900'}`}>
                            Batch #{report.id} · {report.games_count || 0} games
                          </div>
                          <span className={`text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded ${statusClass}`}>
                            {statusLabel.replace('_', ' ')}
                          </span>
                          {report.overall_accuracy_pct != null && (
                            <span className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                              {Number(report.overall_accuracy_pct).toFixed(1)}% accuracy
                            </span>
                          )}
                        </div>
                        <div className={`text-xs truncate ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                          {report.coach_summary || 'Open report for coaching insights'}
                        </div>
                        <div className={`text-xs ${isDarkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                          {new Date(report.created_at).toLocaleString()}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => navigateReliably(`/batch-report/${report.id}`)}
                        className={`px-3 py-1.5 text-sm rounded-md border ${
                          isDarkMode
                            ? 'border-gray-600 text-gray-200 hover:bg-gray-700'
                            : 'border-gray-300 text-gray-700 hover:bg-gray-100'
                        }`}
                      >
                        Open Report
                      </button>
                    </div>
                  </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {!isAnalyzing && batchEtaLabel && requiredCredits >= 5 ? (
          <div
            className={`mb-4 rounded-lg border px-4 py-3 text-sm ${
              isDarkMode
                ? 'border-indigo-800 bg-indigo-950/40 text-indigo-100'
                : 'border-indigo-200 bg-indigo-50 text-indigo-900'
            }`}
          >
            <p className="font-medium">Estimated time</p>
            <p className={`mt-1 ${isDarkMode ? 'text-indigo-200/90' : 'text-indigo-800'}`}>
              A batch of <strong>{gamesForEstimate}</strong> games typically takes{' '}
              <strong>{batchEtaLabel}</strong> (Stockfish depth 14, analyzed one game at a time).
            </p>
            <p className={`mt-2 ${isDarkMode ? 'text-indigo-200/80' : 'text-indigo-700'}`}>
              {batchSendsEmail ? (
                <>
                  After you start, you can <strong>close this tab</strong>. We&apos;ll email you when your
                  coach report is ready, and it will appear under <strong>Saved Batch Reports</strong>.
                </>
              ) : (
                <>
                  You can leave this page after starting and open your report later from{' '}
                  <strong>Saved Batch Reports</strong>.
                </>
              )}
            </p>
          </div>
        ) : null}

        {/* Progress Section */}
        {isAnalyzing ? (
          <div className={`p-6 rounded-lg ${
            isDarkMode ? 'bg-gray-800' : 'bg-white'
          } shadow-sm`}>
            <div className="space-y-4">
              {/* Progress Bar */}
              <div className="relative pt-1">
                <div className="flex mb-2 items-center justify-between">
                  <div>
                    <span className={`text-xs font-semibold inline-block py-1 px-2 uppercase rounded-full ${
                      isDarkMode ? 'bg-gray-700 text-gray-200' : 'bg-gray-200 text-gray-800'
                    }`}>
                      Progress
                    </span>
                  </div>
                  <div className={`text-right ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                    <span className="text-xs font-semibold">
                      {progressPercent}%
                    </span>
                  </div>
                </div>
                <div className={`overflow-hidden h-2 mb-4 text-xs flex rounded ${
                  isDarkMode ? 'bg-gray-700' : 'bg-gray-200'
                }`}>
                  <div
                    style={{ width: `${progressPercent}%` }}
                    className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-indigo-500"
                  />
                </div>
              </div>

              {/* Status Information */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className={`p-4 rounded-lg ${
                  isDarkMode ? 'bg-gray-700' : 'bg-gray-100'
                }`}>
                  <div className="flex items-center space-x-2">
                    <BarChart2 className="h-5 w-5 text-indigo-500" />
                    <span className={`font-medium ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>
                      {currentProgress} of {totalGames} games
                    </span>
                  </div>
                </div>

                <div className={`p-4 rounded-lg ${
                  isDarkMode ? 'bg-gray-700' : 'bg-gray-100'
                }`}>
                  <div className="flex items-center space-x-2">
                    <Clock className="h-5 w-5 text-indigo-500" />
                    <span className={`font-medium ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>
                      Time Elapsed: {formatTime(elapsedTime)}
                    </span>
                  </div>
                </div>

                <div className={`p-4 rounded-lg ${
                  isDarkMode ? 'bg-gray-700' : 'bg-gray-100'
                }`}>
                  <div className="flex items-center space-x-2">
                    <Clock className="h-5 w-5 text-indigo-500" />
                    <span className={`font-medium ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>
                      Estimated: {formatTime(estimatedTime)}
                    </span>
                  </div>
                </div>
              </div>

              <div
                className={`rounded-lg border px-4 py-3 text-sm ${
                  isDarkMode
                    ? 'border-blue-800/60 bg-blue-950/30 text-blue-100'
                    : 'border-blue-200 bg-blue-50 text-blue-900'
                }`}
              >
                {batchSendsEmail ? (
                  <>
                    <strong>Safe to close this tab.</strong> We&apos;ll email you when the report is ready.
                    Progress may sit on one game for several minutes while Stockfish finishes that game.
                  </>
                ) : (
                  <>
                    <strong>You can leave this page.</strong> Check <strong>Saved Batch Reports</strong> for
                    status. Each game may take several minutes to analyze.
                  </>
                )}
              </div>
            </div>
          </div>
        ) : (
          <button
            onClick={startBatchAnalysis}
            disabled={isAnalyzing || requiredCredits < 5}
            className={`w-full py-3 px-4 rounded-lg font-medium transition-colors ${
              isAnalyzing ? 'bg-gray-400 cursor-not-allowed' : isDarkMode ? 'bg-indigo-600 hover:bg-indigo-700 text-white' : 'bg-indigo-600 hover:bg-indigo-700 text-white'
            }`}
          >
            {isAnalyzing ? (
              <div className="flex items-center justify-center space-x-2">
                <LoadingSpinner size="small" />
                <span>Analyzing...</span>
              </div>
            ) : (
              'Start Batch Analysis'
            )}
          </button>
        )}
      </div>
    </div>
  );
};

export default BatchAnalysis;
