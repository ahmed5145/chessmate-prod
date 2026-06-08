/**
 * TopCriticalMoments — batch-wide worst 3 moments with FEN boards (expanded by default).
 */

import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  Chip,
  Grid,
  Paper,
  Typography
} from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import FenBoardImage from './FenBoardImage';
import ReportSectionShell from './ReportSectionShell';
import { findGameResultById, formatGameLabelById } from '../../utils/formatGameLabel';
import { formatNumber } from '../../utils/formatNumber';
import { sanitizeReportFloats } from '../../utils/sanitizeReportText';
import {
  getGamePlatformLabel,
  getGamePlatformUrl,
  scrollToBatchGame,
} from '../../utils/batchGameLinks';
import { buildSingleGameAnalysisLink } from '../../utils/singleGameAnalysisLinks';

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

const TopCriticalMoments = ({ batch_summary, per_game_results, readOnly = false, batchId = null }) => {
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
    <ReportSectionShell
      title="Biggest turning points in your games"
      subtitle="Your largest eval swings in this batch — positions before your move (engine depth 14)."
    >
      <Grid container spacing={2}>
        {moments.map((moment, index) => {
          const platformUrl = moment.platform_game_url || getGamePlatformUrl(per_game_results, moment.game_id);
          const metaParts = [
            `Move ${moment.move_number}`,
            moment.game_id ? formatGameLabelById(per_game_results, moment.game_id) : null,
            moment.player_color ? `You were ${moment.player_color}` : null,
          ].filter(Boolean);

          return (
            <Grid item xs={12} md={4} key={`top-moment-${moment.game_id}-${moment.move_number}-${index}`}>
              <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center', mb: 1 }}>
                  <Chip
                    size="small"
                    label={moment.type || 'moment'}
                    color={momentSeverityColor(moment.type)}
                  />
                  <Typography variant="caption" color="text.secondary">
                    {metaParts.join(' · ')}
                  </Typography>
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
                    {sanitizeReportFloats(moment.explanation)}
                  </Typography>
                )}
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1.5 }}>
                  {moment.game_id ? (
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => scrollToBatchGame(moment.game_id)}
                    >
                      View in breakdown
                    </Button>
                  ) : null}
                  {platformUrl ? (
                    <Button
                      size="small"
                      variant="outlined"
                      href={platformUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      endIcon={<OpenInNewIcon fontSize="small" />}
                    >
                      Open on {getGamePlatformLabel(per_game_results, moment.game_id)}
                    </Button>
                  ) : null}
                  {!readOnly && moment.saved_game_id ? (
                    <Button
                      size="small"
                      variant="text"
                      component={RouterLink}
                      to={buildSingleGameAnalysisLink({
                        gameId: moment.saved_game_id,
                        batchId,
                        move: moment.move_number,
                      })}
                    >
                      Deep review this game
                    </Button>
                  ) : null}
                </Box>
              </Paper>
            </Grid>
          );
        })}
      </Grid>
    </ReportSectionShell>
  );
};

export default TopCriticalMoments;
