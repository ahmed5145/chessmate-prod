import { useState } from 'react';
import { markPriorityInboxReviewed } from '../../services/apiRequests';
import { trackMarketingEvent } from '../../utils/marketingAnalytics';

/**
 * Shared state for marking a batch priority inbox item reviewed (banner + drill footer).
 */
export function useMarkPriorityReviewed(batchId, priorityIndex, onReviewed) {
  const [reviewState, setReviewState] = useState('idle');
  const [reviewError, setReviewError] = useState('');

  const showMarkReviewed = Boolean(batchId && priorityIndex);

  const handleMarkReviewed = async () => {
    if (!showMarkReviewed || reviewState === 'loading' || reviewState === 'done') {
      return;
    }
    setReviewState('loading');
    setReviewError('');
    try {
      await markPriorityInboxReviewed({
        batchId,
        priorityIndex,
      });
      trackMarketingEvent('priority_inbox_reviewed', {
        batch_id: batchId,
        priority_index: priorityIndex,
        surface: 'single_game',
      });
      setReviewState('done');
      if (typeof onReviewed === 'function') {
        onReviewed();
      }
    } catch (error) {
      setReviewState('idle');
      setReviewError(error?.detail || error?.message || 'Could not mark reviewed.');
    }
  };

  return {
    showMarkReviewed,
    reviewState,
    reviewError,
    onMarkReviewed: handleMarkReviewed,
  };
}
