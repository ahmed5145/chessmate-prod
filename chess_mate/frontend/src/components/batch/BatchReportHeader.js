/**
 * BatchReportHeader.js — aggregate stats from batch_summary (Stockfish-derived, not coaching AI).
 */

import React from 'react';
import { Box, Chip, Container, Grid, Paper, Tooltip, Typography } from '@mui/material';
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
    <Container maxWidth="lg" sx={{ py: 2 }}>
      <Paper sx={{ p: 3, border: '1px solid', borderColor: 'divider' }}>
        <Typography variant="overline" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          Batch analysis · {analyzed} games
          {dateRange ? ` · ${dateRange}` : ''}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
          Engine depth 14 · move labels and accuracy are Stockfish-derived, not AI guesses.
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
              <Tooltip title="Chess.com-style accuracy from engine centipawn loss per move (your moves only).">
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Accuracy
                  </Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    {Number(accuracyPct).toFixed(1)}%
                  </Typography>
                </Box>
              </Tooltip>
            </Grid>
          )}
          <Grid item xs={6} sm={3}>
            <Tooltip title="Internal eval stability score (batch-wide). Differs from per-game breakdown.">
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
          {batch_summary.most_common_blunder_type && (
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
    </Container>
  );
};

export default BatchReportHeader;
