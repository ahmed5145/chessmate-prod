import React, { useState } from 'react';
import { useTheme } from '../../context/ThemeContext';
import { freezeInboxStreak } from '../../services/apiRequests';

const InboxStreakChip = ({ streak, onFreezeApplied }) => {
  const { isDarkMode } = useTheme();
  const [freezing, setFreezing] = useState(false);
  const [error, setError] = useState(null);

  if (!streak?.show) {
    return null;
  }

  const freeze = streak.freeze || {};
  const canFreeze = Boolean(freeze.can_use);

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
      <span
        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
          isDarkMode
            ? 'bg-orange-900/40 text-orange-200 border border-orange-700/50'
            : 'bg-orange-100 text-orange-800 border border-orange-200'
        }`}
        title={streak.milestone_message || streak.label}
      >
        <span aria-hidden="true">🔥</span>
        {streak.label}
      </span>
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
