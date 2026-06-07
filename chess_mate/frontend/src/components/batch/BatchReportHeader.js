/**
 * BatchReportHeader.js — aggregate stats from batch_summary (Stockfish-derived, not coaching AI).
 */

import React from 'react';
import { Box, Chip, Grid, Paper, Tooltip, Typography } from '@mui/material';
import { toTitleCase } from '../../utils/formatLabel';

const BatchReportHeader = ({ batch_summary, games_count }) => {
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
      <Paper sx={{ p: 3, border: '1px solid', borderColor: 'divider' }}>
        <Typography variant="overline" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          Batch analysis · {analyzed} games
          {dateRange ? ` · ${dateRange}` : ''}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
          Engine stats (Stockfish depth 14). See legend below for metric definitions.
        </Typography>
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
              <Tooltip title="Share of your moves that matched Stockfish's top line in this batch.">
                <Box>
                  <Typography variant="caption" color="text.secondary">
                  Move match %
                  </Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    {Number(accuracyPct).toFixed(1)}%
                  </Typography>
                </Box>
              </Tooltip>
            </Grid>
          )}
          <Grid item xs={6} sm={3}>
            <Tooltip title="How stable your evaluation stayed across games (batch-wide composite; not the same as move match %).">
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Eval stability
                </Typography>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                  {stabilityPct}%
                </Typography>
              </Box>
            </Tooltip>
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
