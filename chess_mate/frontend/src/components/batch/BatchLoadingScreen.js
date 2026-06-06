/**
 * BatchLoadingScreen.js
 *
 * Full-page loading overlay shown while batch analysis is pending or in progress.
 */

import React from 'react';
import {
  Box,
  Typography,
  CircularProgress,
  LinearProgress,
  Alert
} from '@mui/material';
import MailOutlineIcon from '@mui/icons-material/MailOutline';
import { formatBatchDurationRange } from '../../utils/batchTimeEstimate';

const BatchLoadingScreen = ({
  status,
  progress,
  completed_games,
  total_games,
  sendsCompletionEmail = true,
}) => {
  if (status !== 'pending' && status !== 'in_progress') {
    return null;
  }

  const safeTotalGames = Number(total_games) || 0;
  const safeCompletedGames = Number(completed_games) || 0;
  const progressValue = safeTotalGames > 0
    ? Math.min(100, Math.max(0, (safeCompletedGames / safeTotalGames) * 100))
    : 0;
  const durationLabel = safeTotalGames > 0 ? formatBatchDurationRange(safeTotalGames) : 'several minutes';

  return (
    <Box
      sx={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 1000,
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        px: 2
      }}
    >
      <Box
        sx={{
          width: '100%',
          maxWidth: 480,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
          gap: 2
        }}
      >
        <CircularProgress size={64} color="primary" />

        <Typography variant="h6" sx={{ color: 'common.white', fontWeight: 700 }}>
          Building your batch coach report
        </Typography>

        <Typography variant="body2" sx={{ color: 'grey.300', maxWidth: 420 }}>
          {safeTotalGames > 0 ? (
            <>
              Analyzing <strong>{safeTotalGames}</strong> game{safeTotalGames === 1 ? '' : 's'} with Stockfish
              (depth 14, one game at a time). Typical total time: <strong>{durationLabel}</strong>.
            </>
          ) : (
            <>Preparing your batch analysis. This usually takes several minutes.</>
          )}
        </Typography>

        {status === 'pending' ? (
          <Typography variant="body2" sx={{ color: 'grey.400' }}>
            Waiting to start...
          </Typography>
        ) : (
          <>
            <Typography variant="body2" sx={{ color: 'grey.400' }}>
              {progress || `Game ${safeCompletedGames} of ${safeTotalGames}`}
            </Typography>

            <Box sx={{ width: '100%', maxWidth: 320 }}>
              <LinearProgress
                variant="determinate"
                value={progressValue}
                color="primary"
              />
              <Typography variant="caption" sx={{ color: 'grey.500', mt: 0.5, display: 'block' }}>
                {safeCompletedGames} of {safeTotalGames} games analyzed
              </Typography>
            </Box>
          </>
        )}

        <Alert
          severity="info"
          icon={<MailOutlineIcon fontSize="inherit" />}
          sx={{
            width: '100%',
            textAlign: 'left',
            bgcolor: 'rgba(25, 118, 210, 0.15)',
            color: 'grey.100',
            '& .MuiAlert-icon': { color: 'info.light' },
          }}
        >
          {sendsCompletionEmail ? (
            <>
              <strong>You can close this tab.</strong> We&apos;ll email you when your report is ready.
              You can also find it later under <strong>Batch Analysis → Saved Batch Reports</strong>.
            </>
          ) : (
            <>
              <strong>You can leave this page</strong> and return via <strong>Saved Batch Reports</strong>
              on the Batch Analysis screen. Keep this tab open if you want to jump to the report automatically.
            </>
          )}
        </Alert>
      </Box>
    </Box>
  );
};

export default BatchLoadingScreen;
