/**
 * Share link + download (print-to-PDF) for batch report owners.
 */

import React, { useState } from 'react';
import { toast } from 'react-hot-toast';
import { Button, Stack, Tooltip, Typography } from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import LinkIcon from '@mui/icons-material/Link';
import { enableBatchShare } from '../../services/apiRequests';
import { copyTextToClipboard } from '../../utils/clipboard';
import { downloadBatchReport } from '../../utils/printBatchReport';

const BatchReportActions = ({
  batchId,
  shareToken,
  onShareTokenChange,
  hasCoaching,
}) => {
  const [sharing, setSharing] = useState(false);

  const handleDownload = () => {
    try {
      downloadBatchReport();
      toast('In the print dialog, choose Save as PDF as the destination.', {
        duration: 5000,
        icon: 'ℹ️',
      });
    } catch (error) {
      toast.error('Download is not available on this device.');
    }
  };

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
          : 'Coaching is unavailable for this report.'}
      </Typography>
      <Stack direction="row" spacing={1} flexWrap="wrap" justifyContent="flex-end">
        <Tooltip title='Opens your browser print dialog — pick "Save as PDF" to download. Nav and action buttons are hidden in the export.'>
          <Button
            variant="outlined"
            size="small"
            onClick={handleDownload}
            startIcon={<DownloadIcon fontSize="small" />}
          >
            Download
          </Button>
        </Tooltip>
        <Button
          variant="outlined"
          size="small"
          disabled={sharing}
          onClick={handleCopyShareLink}
          startIcon={<LinkIcon fontSize="small" />}
        >
          {sharing ? 'Copying…' : 'Copy share link'}
        </Button>
      </Stack>
    </Stack>
  );
};

export default BatchReportActions;
