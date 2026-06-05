/**
 * TopCriticalMoments — batch-wide worst 3 moments with FEN boards (expanded by default).
 */

import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Chip,
  Container,
  Grid,
  Link,
  Paper,
  Typography
} from '@mui/material';
import FenBoardImage from './FenBoardImage';

const momentSeverityColor = (type) => {
  if (type === 'blunder') return 'error';
  if (type === 'mistake') return 'warning';
  return 'default';
};

const scrollToGame = (gameId) => {
  const el = document.getElementById(`batch-game-${gameId}`);
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
};

const TopCriticalMoments = ({ batch_summary, per_game_results }) => {
  let moments = Array.isArray(batch_summary?.top_critical_moments)
    ? batch_summary.top_critical_moments
    : [];

  if (moments.length === 0 && Array.isArray(per_game_results)) {
    moments = per_game_results
      .flatMap((game) =>
        (game.critical_moments || []).map((moment) => ({
          ...moment,
          game_id: game.game_id,
          saved_game_id: game.saved_game_id
        }))
      )
      .sort((a, b) => Number(b.eval_swing || 0) - Number(a.eval_swing || 0))
      .slice(0, 3);
  }

  if (moments.length === 0) {
    return null;
  }

  return (
    <Container maxWidth="lg" sx={{ py: 2 }}>
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>
        Top critical moments
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Worst eval swings in this batch — positions before your move (engine depth 14).
      </Typography>
      <Grid container spacing={2}>
        {moments.map((moment, index) => (
          <Grid item xs={12} md={4} key={`top-moment-${moment.game_id}-${moment.move_number}-${index}`}>
            <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1 }}>
                <Chip
                  size="small"
                  label={moment.type || 'moment'}
                  color={momentSeverityColor(moment.type)}
                />
                <Chip size="small" label={`Move ${moment.move_number}`} variant="outlined" />
                {moment.game_id && (
                  <Chip size="small" label={moment.game_id} variant="outlined" />
                )}
              </Box>
              {moment.fen ? (
                <Box sx={{ mb: 1.5 }}>
                  <FenBoardImage fen={moment.fen} size={240} />
                </Box>
              ) : null}
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                Played {moment.played_move || '?'} · best {moment.best_move || '?'} · swing{' '}
                {Number(moment.eval_swing || 0).toFixed(2)}
              </Typography>
              {moment.explanation && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  {moment.explanation}
                </Typography>
              )}
              <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', mt: 1.5 }}>
                {moment.game_id ? (
                  <Link
                    component="button"
                    type="button"
                    variant="body2"
                    onClick={() => scrollToGame(moment.game_id)}
                  >
                    View in breakdown
                  </Link>
                ) : null}
                {moment.saved_game_id ? (
                  <Link
                    component={RouterLink}
                    to={`/game/${moment.saved_game_id}/analysis`}
                    variant="body2"
                  >
                    Open saved game analysis
                  </Link>
                ) : null}
              </Box>
            </Paper>
          </Grid>
        ))}
      </Grid>
    </Container>
  );
};

export default TopCriticalMoments;
