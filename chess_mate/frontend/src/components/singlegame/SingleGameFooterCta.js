import React from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '../../context/ThemeContext';
import { buildBatchPatternCta } from '../../utils/singleGameBatchCta';
import { trackSingleGameEvent } from '../../utils/marketingAnalytics';
import MarkReviewedButton from './MarkReviewedButton';

const SingleGameFooterCta = ({ batchContext = null, gameId = null, markReview = null }) => {
  const { isDarkMode } = useTheme();
  const cta = buildBatchPatternCta(batchContext);

  const handlePrimaryClick = () => {
    trackSingleGameEvent('single_game_batch_cta_click', {
      game_id: gameId,
      batch_id: batchContext?.batch_id || null,
      variant: cta.variant,
      destination: cta.primaryPath,
    });
  };

  return (
    <div
      className={`mt-8 rounded-lg border p-4 ${
        isDarkMode ? 'bg-gray-800/60 border-gray-700' : 'bg-indigo-50/80 border-indigo-100'
      }`}
    >
      <p className={`text-sm font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
        {cta.headline}
      </p>
      <p className={`mt-1 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
        {cta.subline}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <Link
          to={cta.primaryPath}
          onClick={handlePrimaryClick}
          className="inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
        >
          {cta.primaryLabel}
        </Link>
        {cta.variant === 'batch' ? (
          <Link
            to={cta.secondaryPath}
            className={`inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium border ${
              isDarkMode
                ? 'border-gray-600 text-gray-200 hover:bg-gray-700'
                : 'border-indigo-200 text-indigo-700 hover:bg-indigo-100'
            }`}
          >
            {cta.secondaryLabel}
          </Link>
        ) : null}
        <Link
          to="/games"
          className={`inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium ${
            isDarkMode ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          All games
        </Link>
        {markReview ? <MarkReviewedButton {...markReview} /> : null}
      </div>
    </div>
  );
};

export default SingleGameFooterCta;
