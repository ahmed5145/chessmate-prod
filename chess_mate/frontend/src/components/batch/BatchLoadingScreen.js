/**
 * BatchLoadingScreen.js
 *
 * Full-page loading overlay shown while batch analysis is pending or in progress.
 *
 * Props:
 *   - status: string ('pending' | 'in_progress' | other)
 *   - progress: string
 *   - completed_games: number
 *   - total_games: number
 *
 * Pure display component — no state, no API calls.
 */

import React from 'react';
import {
  Box,
  Typography,
  CircularProgress,
  LinearProgress
} from '@mui/material';

const BatchLoadingScreen = ({ status, progress, completed_games, total_games }) => {
  if (status !== 'pending' && status !== 'in_progress') {
    return null;
  }

  const safeTotalGames = Number(total_games) || 0;
  const safeCompletedGames = Number(completed_games) || 0;
  const progressValue = safeTotalGames > 0
    ? Math.min(100, Math.max(0, (safeCompletedGames / safeTotalGames) * 100))
    : 0;

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
          maxWidth: 420,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
          gap: 2
        }}
      >
        <CircularProgress size={64} color="primary" />

        <Typography variant="h6" sx={{ color: 'common.white', fontWeight: 700 }}>
          Analyzing your games...
        </Typography>

        {status === 'pending' ? (
          <Typography variant="body2" sx={{ color: 'grey.400' }}>
            Waiting to start...
          </Typography>
        ) : (
          <>
            <Typography variant="body2" sx={{ color: 'grey.400' }}>
              {progress}
            </Typography>

            <Box sx={{ width: '100%', maxWidth: 300 }}>
              <LinearProgress
                variant="determinate"
                value={progressValue}
                color="primary"
              />
            </Box>
          </>
        )}
      </Box>
    </Box>
  );
};

export default BatchLoadingScreen;
