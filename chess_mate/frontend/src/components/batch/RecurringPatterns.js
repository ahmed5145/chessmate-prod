/**
 * RecurringPatterns.js — weaknesses & strengths from batch_summary (data-driven).
 */

import React from 'react';
import {
  Alert,
  Box,
  Chip,
  Container,
  List,
  ListItem,
  ListItemText,
  Typography
} from '@mui/material';

const RecurringPatterns = ({ batch_summary }) => {
  if (!batch_summary) {
    return null;
  }

  const weaknesses = Array.isArray(batch_summary.recurring_weaknesses)
    ? batch_summary.recurring_weaknesses
    : [];
  const strengths = Array.isArray(batch_summary.strength_patterns)
    ? batch_summary.strength_patterns
    : [];

  if (weaknesses.length === 0 && strengths.length === 0) {
    return null;
  }

  return (
    <Container maxWidth="lg" sx={{ py: 2 }}>
      {weaknesses.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
            Recurring weaknesses (from your games)
          </Typography>
          <List dense disablePadding>
            {weaknesses.map((item, index) => (
              <ListItem
                key={`weak-${item.pattern || index}`}
                sx={{
                  flexDirection: 'column',
                  alignItems: 'flex-start',
                  py: 1.5,
                  borderLeft: 3,
                  borderColor: 'error.main',
                  pl: 2,
                  mb: 1,
                  bgcolor: 'background.paper'
                }}
              >
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 0.5 }}>
                  <Chip size="small" label={item.pattern || 'unknown'} color="error" variant="outlined" />
                  <Chip size="small" label={item.frequency || ''} variant="outlined" />
                  {item.impact && (
                    <Chip size="small" label={item.impact} color="warning" variant="outlined" />
                  )}
                </Box>
                <ListItemText
                  primary={`Avg eval swing: ${Number(item.avg_eval_swing || 0).toFixed(1)}`}
                  secondary={
                    Array.isArray(item.example_game_ids) && item.example_game_ids.length > 0
                      ? `Seen in: ${item.example_game_ids.join(', ')}`
                      : null
                  }
                  primaryTypographyProps={{ variant: 'body2', fontWeight: 600 }}
                  secondaryTypographyProps={{ variant: 'caption' }}
                />
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      {strengths.length > 0 && (
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
            Strength patterns
          </Typography>
          <List dense disablePadding>
            {strengths.map((item, index) => (
              <ListItem key={`strong-${item.pattern || index}`} sx={{ py: 0.75, pl: 0 }}>
                <ListItemText
                  primary={item.detail || item.pattern}
                  secondary={item.frequency ? `Frequency: ${item.frequency}` : null}
                  primaryTypographyProps={{ variant: 'body2' }}
                />
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      <Alert severity="info" sx={{ mt: 2 }} variant="outlined">
        <Typography variant="caption">
          These patterns are computed from engine analysis of your PGNs. Coaching priorities below are AI-generated from this data.
        </Typography>
      </Alert>
    </Container>
  );
};

export default RecurringPatterns;
