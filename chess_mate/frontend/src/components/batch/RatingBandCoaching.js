/**
 * Rating-band study guidance from batch_summary.rating_band_coaching (no AI).
 */

import React from 'react';
import { Box, Container, Paper, Typography } from '@mui/material';

const RatingBandCoaching = ({ batch_summary }) => {
  const band = batch_summary?.rating_band_coaching;
  if (!band || !band.focus) {
    return null;
  }

  return (
    <Container maxWidth="lg" sx={{ py: 2 }}>
      <Paper variant="outlined" sx={{ p: 2, bgcolor: 'background.default' }}>
        <Typography variant="overline" color="text.secondary">
          For your level {band.label ? `(${band.label})` : ''}
        </Typography>
        <Typography variant="body1" sx={{ fontWeight: 600, mb: 0.5 }}>
          {band.focus}
        </Typography>
        {band.daily_drill && (
          <Typography variant="body2" color="text.secondary">
            Daily drill: {band.daily_drill}
          </Typography>
        )}
      </Paper>
    </Container>
  );
};

export default RatingBandCoaching;
