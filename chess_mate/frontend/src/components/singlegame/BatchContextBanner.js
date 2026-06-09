import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '../../context/ThemeContext';
import { markPriorityInboxReviewed } from '../../services/apiRequests';
import { trackMarketingEvent } from '../../utils/marketingAnalytics';

const BatchContextBanner = ({
  batchId,
  batchContext = null,
  move,
  priority,
  onPriorityReviewed,
}) => {
  const { isDarkMode } = useTheme();
  const [reviewState, setReviewState] = useState('idle');
  const [reviewError, setReviewError] = useState('');

  const resolvedBatchId = batchContext?.batch_id || batchId;
  if (!resolvedBatchId) {
    return null;
  }

  const priorityData = batchContext?.priority;
  const priorityTitle = priorityData?.title;
  const priorityRank = batchContext?.priority_rank || priority;
  const patternLabel = batchContext?.pattern_label;
  const openingName = batchContext?.opening_name;
  const openingEco = batchContext?.opening_eco;
  const gameResult = batchContext?.game_result;
  const linkedMove = batchContext?.linked_moment?.move_number || move;
  const showMarkReviewed = Boolean(priorityRank);

  const metaParts = [
    priorityRank ? `Priority #${priorityRank}` : null,
    priorityTitle || null,
    linkedMove ? `Move ${linkedMove}` : null,
    openingName ? `${openingName}${openingEco ? ` (${openingEco})` : ''}` : null,
    gameResult ? `Result ${gameResult}` : null,
  ].filter(Boolean);

  const handleMarkReviewed = async () => {
    if (!priorityRank || reviewState === 'loading' || reviewState === 'done') {
      return;
    }
    setReviewState('loading');
    setReviewError('');
    try {
      await markPriorityInboxReviewed({
        batchId: resolvedBatchId,
        priorityIndex: priorityRank,
      });
      trackMarketingEvent('priority_inbox_reviewed', {
        batch_id: resolvedBatchId,
        priority_index: priorityRank,
        surface: 'single_game',
      });
      setReviewState('done');
      if (typeof onPriorityReviewed === 'function') {
        onPriorityReviewed();
      }
    } catch (error) {
      setReviewState('idle');
      setReviewError(error?.detail || error?.message || 'Could not mark reviewed.');
    }
  };

  return (
    <div
      className={`mb-6 rounded-lg border px-4 py-3 ${
        isDarkMode
          ? 'bg-indigo-950/40 border-indigo-700/50 text-indigo-100'
          : 'bg-indigo-50 border-indigo-200 text-indigo-900'
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm font-medium">From your Batch Coach report</p>
        {patternLabel ? (
          <span
            className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
              isDarkMode ? 'bg-indigo-800 text-indigo-100' : 'bg-indigo-200 text-indigo-900'
            }`}
          >
            {patternLabel}
          </span>
        ) : null}
      </div>

      {metaParts.length > 0 ? (
        <p className={`mt-1 text-sm ${isDarkMode ? 'text-indigo-200/90' : 'text-indigo-800/90'}`}>
          {metaParts.join(' · ')}
        </p>
      ) : null}

      <p className={`mt-1 text-sm ${isDarkMode ? 'text-indigo-200/80' : 'text-indigo-800/80'}`}>
        Depth-20 drill-down on a moment your batch report cited — proof for your coaching plan.
      </p>

      {batchContext?.classification_disclaimer ? (
        <p className={`mt-2 text-xs ${isDarkMode ? 'text-amber-200/90' : 'text-amber-800'}`}>
          {batchContext.classification_disclaimer}
        </p>
      ) : null}

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <Link
          to={`/batch-report/${resolvedBatchId}`}
          className={`text-sm font-semibold underline ${
            isDarkMode ? 'text-indigo-300 hover:text-indigo-200' : 'text-indigo-700 hover:text-indigo-900'
          }`}
        >
          Back to batch report
        </Link>
        {showMarkReviewed ? (
          <button
            type="button"
            onClick={handleMarkReviewed}
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
        ) : null}
      </div>
      {reviewError ? (
        <p className={`mt-2 text-xs ${isDarkMode ? 'text-red-300' : 'text-red-700'}`}>{reviewError}</p>
      ) : null}
    </div>
  );
};

export default BatchContextBanner;
