import React from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '../../context/ThemeContext';
import MarkReviewedButton from './MarkReviewedButton';
import { useMarkPriorityReviewed } from './useMarkPriorityReviewed';

const BatchContextBanner = ({
  batchId,
  batchContext = null,
  move,
  priority,
  markReview: markReviewProp = null,
  onPriorityReviewed,
}) => {
  const { isDarkMode } = useTheme();

  const resolvedBatchId = batchContext?.batch_id || batchId;
  const priorityRank = batchContext?.priority_rank || priority;

  const internalMark = useMarkPriorityReviewed(
    markReviewProp ? null : resolvedBatchId,
    markReviewProp ? null : priorityRank,
    onPriorityReviewed,
  );
  const markReview = markReviewProp || internalMark;

  if (!resolvedBatchId) {
    return null;
  }

  const priorityData = batchContext?.priority;
  const priorityTitle = priorityData?.title;
  const patternLabel = batchContext?.pattern_label;
  const openingName = batchContext?.opening_name;
  const openingEco = batchContext?.opening_eco;
  const gameResult = batchContext?.game_result;
  const linkedMove = batchContext?.linked_moment?.move_number || move;
  const alignment = batchContext?.coach_alignment;

  const alignmentStyles = {
    high: isDarkMode
      ? 'bg-green-900/40 text-green-200 border-green-700/60'
      : 'bg-green-100 text-green-800 border-green-200',
    medium: isDarkMode
      ? 'bg-amber-900/40 text-amber-200 border-amber-700/60'
      : 'bg-amber-100 text-amber-800 border-amber-200',
    low: isDarkMode
      ? 'bg-gray-800 text-gray-200 border-gray-600'
      : 'bg-gray-100 text-gray-700 border-gray-300',
  };

  const metaParts = [
    priorityRank ? `Priority #${priorityRank}` : null,
    priorityTitle || null,
    linkedMove ? `Move ${linkedMove}` : null,
    openingName ? `${openingName}${openingEco ? ` (${openingEco})` : ''}` : null,
    gameResult ? `Result ${gameResult}` : null,
  ].filter(Boolean);

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

      {alignment ? (
        <div
          className={`mt-2 inline-flex max-w-full items-start gap-2 rounded-md border px-3 py-2 text-xs ${
            alignmentStyles[alignment.tier] || alignmentStyles.low
          }`}
          title={alignment.tooltip}
        >
          <span className="font-semibold shrink-0">{alignment.alignment_pct}% aligned</span>
          <span>{alignment.headline}</span>
        </div>
      ) : null}

      {alignment?.mismatch_note ? (
        <p className={`mt-2 text-xs ${isDarkMode ? 'text-amber-200/90' : 'text-amber-800'}`}>
          {alignment.mismatch_note}
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
        <MarkReviewedButton {...markReview} />
      </div>
    </div>
  );
};

export default BatchContextBanner;
