import React from 'react';
import { useTheme } from '../../context/ThemeContext';

const MarkReviewedButton = ({
  showMarkReviewed,
  reviewState,
  reviewError,
  onMarkReviewed,
}) => {
  const { isDarkMode } = useTheme();

  if (!showMarkReviewed) {
    return null;
  }

  return (
    <>
      <button
        type="button"
        onClick={onMarkReviewed}
        disabled={reviewState === 'loading' || reviewState === 'done'}
        className={`text-sm font-semibold px-3 py-1 rounded-md transition ${
          reviewState === 'done'
            ? (isDarkMode ? 'bg-green-900/40 text-green-200' : 'bg-green-100 text-green-800')
            : (isDarkMode
              ? 'bg-indigo-800 text-indigo-100 hover:bg-indigo-700 disabled:opacity-60'
              : 'bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-60')
        }`}
      >
        {reviewState === 'done' ? 'Marked reviewed' : reviewState === 'loading' ? 'Saving…' : 'Mark reviewed'}
      </button>
      {reviewError ? (
        <p className={`w-full text-xs ${isDarkMode ? 'text-red-300' : 'text-red-700'}`}>{reviewError}</p>
      ) : null}
    </>
  );
};

export default MarkReviewedButton;
