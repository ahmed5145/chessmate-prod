/**
 * GameAccordion.js — per-game breakdown from Stockfish analysis (critical moments, phases).
 */

import React from 'react';
import {
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Container,
  Box,
  Divider
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

const GameAccordion = ({ per_game_results }) => {
  if (!per_game_results || !Array.isArray(per_game_results) || per_game_results.length === 0) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Typography variant="body1">No game data available.</Typography>
      </Container>
    );
  }

  const getResultChipColor = (result) => {
    if (result === '1-0') return 'success';
    if (result === '0-1') return 'error';
    return 'default';
  };

  const getResultLabel = (result, playerColor) => {
    if (result === '1/2-1/2' || result === '*') return 'D';
    const playedWhite = playerColor === 'white';
    if (result === '1-0') return playedWhite ? 'W' : 'L';
    if (result === '0-1') return playedWhite ? 'L' : 'W';
    return 'D';
  };

  const formatPercent = (value) => {
    const numericValue = Number(value);
    if (Number.isNaN(numericValue)) {
      return '0%';
    }
    const clamped = Math.max(0, Math.min(1, numericValue));
    return `${Math.round(clamped * 100)}%`;
  };

  const getPhaseScore = (avgEvalDrop) => {
    const numericValue = Number(avgEvalDrop);
    if (Number.isNaN(numericValue)) {
      return 0;
    }
    return Math.max(0, Math.min(1, 1 - numericValue));
  };

  const momentSeverityColor = (type) => {
    if (type === 'blunder') return 'error';
    if (type === 'mistake') return 'warning';
    return 'default';
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>
        Game-by-game breakdown
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Engine-derived stats and critical moments from each game in this batch.
      </Typography>

      {per_game_results.map((game, index) => {
        const phaseBreakdown = game.phase_breakdown || {};
        const moveQuality = game.move_quality || {};
        const criticalMoments = Array.isArray(game.critical_moments) ? game.critical_moments : [];
        const missedPatterns = Array.isArray(game.tactical_patterns_missed)
          ? game.tactical_patterns_missed
          : [];
        const elo =
          game.player_color === 'black'
            ? game.black_elo
            : game.player_color === 'white'
              ? game.white_elo
              : null;

        return (
          <Accordion key={game.game_id || index} defaultExpanded={index === 0} sx={{ mb: 2 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1.5,
                  flexWrap: 'wrap',
                  width: '100%'
                }}
              >
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                  {game.game_id || `Game ${index + 1}`}
                </Typography>
                <Chip
                  label={getResultLabel(game.result, game.player_color)}
                  color={getResultChipColor(game.result)}
                  size="small"
                />
                <Typography variant="subtitle2">{game.opening_name || 'Unknown opening'}</Typography>
                {game.player_color && (
                  <Chip label={game.player_color} size="small" variant="outlined" />
                )}
                {elo != null && (
                  <Typography variant="caption" color="text.secondary">
                    {elo} elo
                  </Typography>
                )}
                <Typography variant="caption" color="text.secondary">
                  {game.total_moves || 0} moves · {moveQuality.blunder || 0} blunders
                </Typography>
              </Box>
            </AccordionSummary>

            <AccordionDetails>
              <Box sx={{ display: 'grid', gap: 2 }}>
                <Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                    Move quality
                  </Typography>
                  <Typography variant="body2">
                    {moveQuality.blunder || 0} blunders · {moveQuality.mistake || 0} mistakes ·{' '}
                    {moveQuality.inaccuracy || 0} inaccuracies · {moveQuality.good || 0} good moves
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 0.5 }}>
                    Opening accuracy (game): {formatPercent(game.opening_accuracy)}
                  </Typography>
                </Box>

                <Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                    Phase performance (avg eval drop → accuracy proxy)
                  </Typography>
                  <Typography variant="body2">
                    Opening: {formatPercent(getPhaseScore(phaseBreakdown.opening?.avg_eval_drop))}
                    {phaseBreakdown.opening?.moves != null ? ` (${phaseBreakdown.opening.moves} moves)` : ''}
                  </Typography>
                  <Typography variant="body2">
                    Middlegame: {formatPercent(getPhaseScore(phaseBreakdown.middlegame?.avg_eval_drop))}
                    {phaseBreakdown.middlegame?.moves != null
                      ? ` (${phaseBreakdown.middlegame.moves} moves)`
                      : ''}
                  </Typography>
                  <Typography variant="body2">
                    Endgame: {formatPercent(getPhaseScore(phaseBreakdown.endgame?.avg_eval_drop))}
                    {phaseBreakdown.endgame?.moves != null ? ` (${phaseBreakdown.endgame.moves} moves)` : ''}
                  </Typography>
                </Box>

                {missedPatterns.length > 0 && (
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {missedPatterns.map((pattern) => (
                      <Chip
                        key={pattern}
                        label={String(pattern).replace(/_/g, ' ')}
                        size="small"
                        color="warning"
                        variant="outlined"
                      />
                    ))}
                  </Box>
                )}

                {criticalMoments.length > 0 && (
                  <Box>
                    <Divider sx={{ mb: 1.5 }} />
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                      Critical moments ({criticalMoments.length})
                    </Typography>
                    {criticalMoments.map((moment, momentIndex) => (
                      <Box
                        key={`${game.game_id}-moment-${momentIndex}`}
                        sx={{
                          mb: 2,
                          pl: 2,
                          borderLeft: 3,
                          borderColor: `${momentSeverityColor(moment.type)}.main`
                        }}
                      >
                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 0.5 }}>
                          <Chip
                            size="small"
                            label={moment.type || 'moment'}
                            color={momentSeverityColor(moment.type)}
                          />
                          <Chip size="small" label={`Move ${moment.move_number}`} variant="outlined" />
                          {moment.phase && (
                            <Chip size="small" label={moment.phase} variant="outlined" />
                          )}
                          {moment.tactical_theme && (
                            <Chip
                              size="small"
                              label={String(moment.tactical_theme).replace(/_/g, ' ')}
                              variant="outlined"
                            />
                          )}
                        </Box>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          Played {moment.played_move || '?'} · engine suggests {moment.best_move || '?'} · swing{' '}
                          {Number(moment.eval_swing || 0).toFixed(2)}
                        </Typography>
                        {moment.explanation && (
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                            {moment.explanation}
                          </Typography>
                        )}
                      </Box>
                    ))}
                  </Box>
                )}
              </Box>
            </AccordionDetails>
          </Accordion>
        );
      })}
    </Container>
  );
};

export default GameAccordion;
