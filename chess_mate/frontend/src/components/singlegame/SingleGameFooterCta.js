import React from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '../../context/ThemeContext';

const SingleGameFooterCta = ({ batchId = null }) => {
  const { isDarkMode } = useTheme();

  return (
    <div
      className={`mt-8 rounded-lg border p-4 ${
        isDarkMode ? 'bg-gray-800/60 border-gray-700' : 'bg-indigo-50/80 border-indigo-100'
      }`}
    >
      <p className={`text-sm font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
        {batchId
          ? 'Patterns across many games live in your batch report.'
          : 'Want patterns across many games?'}
      </p>
      <p className={`mt-1 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
        Batch Coach is included after import — no need to analyze each game first.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {batchId ? (
          <Link
            to={`/batch-report/${batchId}`}
            className="inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
          >
            View batch report
          </Link>
        ) : null}
        <Link
          to="/batch-analysis"
          className={`inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium border ${
            isDarkMode
              ? 'border-gray-600 text-gray-200 hover:bg-gray-700'
              : 'border-indigo-200 text-indigo-700 hover:bg-indigo-100'
          }`}
        >
          {batchId ? 'Run new batch' : 'Start Batch Coach'}
        </Link>
        <Link
          to="/games"
          className={`inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium ${
            isDarkMode ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          All games
        </Link>
      </div>
    </div>
  );
};

export default SingleGameFooterCta;
