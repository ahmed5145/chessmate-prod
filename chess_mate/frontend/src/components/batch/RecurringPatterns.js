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
  const openingInsights = Array.isArray(batch_summary.opening_insights)
    ? batch_summary.opening_insights
    : [];
  const endgameInsights = Array.isArray(batch_summary.endgame_insights)
    ? batch_summary.endgame_insights
    : [];

  if (
    weaknesses.length === 0 &&
    strengths.length === 0 &&
    openingInsights.length === 0 &&
    endgameInsights.length === 0
  ) {
    return null;
  }

  return (
    <Container maxWidth="lg" sx={{ py: 2 }}>
      {openingInsights.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
            Opening matchups (your games)
          </Typography>
          <List dense disablePadding>
            {openingInsights.map((item) => (
              <ListItem
                key={item.opening_name}
                sx={{
                  flexDirection: 'column',
                  alignItems: 'flex-start',
                  py: 1.5,
                  borderLeft: 3,
                  borderColor: item.status === 'struggling' ? 'error.main' : 'success.main',
                  pl: 2,
                  mb: 1
                }}
              >
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 0.5 }}>
                  <Chip size="small" label={item.opening_name} color="primary" variant="outlined" />
                  {item.eco_code && (
                    <Chip size="small" label={`ECO ${item.eco_code}`} variant="outlined" />
                  )}
                  <Chip size="small" label={item.record || ''} variant="outlined" />
                  {item.avg_opening_score != null && (
                    <Chip
                      size="small"
                      label={`Opening phase ${Math.round(item.avg_opening_score * 100)}%`}
                      variant="outlined"
                    />
                  )}
                </Box>
                {item.recommendation && (
                  <Typography variant="body2">{item.recommendation}</Typography>
                )}
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      {endgameInsights.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
            Endgame trouble spots
          </Typography>
          <List dense disablePadding>
            {endgameInsights.map((item) => (
              <ListItem
                key={item.endgame_type}
                sx={{
                  flexDirection: 'column',
                  alignItems: 'flex-start',
                  py: 1.5,
                  borderLeft: 3,
                  borderColor: 'warning.main',
                  pl: 2,
                  mb: 1
                }}
              >
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 0.5 }}>
                  <Chip size="small" label={item.label || item.endgame_type} color="warning" variant="outlined" />
                  <Chip size="small" label={item.frequency || ''} variant="outlined" />
                </Box>
                {item.study_focus && (
                  <Typography variant="body2" sx={{ mb: 0.5 }}>
                    {item.study_focus}
                  </Typography>
                )}
                {Array.isArray(item.example_moments) && item.example_moments.length > 0 && (
                  <Typography variant="caption" color="text.secondary">
                    Examples:{' '}
                    {item.example_moments
                      .map(
                        (ex) =>
                          `${ex.game_id} move ${ex.move_number} (played ${ex.played_move}, best ${ex.best_move})`
                      )
                      .join(' · ')}
                  </Typography>
                )}
              </ListItem>
            ))}
          </List>
        </Box>
      )}

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
                  primary={item.detail || `Avg eval swing: ${Number(item.avg_eval_swing || 0).toFixed(1)}`}
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
