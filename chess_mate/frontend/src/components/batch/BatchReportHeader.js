/**
 * BatchReportHeader.js — aggregate stats from batch_summary (Stockfish-derived, not coaching AI).
 */

import React from 'react';
import { Box, Chip, Container, Grid, Paper, Typography } from '@mui/material';

const BatchReportHeader = ({ batch_summary, games_count }) => {
  if (!batch_summary) {
    return null;
  }

  const wld = batch_summary.win_loss_draw || {};
  const stabilityPct = Math.round(Number(batch_summary.overall_accuracy || 0) * 100);
  const analyzed = batch_summary.games_analyzed ?? games_count ?? 0;
  const rating = batch_summary.player_rating;
  const dateRange = batch_summary.date_range;

  return (
    <Container maxWidth="lg" sx={{ py: 2 }}>
      <Paper sx={{ p: 3, border: '1px solid', borderColor: 'divider' }}>
        <Typography variant="overline" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
          Batch analysis · {analyzed} games
          {dateRange ? ` · ${dateRange}` : ''}
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
          <Grid item xs={6} sm={3}>
            <Typography variant="caption" color="text.secondary">
              Overall eval stability
            </Typography>
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
          {batch_summary.most_common_blunder_type && (
            <Grid item xs={12} sm={3}>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: { xs: 1, sm: 2 } }}>
                <Chip
                  size="small"
                  label={`Top issue: ${String(batch_summary.most_common_blunder_type).replace(/_/g, ' ')}`}
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
