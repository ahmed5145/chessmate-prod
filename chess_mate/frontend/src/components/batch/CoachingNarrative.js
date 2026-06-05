/**
 * CoachingNarrative.js — per-phase AI narrative (distinct from generic training week strings).
 */

import React from 'react';
import { Container, Grid, Paper, Typography } from '@mui/material';

const CoachingNarrative = ({ coaching_report }) => {
  const narrative = coaching_report?.coaching_narrative;
  if (!narrative || typeof narrative !== 'object') {
    return null;
  }

  const phases = [
    { key: 'opening', label: 'Opening' },
    { key: 'middlegame', label: 'Middlegame' },
    { key: 'endgame', label: 'Endgame' }
  ].filter((p) => narrative[p.key]);

  if (phases.length === 0) {
    return null;
  }

  return (
    <Container maxWidth="lg" sx={{ py: 2 }}>
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
        Phase coaching notes
      </Typography>
      <Grid container spacing={2}>
        {phases.map((phase) => (
          <Grid item xs={12} md={4} key={phase.key}>
            <Paper sx={{ p: 2, height: '100%', border: '1px solid', borderColor: 'divider' }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                {phase.label}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {narrative[phase.key]}
              </Typography>
            </Paper>
          </Grid>
        ))}
      </Grid>
      {coaching_report.one_thing_to_do_today && (
        <Paper
          sx={(theme) => ({
            mt: 2,
            p: 2,
            border: '1px solid',
            borderColor: theme.palette.mode === 'dark' ? 'primary.dark' : 'primary.main',
            bgcolor:
              theme.palette.mode === 'dark'
                ? 'rgba(99, 102, 241, 0.12)'
                : 'primary.main',
            color: theme.palette.mode === 'dark' ? 'text.primary' : 'primary.contrastText',
          })}
        >
          <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
            Do today
          </Typography>
          <Typography variant="body2">{coaching_report.one_thing_to_do_today}</Typography>
        </Paper>
      )}
    </Container>
  );
};

export default CoachingNarrative;
