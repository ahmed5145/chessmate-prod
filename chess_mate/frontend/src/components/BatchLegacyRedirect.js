import React, { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import LoadingSpinner from './LoadingSpinner';

/**
 * Redirect legacy batch report URLs to /batch-report/:batchId (integer PK).
 */
const BatchLegacyRedirect = () => {
  const navigate = useNavigate();
  const { taskId, reportId } = useParams();
  const raw = reportId || taskId;

  useEffect(() => {
    if (!raw) {
      navigate('/batch-analysis', { replace: true });
      return;
    }

    if (/^\d+$/.test(String(raw))) {
      const target = `/batch-report/${raw}`;
      // Hard navigation avoids SPA catch-all sending users to /dashboard on stale bundles.
      window.location.replace(target);
      return;
    }

    toast.error('This report link is outdated. Open your report from Batch Coach history.');
    window.location.replace('/batch-analysis');
  }, [raw, navigate]);

  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <LoadingSpinner size="large" />
      <p className="text-sm text-gray-500">Opening report…</p>
    </div>
  );
};

export default BatchLegacyRedirect;
