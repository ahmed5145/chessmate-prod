import React, { useState } from 'react';
import { useTheme } from '../../context/ThemeContext';
import { freezeInboxStreak } from '../../services/apiRequests';

const InboxStreakChip = ({ streak, onFreezeApplied }) => {
  const { isDarkMode } = useTheme();
  const [freezing, setFreezing] = useState(false);
  const [error, setError] = useState(null);

  const freeze = streak.freeze || {};
  const canFreeze = Boolean(freeze.can_use);
  const showBadge = Boolean(streak?.show_badge ?? (streak?.show && (streak?.count || 0) >= 2));
  const showProgress = Boolean(streak?.show && !showBadge && streak?.label);

  if (!showBadge && !showProgress && !streak?.hint) {
    return null;
  }

  const handleFreeze = async () => {
    if (!canFreeze || freezing) {
      return;
    }
    setFreezing(true);
    setError(null);
    try {
      const result = await freezeInboxStreak();
      onFreezeApplied?.(result);
    } catch (freezeError) {
      setError(
        freezeError?.detail
        || freezeError?.message
        || 'Could not apply streak freeze.'
      );
    } finally {
      setFreezing(false);
    }
  };

  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      {showBadge || showProgress ? (
        <span
          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
            showBadge
              ? (isDarkMode
                ? 'bg-orange-900/40 text-orange-200 border border-orange-700/50'
                : 'bg-orange-100 text-orange-800 border border-orange-200')
              : (isDarkMode
                ? 'bg-gray-800 text-gray-300 border border-gray-600'
                : 'bg-gray-100 text-gray-700 border border-gray-300')
          }`}
          title={streak.milestone_message || streak.label || streak.hint}
        >
          {showBadge ? <span aria-hidden="true">🔥</span> : null}
          {streak.label}
        </span>
      ) : null}
      {!showBadge && !showProgress && streak.hint ? (
        <span className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          {streak.hint}
        </span>
      ) : null}
      {canFreeze ? (
        <button
          type="button"
          onClick={handleFreeze}
          disabled={freezing}
          className={`text-xs font-semibold underline ${
            isDarkMode ? 'text-orange-200 hover:text-orange-100' : 'text-orange-700 hover:text-orange-900'
          }`}
        >
          {freezing ? 'Freezing…' : (freeze.label || 'Use freeze (1 left this month)')}
        </button>
      ) : null}
      {error ? (
        <span className={`text-xs ${isDarkMode ? 'text-red-300' : 'text-red-700'}`}>{error}</span>
      ) : null}
    </span>
  );
};

export default InboxStreakChip;
