import React from 'react';
import { useTheme } from '../../context/ThemeContext';

const InboxStreakChip = ({ streak }) => {
  const { isDarkMode } = useTheme();

  if (!streak?.show) {
    return null;
  }

  return (
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
  );
};

export default InboxStreakChip;
