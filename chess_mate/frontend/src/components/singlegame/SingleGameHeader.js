import React from 'react';
import GamePlatformBadge from '../GamePlatformBadge';
import { useTheme } from '../../context/ThemeContext';
import { formatListOpeningLabel } from '../../utils/formatListOpeningLabel';

const formatResultLabel = (result) => {
  const value = String(result || '').toLowerCase();
  if (value === 'win') return 'Win';
  if (value === 'loss') return 'Loss';
  if (value === 'draw') return 'Draw';
  return result || '—';
};

const resultBadgeClass = (result, isDarkMode) => {
  const value = String(result || '').toLowerCase();
  if (value === 'win') {
    return isDarkMode ? 'bg-green-900 text-green-200' : 'bg-green-100 text-green-800';
  }
  if (value === 'loss') {
    return isDarkMode ? 'bg-red-900 text-red-200' : 'bg-red-100 text-red-800';
  }
  if (value === 'draw') {
    return isDarkMode ? 'bg-yellow-900 text-yellow-200' : 'bg-yellow-100 text-yellow-800';
  }
  return isDarkMode ? 'bg-gray-700 text-gray-200' : 'bg-gray-100 text-gray-800';
};

const SingleGameHeader = ({ gameContext = {} }) => {
  const { isDarkMode } = useTheme();

  const opponent = gameContext.opponent || gameContext.opponent_name || 'Opponent';
  const openingLabel = formatListOpeningLabel({
    opening_name: gameContext.opening_name,
    eco_code: gameContext.eco,
  });
  const datePlayed = gameContext.date_played
    ? new Date(gameContext.date_played).toLocaleDateString()
    : null;
  const playerColor = gameContext.player_color
    ? `You played ${gameContext.player_color}`
    : null;

  return (
    <div
      className={`mb-6 rounded-lg border p-4 ${
        isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
      }`}
    >
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <h2 className={`text-xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
          vs {opponent}
        </h2>
        <span
          className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${resultBadgeClass(
            gameContext.result,
            isDarkMode
          )}`}
        >
          {formatResultLabel(gameContext.result)}
        </span>
        {gameContext.platform ? (
          <GamePlatformBadge platform={gameContext.platform} isDarkMode={isDarkMode} />
        ) : null}
      </div>
      <div className={`flex flex-wrap gap-x-4 gap-y-1 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
        {openingLabel ? <span>{openingLabel}</span> : null}
        {datePlayed ? <span>{datePlayed}</span> : null}
        {playerColor ? <span>{playerColor}</span> : null}
        <span className={isDarkMode ? 'text-gray-500' : 'text-gray-500'}>Depth-20 review</span>
      </div>
      {gameContext.platform_game_url ? (
        <a
          href={gameContext.platform_game_url}
          target="_blank"
          rel="noopener noreferrer"
          className={`mt-2 inline-block text-sm font-medium underline ${
            isDarkMode ? 'text-indigo-400' : 'text-indigo-600'
          }`}
        >
          Open original game
        </a>
      ) : null}
    </div>
  );
};

export default SingleGameHeader;
