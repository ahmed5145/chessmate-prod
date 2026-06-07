/**
 * RecurringPatterns.js — weaknesses, strengths, opening records, endgame spots.
 */

import React from 'react';
import {
  Box,
  Button,
  Chip,
  Container,
  List,
  ListItem,
  ListItemText,
  Paper,
  Typography
} from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { formatGameLabelById } from '../../utils/formatGameLabel';
import { formatNumber } from '../../utils/formatNumber';
import {
  getGamePlatformLabel,
  getGamePlatformUrl,
  scrollToBatchGame,
} from '../../utils/batchGameLinks';
import { resolveOpeningInsights } from '../../utils/openingInsights';

const GameExampleActions = ({ perGameResults, gameId, moveNumber }) => {
  const platformUrl = getGamePlatformUrl(perGameResults, gameId);
  const platformLabel = getGamePlatformLabel(perGameResults, gameId);

  return (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
      {platformUrl ? (
        <Button
          size="small"
          variant="outlined"
          href={platformUrl}
          target="_blank"
          rel="noopener noreferrer"
          endIcon={<OpenInNewIcon fontSize="small" />}
        >
          View on {platformLabel}
        </Button>
      ) : null}
      {gameId ? (
        <Button size="small" variant="text" onClick={() => scrollToBatchGame(gameId)}>
          {moveNumber ? `See move ${moveNumber} in report` : 'See in game breakdown'}
        </Button>
      ) : null}
    </Box>
  );
};

const RecurringPatterns = ({ batch_summary, per_game_results = [] }) => {
  if (!batch_summary) {
    return null;
  }

  const weaknesses = Array.isArray(batch_summary.recurring_weaknesses)
    ? batch_summary.recurring_weaknesses
    : [];
  const strengths = Array.isArray(batch_summary.strength_patterns)
    ? batch_summary.strength_patterns
    : [];
  const openingInsights = resolveOpeningInsights(batch_summary, per_game_results);
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
          <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>
            Opening matchups
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Record by specific ECO line in this batch — each variation is listed separately with its score.
          </Typography>
          <List dense disablePadding>
            {openingInsights.map((item) => (
              <ListItem
                key={`${item.opening_name}-${item.player_color || 'x'}`}
                sx={{
                  flexDirection: 'column',
                  alignItems: 'flex-start',
                  py: 1.5,
                  borderLeft: 3,
                  borderColor:
                    item.status === 'struggling' || item.status === 'needs_work'
                      ? 'warning.main'
                      : item.status === 'strong'
                        ? 'success.main'
                        : 'divider',
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
                {item.study_url && (
                  <Button
                    size="small"
                    variant="outlined"
                    href={item.study_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    endIcon={<OpenInNewIcon fontSize="small" />}
                    sx={{ mt: 0.5 }}
                  >
                    Practice on Lichess
                  </Button>
                )}
                {Array.isArray(item.example_moments) && item.example_moments.length > 0 && (
                  <Box sx={{ mt: 1, width: '100%' }}>
                    {item.example_moments.slice(0, 2).map((ex, idx) => (
                      <Box key={`${ex.game_id}-${ex.move_number}-${idx}`} sx={{ mb: 1 }}>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {formatGameLabelById(per_game_results, ex.game_id)} · move {ex.move_number}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          You played {ex.played_move || '?'} · engine suggests {ex.best_move || '?'}
                        </Typography>
                        <GameExampleActions
                          perGameResults={per_game_results}
                          gameId={ex.game_id}
                          moveNumber={ex.move_number}
                        />
                      </Box>
                    ))}
                  </Box>
                )}
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      {weaknesses.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
            Recurring weaknesses
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
                  primary={item.detail || `Avg eval swing: ${formatNumber(item.avg_eval_swing, 2)}`}
                  primaryTypographyProps={{ variant: 'body2', fontWeight: 600 }}
                />
                {Array.isArray(item.example_game_ids) && item.example_game_ids.length > 0 && (
                  <Box sx={{ mt: 0.5 }}>
                    {item.example_game_ids.slice(0, 2).map((gameId) => (
                      <Box key={gameId} sx={{ mb: 0.5 }}>
                        <Typography variant="caption" color="text.secondary">
                          Example: {formatGameLabelById(per_game_results, gameId)}
                        </Typography>
                        <GameExampleActions perGameResults={per_game_results} gameId={gameId} />
                      </Box>
                    ))}
                  </Box>
                )}
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      {strengths.length > 0 && (
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
            What you did well
          </Typography>
          <Box sx={{ display: 'grid', gap: 1.5 }}>
            {strengths.map((item, index) => (
              <Paper key={`strong-${item.pattern || index}`} variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
                  {item.pattern ? String(item.pattern).replace(/_/g, ' ') : 'Strength'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {item.detail || item.pattern}
                </Typography>
                {item.frequency ? (
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                    Seen in {item.frequency}
                  </Typography>
                ) : null}
              </Paper>
            ))}
          </Box>
        </Box>
      )}
    </Container>
  );
};

export default RecurringPatterns;
