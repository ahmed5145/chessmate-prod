/**
 * Share link for batch report owners (keeps users on-platform — no PDF/download export).
 */

import React, { useState } from 'react';
import { toast } from 'react-hot-toast';
import { Button, Stack, Typography } from '@mui/material';
import LinkIcon from '@mui/icons-material/Link';
import { enableBatchShare } from '../../services/apiRequests';
import { copyTextToClipboard } from '../../utils/clipboard';

const BatchReportActions = ({
  batchId,
  shareToken,
  onShareTokenChange,
  hasCoaching,
}) => {
  const [sharing, setSharing] = useState(false);

  const handleCopyShareLink = async () => {
    if (!batchId || sharing) {
      return;
    }

    setSharing(true);
    try {
      let token = shareToken;
      let url;

      if (!token) {
        const data = await enableBatchShare(batchId);
        token = data.share_token;
        onShareTokenChange?.(token);
        url = data.share_url || `${window.location.origin}/share/batch/${token}`;
      } else {
        url = `${window.location.origin}/share/batch/${token}`;
      }

      const copied = await copyTextToClipboard(url);
      if (copied) {
        toast.success('Share link copied — anyone with the link can view this report (read-only).', {
          duration: 4500
        });
      } else {
        toast.success(url, { duration: 8000 });
      }
    } catch (error) {
      toast.error(error?.detail || error?.message || 'Could not create share link.');
    } finally {
      setSharing(false);
    }
  };

  return (
    <Stack
      className="batch-report-no-print batch-report-actions"
      direction={{ xs: 'column', md: 'row' }}
      alignItems={{ xs: 'stretch', md: 'center' }}
      justifyContent="space-between"
      spacing={1.25}
      sx={{ width: '100%', maxWidth: '100%', minWidth: 0 }}
    >
      <Typography
        variant="body2"
        color="text.secondary"
        sx={{ width: '100%', minWidth: 0, lineHeight: 1.45 }}
      >
        {hasCoaching
          ? 'Coaching is AI-generated from your engine analysis.'
          : 'Coaching is unavailable for this report.'}
      </Typography>
      <Stack
        direction="row"
        spacing={1}
        flexWrap="wrap"
        useFlexGap
        sx={{ width: { xs: '100%', md: 'auto' }, minWidth: 0, justifyContent: { xs: 'stretch', md: 'flex-end' } }}
      >
        <Button
          variant="outlined"
          size="small"
          disabled={sharing}
          onClick={handleCopyShareLink}
          startIcon={<LinkIcon fontSize="small" />}
          sx={{ flex: { xs: 1, md: 'none' }, minWidth: 0 }}
        >
          {sharing ? 'Copying…' : 'Copy share link'}
        </Button>
      </Stack>
    </Stack>
  );
};

export default BatchReportActions;
