/**
 * Single degraded-coaching notice for the batch report (replaces per-section alerts).
 */

import React from 'react';
import { Alert, Container, Typography } from '@mui/material';

const CoachingUnavailableBanner = ({ coachingReport }) => {
  if (coachingReport) {
    return null;
  }

  return (
    <Container maxWidth="lg" sx={{ py: 0, pb: 1 }}>
      <Alert severity="info" variant="outlined">
        <Typography variant="body2">
          AI coaching narrative is unavailable for this batch. Stockfish stats, openings, and game
          breakdown below are still complete.
        </Typography>
      </Alert>
    </Container>
  );
};

export default CoachingUnavailableBanner;
