import React from 'react';
import { useTheme } from '../../context/ThemeContext';

const DashboardPageHeader = ({ eyebrow, subtitle }) => {
  const { isDarkMode } = useTheme();

  return (
    <header className="mb-6">
      <p className={`text-xs font-semibold uppercase tracking-wider ${
        isDarkMode ? 'text-indigo-300' : 'text-indigo-600'
      }`}
      >
        {eyebrow}
      </p>
      {subtitle ? (
        <p className={`mt-1 text-sm sm:text-base max-w-2xl ${
          isDarkMode ? 'text-gray-300' : 'text-gray-600'
        }`}
        >
          {subtitle}
        </p>
      ) : null}
    </header>
  );
};

export default DashboardPageHeader;
