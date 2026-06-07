/**
 * Share link + download / print / coaching refresh for batch report owners.
 */

import React, { useState } from 'react';
import { toast } from 'react-hot-toast';
import { Button, Stack, Tooltip, Typography } from '@mui/material';
import LinkIcon from '@mui/icons-material/Link';
import RefreshIcon from '@mui/icons-material/Refresh';
import PrintIcon from '@mui/icons-material/Print';
import { enableBatchShare, regenerateBatchCoaching } from '../../services/apiRequests';
import { copyTextToClipboard } from '../../utils/clipboard';
import { downloadReportPdf } from '../../utils/downloadReportPdf';
import { printBatchReport } from '../../utils/printBatchReport';
import { formatRegenerateCoachingError } from '../../utils/batchCoachingErrors';

const BatchReportActions = ({
  batchId,
  shareToken,
  onShareTokenChange,
  hasCoaching,
  canRegenerateCoaching = false,
  onReportRefresh,
}) => {
  const [sharing, setSharing] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  const handlePrint = () => {
    try {
      printBatchReport();
    } catch (error) {
      toast.error('Browser print is not available on this device.');
    }
  };

  const handleDownloadPdf = async () => {
    if (downloading) {
      return;
    }
    setDownloading(true);
    const toastId = toast.loading('Building PDF…');
    try {
      await downloadReportPdf(`chessmate-batch-report-${batchId || 'export'}.pdf`);
      toast.success('PDF downloaded.', { id: toastId });
    } catch (error) {
      console.error('PDF download failed:', error);
      toast.error(
        'Could not generate a PDF from this report. Use Print instead — it uses your browser and usually works when PDF export fails.',
        { id: toastId, duration: 6000 }
      );
    } finally {
      setDownloading(false);
    }
  };

  const handleRegenerateCoaching = async () => {
    if (!batchId || regenerating || !canRegenerateCoaching) {
      return;
    }

    setRegenerating(true);
    const toastId = toast.loading('Refreshing coaching…');
    try {
      const updatedReport = await regenerateBatchCoaching(batchId);
      onReportRefresh?.(updatedReport);
      toast.success('Coaching refreshed from your saved engine analysis.', { id: toastId });
    } catch (error) {
      console.error('Coaching regenerate failed:', error);
      toast.error(formatRegenerateCoachingError(error), { id: toastId, duration: 5500 });
    } finally {
      setRegenerating(false);
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

  const regenerateLabel = hasCoaching ? 'Refresh coaching' : 'Generate coaching';

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
          : 'Coaching is unavailable — refresh to try generating it again.'}
      </Typography>
      <Stack direction="row" spacing={1} flexWrap="wrap" justifyContent="flex-end">
        {canRegenerateCoaching ? (
          <Tooltip title="Re-runs AI coaching from saved Stockfish data (daily limit applies).">
            <span>
              <Button
                variant="outlined"
                size="small"
                disabled={regenerating}
                onClick={handleRegenerateCoaching}
                startIcon={<RefreshIcon fontSize="small" />}
              >
                {regenerating ? 'Refreshing…' : regenerateLabel}
              </Button>
            </span>
          </Tooltip>
        ) : null}
        <Button
          variant="outlined"
          size="small"
          onClick={handlePrint}
          startIcon={<PrintIcon fontSize="small" />}
        >
          Print
        </Button>
        <Button variant="outlined" size="small" disabled={downloading} onClick={handleDownloadPdf}>
          {downloading ? 'Preparing PDF…' : 'Download PDF'}
        </Button>
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
