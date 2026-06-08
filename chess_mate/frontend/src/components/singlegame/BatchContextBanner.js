import React from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '../../context/ThemeContext';

const BatchContextBanner = ({ batchId, move, priority }) => {
  const { isDarkMode } = useTheme();

  if (!batchId) {
    return null;
  }

  const metaParts = [
    priority ? `Priority #${priority}` : null,
    move ? `Move ${move}` : null,
  ].filter(Boolean);

  return (
    <div
      className={`mb-6 rounded-lg border px-4 py-3 ${
        isDarkMode
          ? 'bg-indigo-950/40 border-indigo-700/50 text-indigo-100'
          : 'bg-indigo-50 border-indigo-200 text-indigo-900'
      }`}
    >
      <p className="text-sm font-medium">
        From your Batch Coach report
        {metaParts.length > 0 ? ` · ${metaParts.join(' · ')}` : ''}
      </p>
      <p className={`mt-1 text-sm ${isDarkMode ? 'text-indigo-200/80' : 'text-indigo-800/80'}`}>
        This is a depth-20 drill-down on a moment your batch report cited — proof for your coaching plan.
      </p>
      <Link
        to={`/batch-report/${batchId}`}
        className={`mt-2 inline-block text-sm font-semibold underline ${
          isDarkMode ? 'text-indigo-300 hover:text-indigo-200' : 'text-indigo-700 hover:text-indigo-900'
        }`}
      >
        Back to batch report
      </Link>
    </div>
  );
};

export default BatchContextBanner;
