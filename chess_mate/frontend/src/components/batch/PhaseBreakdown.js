/**
 * PhaseBreakdown.js — performance across chess phases (opening, middlegame, endgame).
 */

import React from 'react';
import {
  Box,
  Typography,
  LinearProgress,
  Chip,
  Grid,
  Paper
} from '@mui/material';
import MetricInfoIcon from '../shared/MetricInfoIcon';
import ReportSectionShell from './ReportSectionShell';

const PhaseBreakdown = ({ batch_summary }) => {
  if (!batch_summary || !batch_summary.phase_performance) {
    return null;
  }

  const phases = batch_summary.phase_performance;
  const phaseKeys = ['opening', 'middlegame', 'endgame'];

  const getProgressColor = (score) => {
    if (score >= 0.75) return 'success';
    if (score >= 0.5) return 'warning';
    return 'error';
  };

  const getTrendChip = (trend) => {
    if (!trend) return { color: 'default', label: 'No data' };

    const trendLower = trend.toLowerCase();
    if (trendLower === 'strong') return { color: 'success', label: 'Strong' };
    if (trendLower === 'inconsistent') return { color: 'warning', label: 'Inconsistent' };
    if (trendLower === 'weak') return { color: 'error', label: 'Weak' };
    if (trendLower === 'no_data') return { color: 'default', label: 'No data' };

    return { color: 'default', label: trendLower };
  };

  const capitalize = (str) => str.charAt(0).toUpperCase() + str.slice(1);

  return (
    <ReportSectionShell
      title="Phase performance"
      titleExtra={<MetricInfoIcon metricKey="phase_move_match" />}
      subtitle="Move match % by opening, middlegame, and endgame."
    >
      <Grid container spacing={3}>
        {phaseKeys.map((phaseKey) => {
          const phaseData = phases[phaseKey];
          if (!phaseData) return null;

          const score = phaseData.score || 0;
          const trend = phaseData.trend || null;
          const accuracyPct = phaseData.accuracy_pct;
          const progressValue =
            accuracyPct != null ? Math.round(Number(accuracyPct)) : Math.round(score * 100);
          const progressColor =
            accuracyPct != null
              ? progressValue >= 75
                ? 'success'
                : progressValue >= 50
                  ? 'warning'
                  : 'error'
              : getProgressColor(score);
          const trendChip = getTrendChip(trend);
          const metricLabel =
            accuracyPct != null
              ? `${Number(accuracyPct).toFixed(1)}% move match`
              : `${Math.round(score * 100)}% stable`;

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
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    {capitalize(phaseKey)}
                  </Typography>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'primary.main' }}>
                    {metricLabel}
                  </Typography>
                </Box>

                <Box sx={{ mb: 1.5 }}>
                  <LinearProgress
                    variant="determinate"
                    value={Math.min(100, Math.max(0, progressValue))}
                    color={progressColor}
                    sx={{ height: 8, borderRadius: 1 }}
                  />
                </Box>

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
    </ReportSectionShell>
  );
};

export default PhaseBreakdown;
