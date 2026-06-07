/**
 * PriorityCard.js
 *
 * Displays a single priority (one of top 3) with rank, title, and detailed guidance.
 *
 * Props:
 *   - priority: object | null
 *       {
 *         rank: 1|2|3,
 *         title: string,
 *         why_it_matters: string,
 *         how_to_fix: string,
 *         specific_drill: string,
 *         estimated_study_hours: number
 *       }
 *
 * Pure display component — no state, no API calls.
 */

import React from 'react';
import {
  Card,
  CardContent,
  Box,
  Typography,
  Chip,
  Button
} from '@mui/material';

const extractGameIds = (...parts) => {
  const text = parts.filter(Boolean).join(' ');
  const matches = text.match(/game_\d+/gi) || [];
  return [...new Set(matches.map((id) => id.toLowerCase()))];
};

const scrollToGame = (gameId) => {
  const el = document.getElementById(`batch-game-${gameId}`);
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
};

const PriorityCard = ({ priority }) => {
  // Validate priority object
  if (!priority || typeof priority !== 'object') {
    return null;
  }

  const {
    rank,
    title,
    why_it_matters,
    how_to_fix,
    specific_drill,
  } = priority;

  if (!rank || !title || !why_it_matters || !how_to_fix || !specific_drill) {
    return null;
  }

  /**
   * Map rank to MUI Chip color
   */
  const getRankColor = (rankNum) => {
    if (rankNum === 1) return 'error';
    if (rankNum === 2) return 'warning';
    if (rankNum === 3) return 'info';
    return 'default';
  };

  const rankColor = getRankColor(rank);
  const linkedGames = extractGameIds(title, why_it_matters, specific_drill);

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        {/* Rank badge at top-left */}
        <Box sx={{ mb: 2 }}>
          <Chip
            label={rank}
            color={rankColor}
            variant="filled"
            size="small"
            sx={{ fontWeight: 700, fontSize: '0.875rem' }}
          />
        </Box>

        {/* Title */}
        <Typography variant="h6" sx={{ fontWeight: 700, mb: 2.5 }}>
          {title}
        </Typography>

        {/* Why it matters section */}
        <Box sx={{ mb: 2 }}>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: 'block', fontWeight: 600, mb: 0.5 }}
          >
            Why it matters
          </Typography>
          <Typography variant="body2">
            {why_it_matters}
          </Typography>
        </Box>

        {/* How to fix section */}
        <Box sx={{ mb: 2 }}>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: 'block', fontWeight: 600, mb: 0.5 }}
          >
            How to fix
          </Typography>
          <Typography variant="body2">
            {how_to_fix}
          </Typography>
        </Box>

        {/* Drill section */}
        <Box sx={{ mb: 3 }}>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: 'block', fontWeight: 600, mb: 0.5 }}
          >
            Drill
          </Typography>
          <Typography variant="body2">
            {specific_drill}
          </Typography>
        </Box>

        {linkedGames.length > 0 && (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
            {linkedGames.map((gameId) => (
              <Button
                key={gameId}
                size="small"
                variant="text"
                onClick={() => scrollToGame(gameId)}
              >
                View {gameId}
              </Button>
            ))}
          </Box>
        )}

      </CardContent>
    </Card>
  );
};

export default PriorityCard;
