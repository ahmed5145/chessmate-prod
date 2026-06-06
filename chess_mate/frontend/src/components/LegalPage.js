import React from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';

const LegalPage = ({ title, children }) => {
  const { isDarkMode } = useTheme();

  return (
    <div className={`min-h-screen ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <Link
          to="/"
          className={`text-sm mb-6 inline-block ${isDarkMode ? 'text-indigo-300 hover:text-indigo-200' : 'text-indigo-600 hover:text-indigo-800'}`}
        >
          ← Back to home
        </Link>
        <h1 className={`text-3xl font-bold mb-8 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>{title}</h1>
        <div className={`prose prose-sm max-w-none space-y-4 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          {children}
        </div>
      </div>
    </div>
  );
};

export default LegalPage;
