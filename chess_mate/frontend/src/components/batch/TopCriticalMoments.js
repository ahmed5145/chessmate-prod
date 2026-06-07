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
import { findGameResultById, formatGameLabelById } from '../../utils/formatGameLabel';
import { formatNumber } from '../../utils/formatNumber';
import {
  getGamePlatformLabel,
  scrollToBatchGame,
} from '../../utils/batchGameLinks';

const momentSeverityColor = (type) => {
  if (type === 'blunder') return 'error';
  if (type === 'mistake') return 'warning';
  return 'default';
};

const enrichMoment = (moment, per_game_results) => {
  const game = findGameResultById(per_game_results, moment.game_id);
  return {
    ...moment,
    player_color: moment.player_color || game?.player_color,
    platform_game_url: moment.platform_game_url || game?.platform_game_url,
    platform: moment.platform || game?.platform,
  };
};

const TopCriticalMoments = ({ batch_summary, per_game_results, readOnly = false }) => {
  let moments = Array.isArray(batch_summary?.top_critical_moments)
    ? [...batch_summary.top_critical_moments]
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

  moments = moments.map((moment) => enrichMoment(moment, per_game_results));

  if (moments.length === 0) {
    return null;
  }

  return (
    <Container maxWidth="lg" sx={{ py: 2 }}>
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>
        Biggest turning points in your games
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Your largest eval swings in this batch — positions before your move (engine depth 14).
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
                  <Chip
                    size="small"
                    label={formatGameLabelById(per_game_results, moment.game_id)}
                    variant="outlined"
                  />
                )}
                {moment.player_color && (
                  <Chip
                    size="small"
                    label={`You were ${moment.player_color}`}
                    variant="outlined"
                    color="info"
                  />
                )}
              </Box>
              {moment.fen ? (
                <Box sx={{ mb: 1.5 }}>
                  <FenBoardImage
                    fen={moment.fen}
                    size={240}
                    orientation={moment.player_color || 'white'}
                    playedMoveUci={moment.played_move_uci}
                    bestMoveUci={moment.best_move_uci}
                  />
                </Box>
              ) : null}
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                You played {moment.played_move || '?'} · best for you {moment.best_move || '?'} · swing{' '}
                {formatNumber(moment.eval_swing, 2)}
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
                    onClick={() => scrollToBatchGame(moment.game_id)}
                  >
                    View in breakdown
                  </Link>
                ) : null}
                {moment.platform_game_url ? (
                  <Link
                    href={moment.platform_game_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    variant="body2"
                  >
                    View on {getGamePlatformLabel(per_game_results, moment.game_id)}
                  </Link>
                ) : null}
                {!readOnly && moment.saved_game_id ? (
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
