/**
 * GameAccordion.js
 * 
 * Displays a game-by-game breakdown from per-game analysis results.
 * 
 * Props:
 *   - per_game_results: array | null
 *       Array of per-game result objects
 * 
 * Pure display component — no state, no API calls.
 */

import React from 'react';
import {
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Container,
  Box
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

const GameAccordion = ({ per_game_results }) => {
  if (!per_game_results || !Array.isArray(per_game_results) || per_game_results.length === 0) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Typography variant="body1">
          No game data available.
        </Typography>
      </Container>
    );
  }

  const getResultChipColor = (result) => {
    if (result === '1-0') return 'success';
    if (result === '0-1') return 'error';
    return 'default';
  };

  const getResultLabel = (result) => {
    if (result === '1-0') return 'W';
    if (result === '0-1') return 'L';
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

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 3 }}>
        Game-by-Game Breakdown
      </Typography>

      {per_game_results.map((game, index) => {
        const phaseBreakdown = game.phase_breakdown || {};
        const moveQuality = game.move_quality || {};

        return (
          <Accordion key={game.game_id || index} sx={{ mb: 2 }}>
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
                  Game {index + 1}
                </Typography>
                <Chip
                  label={getResultLabel(game.result)}
                  color={getResultChipColor(game.result)}
                  size="small"
                />
                <Typography variant="subtitle2">
                  {game.opening_name || 'Unknown opening'}
                </Typography>
                <Typography variant="subtitle2" color="text.secondary">
                  {game.total_moves || 0} moves
                </Typography>
              </Box>
            </AccordionSummary>

            <AccordionDetails>
              <Box sx={{ display: 'grid', gap: 1.5 }}>
                <Typography variant="body2">
                  Opening accuracy: {formatPercent(game.opening_accuracy)}
                </Typography>

                <Box sx={{ display: 'grid', gap: 0.75 }}>
                  <Typography variant="body2">
                    Opening phase accuracy: {formatPercent(getPhaseScore(phaseBreakdown.opening?.avg_eval_drop))}
                  </Typography>
                  <Typography variant="body2">
                    Middlegame phase accuracy: {formatPercent(getPhaseScore(phaseBreakdown.middlegame?.avg_eval_drop))}
                  </Typography>
                  <Typography variant="body2">
                    Endgame phase accuracy: {formatPercent(getPhaseScore(phaseBreakdown.endgame?.avg_eval_drop))}
                  </Typography>
                </Box>

                <Typography variant="body2">
                  {moveQuality.blunder || 0} blunders, {moveQuality.mistake || 0} mistakes, {moveQuality.inaccuracy || 0} inaccuracies
                </Typography>
              </Box>
            </AccordionDetails>
          </Accordion>
        );
      })}
    </Container>
  );
};

export default GameAccordion;
