import React from 'react';
import { useTheme } from '../../context/ThemeContext';
import {
  formatSingleGameStreakCopy,
  shouldShowSingleGameStreak,
} from '../../utils/singleGameStreak';

const SingleGameStreakCard = ({ streak = null }) => {
  const { isDarkMode } = useTheme();

  if (!shouldShowSingleGameStreak(streak)) {
    return null;
  }

  const copy = formatSingleGameStreakCopy(streak);

  return (
    <div
      className={`mb-6 rounded-lg border px-4 py-3 ${
        isDarkMode ? 'border-amber-700/60 bg-amber-900/20' : 'border-amber-200 bg-amber-50'
      }`}
    >
      <p className={`text-sm font-semibold ${isDarkMode ? 'text-amber-200' : 'text-amber-900'}`}>
        <span aria-hidden="true" className="mr-1">🔥</span>
        {copy}
      </p>
      <p className={`mt-1 text-xs ${isDarkMode ? 'text-amber-100/80' : 'text-amber-800/80'}`}>
        Your last consecutive depth-20 reviews had no 1+ pawn blunder or missed win on your moves.
      </p>
    </div>
  );
};

export default SingleGameStreakCard;
