/**
 * BatchReportHeader.js — aggregate stats from batch_summary (Stockfish-derived, not coaching AI).
 */

import React from 'react';
import { Box, Chip, Grid, Paper, Typography } from '@mui/material';
import MetricInfoIcon from '../shared/MetricInfoIcon';
import { toTitleCase } from '../../utils/formatLabel';
import FixRateCard from './FixRateCard';

const BatchReportHeader = ({ batch_summary, games_count, fix_rate: fixRate, batchId = null }) => {
  if (!batch_summary) {
    return null;
  }

  const wld = batch_summary.win_loss_draw || {};
  const stabilityRaw =
    batch_summary.overall_eval_stability ?? batch_summary.overall_accuracy ?? 0;
  const stabilityPct = Math.round(Number(stabilityRaw) * 100);
  const accuracyPct = batch_summary.overall_accuracy_pct;
  const analyzed = batch_summary.games_analyzed ?? games_count ?? 0;
  const rating = batch_summary.player_rating;
  const dateRange = batch_summary.date_range;

  return (
    <Box sx={{ py: 2 }}>
      <FixRateCard fixRate={fixRate} batchId={batchId} />
      <Paper sx={{ p: 3, border: '1px solid', borderColor: 'divider' }}>
        <Typography variant="overline" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          Batch Coach · {analyzed} games
          {dateRange ? ` · ${dateRange}` : ''}
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.25, mb: 1 }}>
          <Typography variant="caption" color="text.secondary">
            Engine stats (Stockfish depth 14)
          </Typography>
          <MetricInfoIcon metricKeys={['move_match', 'eval_stability']} />
        </Box>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={6} sm={3}>
            <Typography variant="caption" color="text.secondary">
              Record
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 700 }}>
              {wld.wins ?? 0}W · {wld.losses ?? 0}L · {wld.draws ?? 0}D
            </Typography>
          </Grid>
          {accuracyPct != null && (
            <Grid item xs={6} sm={3}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Typography variant="caption" color="text.secondary">
                  Move match %
                </Typography>
                <MetricInfoIcon metricKey="move_match" />
              </Box>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {Number(accuracyPct).toFixed(1)}%
              </Typography>
            </Grid>
          )}
          <Grid item xs={6} sm={3}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Typography variant="caption" color="text.secondary">
                Eval stability
              </Typography>
              <MetricInfoIcon metricKey="eval_stability" />
            </Box>
            <Typography variant="h6" sx={{ fontWeight: 700 }}>
              {stabilityPct}%
            </Typography>
          </Grid>
          {rating != null && (
            <Grid item xs={6} sm={3}>
              <Typography variant="caption" color="text.secondary">
                Avg rating (batch)
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {rating}
              </Typography>
            </Grid>
          )}
          {batch_summary.most_common_blunder_type &&
            String(batch_summary.most_common_blunder_type).toLowerCase() !== 'unknown' && (
            <Grid item xs={12} sm={3}>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: { xs: 1, sm: 2 } }}>
                <Chip
                  size="small"
                  label={`Top issue: ${toTitleCase(batch_summary.most_common_blunder_type)}`}
                  color="warning"
                  variant="outlined"
                />
              </Box>
            </Grid>
          )}
        </Grid>
      </Paper>
    </Box>
  );
};

export default BatchReportHeader;
