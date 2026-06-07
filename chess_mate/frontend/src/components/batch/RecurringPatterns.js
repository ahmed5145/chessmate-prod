/**
 * Tactical weaknesses and endgame trouble spots (openings live in OpeningSection).
 */

import React from 'react';
import {
  Box,
  Button,
  Chip,
  List,
  ListItem,
  ListItemText,
  Typography,
} from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { formatGameLabelById } from '../../utils/formatGameLabel';
import { formatNumber } from '../../utils/formatNumber';
import ReportSectionShell, { ReportSubsection } from './ReportSectionShell';
import GameExampleActions from './GameExampleActions';

const RecurringPatterns = ({ batch_summary, per_game_results = [] }) => {
  if (!batch_summary) {
    return null;
  }

  const weaknesses = Array.isArray(batch_summary.recurring_weaknesses)
    ? batch_summary.recurring_weaknesses
    : [];
  const endgameInsights = Array.isArray(batch_summary.endgame_insights)
    ? batch_summary.endgame_insights
    : [];

  if (weaknesses.length === 0 && endgameInsights.length === 0) {
    return null;
  }

  return (
    <ReportSectionShell
      title="Tactical & endgame patterns"
      subtitle="Recurring mistake themes and endgame positions where you lost evaluation."
      showStatusHint
    >
      {endgameInsights.length > 0 ? (
        <ReportSubsection title="Endgame trouble spots">
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
                  mb: 1,
                }}
              >
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 0.5 }}>
                  <Chip size="small" label={item.label || item.endgame_type} color="warning" variant="outlined" />
                  <Chip size="small" label={item.frequency || ''} variant="outlined" />
                </Box>
                {item.study_focus ? (
                  <Typography variant="body2" sx={{ mb: 0.5 }}>
                    {item.study_focus}
                  </Typography>
                ) : null}
                {item.study_url ? (
                  <Button
                    size="small"
                    variant="outlined"
                    href={item.study_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    endIcon={<OpenInNewIcon fontSize="small" />}
                    sx={{ mt: 0.5, textTransform: 'none', fontWeight: 600 }}
                  >
                    Practice on Lichess
                  </Button>
                ) : null}
                {Array.isArray(item.example_moments) && item.example_moments.length > 0 ? (
                  <Box sx={{ mt: 1, width: '100%' }}>
                    {item.example_moments.slice(0, 2).map((ex, idx) => (
                      <Box key={`${ex.game_id}-${ex.move_number}-${idx}`} sx={{ mb: 1 }}>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {formatGameLabelById(per_game_results, ex.game_id)} · move {ex.move_number}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          You played {ex.played_move || '?'} · best for you {ex.best_move || '?'}
                        </Typography>
                        <GameExampleActions
                          perGameResults={per_game_results}
                          gameId={ex.game_id}
                          moveNumber={ex.move_number}
                        />
                      </Box>
                    ))}
                  </Box>
                ) : null}
              </ListItem>
            ))}
          </List>
        </ReportSubsection>
      ) : null}

      {weaknesses.length > 0 ? (
        <ReportSubsection title="Recurring weaknesses" sx={{ mb: 0 }}>
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
                  bgcolor: 'background.paper',
                }}
              >
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 0.5 }}>
                  <Chip size="small" label={item.pattern || 'unknown'} color="error" variant="outlined" />
                  <Chip size="small" label={item.frequency || ''} variant="outlined" />
                  {item.impact ? (
                    <Chip size="small" label={item.impact} color="warning" variant="outlined" />
                  ) : null}
                </Box>
                <ListItemText
                  primary={item.detail || `Avg eval swing: ${formatNumber(item.avg_eval_swing, 2)}`}
                  primaryTypographyProps={{ variant: 'body2', fontWeight: 600 }}
                />
                {Array.isArray(item.example_game_ids) && item.example_game_ids.length > 0 ? (
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
                ) : null}
              </ListItem>
            ))}
          </List>
        </ReportSubsection>
      ) : null}
    </ReportSectionShell>
  );
};

export default RecurringPatterns;
