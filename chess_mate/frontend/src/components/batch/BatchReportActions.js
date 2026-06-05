/**
 * Share link + print actions for batch report owners.
 */

import React, { useState } from 'react';
import { toast } from 'react-hot-toast';
import { Button, Stack, Typography } from '@mui/material';
import {
  enableBatchShare,
  revokeBatchShare
} from '../../services/apiRequests';

const BatchReportActions = ({
  batchId,
  shareToken,
  onShareTokenChange,
  canRegenerate,
  regenerating,
  onRegenerateCoaching,
  hasCoaching
}) => {
  const [sharing, setSharing] = useState(false);

  const handlePrint = () => {
    window.print();
  };

  const handleShare = async () => {
    if (!batchId || sharing) {
      return;
    }
    setSharing(true);
    try {
      const data = await enableBatchShare(batchId);
      onShareTokenChange?.(data.share_token);
      const url = data.share_url || `${window.location.origin}/share/batch/${data.share_token}`;
      await navigator.clipboard.writeText(url);
      toast.success('Share link copied to clipboard.');
    } catch (error) {
      toast.error(error?.detail || error?.message || 'Could not create share link.');
    } finally {
      setSharing(false);
    }
  };

  const handleRevokeShare = async () => {
    if (!batchId || sharing) {
      return;
    }
    setSharing(true);
    try {
      await revokeBatchShare(batchId);
      onShareTokenChange?.(null);
      toast.success('Share link revoked.');
    } catch (error) {
      toast.error(error?.detail || error?.message || 'Could not revoke share link.');
    } finally {
      setSharing(false);
    }
  };

  const handleCopyExisting = async () => {
    if (!shareToken) {
      return;
    }
    const url = `${window.location.origin}/share/batch/${shareToken}`;
    await navigator.clipboard.writeText(url);
    toast.success('Share link copied.');
  };

  return (
    <Stack
      className="batch-report-no-print"
      direction={{ xs: 'column', sm: 'row' }}
      alignItems={{ xs: 'stretch', sm: 'center' }}
      justifyContent="space-between"
      spacing={1}
      sx={{ px: { xs: 0, sm: 1 } }}
    >
      <Typography variant="body2" color="text.secondary">
        {hasCoaching
          ? 'Coaching is AI-generated from your engine analysis.'
          : 'Coaching unavailable — regenerate to try again.'}
      </Typography>
      <Stack direction="row" spacing={1} flexWrap="wrap" justifyContent="flex-end">
        <Button variant="outlined" size="small" onClick={handlePrint}>
          Print / PDF
        </Button>
        {shareToken ? (
          <>
            <Button variant="outlined" size="small" disabled={sharing} onClick={handleCopyExisting}>
              Copy share link
            </Button>
            <Button variant="text" size="small" color="error" disabled={sharing} onClick={handleRevokeShare}>
              Revoke link
            </Button>
          </>
        ) : (
          <Button variant="outlined" size="small" disabled={sharing} onClick={handleShare}>
            {sharing ? 'Sharing…' : 'Share report'}
          </Button>
        )}
        {canRegenerate ? (
          <Button
            variant="outlined"
            size="small"
            disabled={regenerating}
            onClick={onRegenerateCoaching}
          >
            {regenerating ? 'Regenerating…' : 'Regenerate coaching'}
          </Button>
        ) : null}
      </Stack>
    </Stack>
  );
};

export default BatchReportActions;
