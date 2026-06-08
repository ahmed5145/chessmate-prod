/**
 * BatchLoadingScreen.js
 *
 * Full-page loading overlay shown while batch analysis is pending or in progress.
 */

import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Typography,
  CircularProgress,
  LinearProgress,
  Alert,
  Button,
  Stack
} from '@mui/material';
import MailOutlineIcon from '@mui/icons-material/MailOutline';
import { formatBatchDurationRange } from '../../utils/batchTimeEstimate';
import {
  BATCH_COACH_BUILDING_TITLE,
  BATCH_COACH_NAV_LABEL,
  BATCH_COACH_PREPARING,
  BATCH_COACH_SAVED_BREADCRUMB,
  SAVED_BATCH_COACH_REPORTS,
} from '../../utils/batchCoachLabels';

const NAVBAR_HEIGHT_PX = 64;

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
        top: `${NAVBAR_HEIGHT_PX}px`,
        left: 0,
        width: '100%',
        height: `calc(100% - ${NAVBAR_HEIGHT_PX}px)`,
        zIndex: 40,
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
          {BATCH_COACH_BUILDING_TITLE}
        </Typography>

        <Typography variant="body2" sx={{ color: 'grey.300', maxWidth: 420 }}>
          {safeTotalGames > 0 ? (
            <>
              Analyzing <strong>{safeTotalGames}</strong> game{safeTotalGames === 1 ? '' : 's'} with Stockfish
              (depth 14, one game at a time). Typical total time: <strong>{durationLabel}</strong>.
            </>
          ) : (
            <>{BATCH_COACH_PREPARING}</>
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
              You can also find it later under <strong>{BATCH_COACH_SAVED_BREADCRUMB}</strong>.
            </>
          ) : (
            <>
              <strong>You can leave this page</strong> and return via <strong>{SAVED_BATCH_COACH_REPORTS}</strong>
              on the {BATCH_COACH_NAV_LABEL} screen. Keep this tab open if you want to jump to the report automatically.
            </>
          )}
        </Alert>

        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ width: '100%' }}>
          <Button
            component={RouterLink}
            to="/dashboard"
            variant="outlined"
            size="small"
            sx={{ color: 'grey.100', borderColor: 'grey.500', flex: 1 }}
          >
            Back to dashboard
          </Button>
          <Button
            component={RouterLink}
            to="/batch-analysis"
            variant="outlined"
            size="small"
            sx={{ color: 'grey.100', borderColor: 'grey.500', flex: 1 }}
          >
            {BATCH_COACH_NAV_LABEL}
          </Button>
        </Stack>
      </Box>
    </Box>
  );
};

export default BatchLoadingScreen;
