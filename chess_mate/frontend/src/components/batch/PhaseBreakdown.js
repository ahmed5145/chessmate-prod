/**
 * PhaseBreakdown.js
 *
 * Displays performance across chess phases (opening, middlegame, endgame).
 * Shows 3 colored progress bars with trend indicators.
 *
 * Props:
 *   - batch_summary: object | null
 *       Contains phase_performance with opening/middlegame/endgame scores and trends
 *
 * Pure display component — no state, no API calls.
 */

import React from 'react';
import {
  Box,
  Typography,
  LinearProgress,
  Chip,
  Container,
  Grid,
  Paper
} from '@mui/material';

const PhaseBreakdown = ({ batch_summary }) => {
  // Return null if batch_summary missing or no phase_performance
  if (!batch_summary || !batch_summary.phase_performance) {
    return null;
  }

  const phases = batch_summary.phase_performance;
  const phaseKeys = ['opening', 'middlegame', 'endgame'];

  /**
   * Get color for LinearProgress based on score (0-1 scale)
   */
  const getProgressColor = (score) => {
    if (score >= 0.75) return 'success';
    if (score >= 0.5) return 'warning';
    return 'error';
  };

  /**
   * Get Chip color and label based on trend
   */
  const getTrendChip = (trend) => {
    if (!trend) return { color: 'default', label: 'No data' };

    const trendLower = trend.toLowerCase();
    if (trendLower === 'strong') return { color: 'success', label: 'Strong' };
    if (trendLower === 'inconsistent') return { color: 'warning', label: 'Inconsistent' };
    if (trendLower === 'weak') return { color: 'error', label: 'Weak' };
    if (trendLower === 'no_data') return { color: 'default', label: 'No data' };

    // Default fallback
    return { color: 'default', label: trendLower };
  };

  /**
   * Capitalize phase name
   */
  const capitalize = (str) => str.charAt(0).toUpperCase() + str.slice(1);

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h6" sx={{ mb: 1, fontWeight: 600 }}>
        Phase performance
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 3 }}>
        Eval stability by phase (higher is better). Not Chess.com accuracy or ACPL.
      </Typography>

      <Grid container spacing={3}>
        {phaseKeys.map((phaseKey) => {
          const phaseData = phases[phaseKey];
          if (!phaseData) return null;

          const score = phaseData.score || 0;
          const trend = phaseData.trend || null;
          const progressValue = Math.round(score * 100);
          const progressColor = getProgressColor(score);
          const trendChip = getTrendChip(trend);

          return (
            <Grid item xs={12} key={phaseKey}>
              <Paper
                sx={{
                  p: 2,
                  bgcolor: 'background.paper',
                  border: '1px solid',
                  borderColor: 'divider'
                }}
              >
                {/* Phase label row: name on left, score on right */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    {capitalize(phaseKey)}
                  </Typography>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'primary.main' }}>
                    {progressValue}% stable
                  </Typography>
                </Box>

                {/* Progress bar */}
                <Box sx={{ mb: 1.5 }}>
                  <LinearProgress
                    variant="determinate"
                    value={progressValue}
                    color={progressColor}
                    sx={{ height: 8, borderRadius: 1 }}
                  />
                </Box>

                {/* Trend chip below bar */}
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Chip
                    label={trendChip.label}
                    color={trendChip.color}
                    variant="outlined"
                    size="small"
                    sx={{ fontSize: '0.75rem' }}
                  />
                </Box>
              </Paper>
            </Grid>
          );
        })}
      </Grid>
    </Container>
  );
};

export default PhaseBreakdown;
