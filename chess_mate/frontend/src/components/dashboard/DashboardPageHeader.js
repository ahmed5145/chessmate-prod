import React from 'react';
import { useTheme } from '../../context/ThemeContext';

const DashboardPageHeader = ({ eyebrow, subtitle }) => {
  const { isDarkMode } = useTheme();

  return (
    <header className="mb-6">
      <h1 className={`text-2xl sm:text-3xl font-bold tracking-tight ${
        isDarkMode ? 'text-white' : 'text-gray-900'
      }`}
      >
        {eyebrow}
      </h1>
      {subtitle ? (
        <p className={`mt-2 text-sm sm:text-base leading-relaxed max-w-2xl ${
          isDarkMode ? 'text-gray-400' : 'text-gray-600'
        }`}
        >
          {subtitle}
        </p>
      ) : null}
    </header>
  );
};

export default DashboardPageHeader;
