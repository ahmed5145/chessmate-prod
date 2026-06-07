/**
 * Opening repertoire gaps — lines where the player loses or underperforms.
 */

import React from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  List,
  ListItem,
  Typography
} from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { lichessOpeningSearchUrl } from '../../utils/lichessStudyLinks';
import {
  resolveOpeningInsights,
  resolveRepertoireGaps,
} from '../../utils/openingInsights';

const RepertoireGaps = ({ batch_summary, per_game_results = [] }) => {
  const gaps = resolveRepertoireGaps(batch_summary, per_game_results);
  const openingInsights = resolveOpeningInsights(batch_summary, per_game_results);

  if (openingInsights.length === 0) {
    return (
      <Container maxWidth="lg" sx={{ py: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>
          Repertoire gaps
        </Typography>
        <Alert severity="info" variant="outlined">
          <Typography variant="body2">
            No recognizable opening data in this batch. Import games with ECO/opening tags or run a
            new batch analysis to see repertoire feedback.
          </Typography>
        </Alert>
      </Container>
    );
  }

  const exampleGame = (gap) => {
    if (!Array.isArray(per_game_results)) {
      return null;
    }
    return per_game_results.find(
      (game) =>
        (game.opening_name === gap.opening_name ||
          String(game.opening_name || '').startsWith(`${gap.opening_name}:`)) &&
        game.player_color === gap.player_color &&
        game.platform_game_url
    );
  };

  return (
    <Container maxWidth="lg" sx={{ py: 2 }}>
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>
        Repertoire gaps
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Opening lines that cost you multiple games or scored poorly in the opening phase.
      </Typography>

      {gaps.length === 0 ? (
        <Alert severity="info" variant="outlined" sx={{ mb: 2 }}>
          <Typography variant="body2">
            Nothing flagged as a major gap this batch — see <strong>Opening matchups</strong> for
            how each line went.
          </Typography>
        </Alert>
      ) : (
        <List dense disablePadding>
          {gaps.map((gap) => {
            const linkedGame = exampleGame(gap);
            return (
              <ListItem
                key={`${gap.opening_name}-${gap.player_color}`}
                sx={{
                  flexDirection: 'column',
                  alignItems: 'flex-start',
                  py: 1.5,
                  borderLeft: 3,
                  borderColor: 'error.main',
                  pl: 2,
                  mb: 1
                }}
              >
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 0.5 }}>
                  <Chip size="small" label={gap.opening_name} color="error" variant="outlined" />
                  {gap.eco_code && (
                    <Chip size="small" label={`ECO ${gap.eco_code}`} variant="outlined" />
                  )}
                  {gap.player_color && (
                    <Chip size="small" label={`as ${gap.player_color}`} variant="outlined" />
                  )}
                  {gap.record && <Chip size="small" label={gap.record} variant="outlined" />}
                </Box>
                <Typography variant="body2" sx={{ mb: 1 }}>
                  {gap.summary ? (
                    gap.summary
                  ) : (
                    <>
                      Review <strong>{gap.opening_name}</strong> as {gap.player_color || 'your color'}.
                    </>
                  )}
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  <Box
                    component="a"
                    href={lichessOpeningSearchUrl(gap.opening_name)}
                    target="_blank"
                    rel="noopener noreferrer"
                    sx={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 0.5,
                      fontSize: '0.875rem',
                      color: 'primary.main',
                      textDecoration: 'none',
                      '&:hover': { textDecoration: 'underline' }
                    }}
                  >
                    Study on Lichess
                    <OpenInNewIcon sx={{ fontSize: 16 }} />
                  </Box>
                  {linkedGame?.platform_game_url ? (
                    <Button
                      size="small"
                      variant="text"
                      href={linkedGame.platform_game_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      endIcon={<OpenInNewIcon fontSize="small" />}
                    >
                      View game on {linkedGame.platform || 'platform'}
                    </Button>
                  ) : null}
                </Box>
              </ListItem>
            );
          })}
        </List>
      )}

    </Container>
  );
};

export default RepertoireGaps;
