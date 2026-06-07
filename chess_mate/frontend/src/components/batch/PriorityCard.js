/**
 * PriorityCard.js — single top-3 priority with practice + game review drills.
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
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import {
  formatGameLabelById,
  humanizeGameIdInText,
} from '../../utils/formatGameLabel';
import { buildPriorityDrillDisplay } from '../../utils/priorityDrillDisplay';
import {
  getGamePlatformLabel,
  getGamePlatformUrl,
  scrollToBatchGame,
} from '../../utils/batchGameLinks';

const extractGameIds = (...parts) => {
  const text = parts.filter(Boolean).join(' ');
  const matches = text.match(/game_\d+/gi) || [];
  return [...new Set(matches.map((id) => id.toLowerCase()))];
};

const PriorityCard = ({ priority, per_game_results = [] }) => {
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

  const getRankColor = (rankNum) => {
    if (rankNum === 1) return 'error';
    if (rankNum === 2) return 'warning';
    if (rankNum === 3) return 'info';
    return 'default';
  };

  const rankColor = getRankColor(rank);
  const linkedGames = extractGameIds(title, why_it_matters, how_to_fix, specific_drill);
  const humanize = (text) => humanizeGameIdInText(text, per_game_results);
  const drillDisplay = buildPriorityDrillDisplay(priority, per_game_results);

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Box sx={{ mb: 2 }}>
          <Chip
            label={rank}
            color={rankColor}
            variant="filled"
            size="small"
            sx={{ fontWeight: 700, fontSize: '0.875rem' }}
          />
        </Box>

        <Typography variant="h6" sx={{ fontWeight: 700, mb: 2.5 }}>
          {humanize(title)}
        </Typography>

        <Box sx={{ mb: 2 }}>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: 'block', fontWeight: 600, mb: 0.5 }}
          >
            Why it matters
          </Typography>
          <Typography variant="body2">
            {humanize(why_it_matters)}
          </Typography>
        </Box>

        <Box sx={{ mb: 2 }}>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: 'block', fontWeight: 600, mb: 0.5 }}
          >
            How to fix
          </Typography>
          <Typography variant="body2">
            {humanize(how_to_fix)}
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: 'block', fontWeight: 600, mb: 0.5 }}
          >
            Drill
          </Typography>
          {drillDisplay.practice ? (
            <Box sx={{ mb: 1.5 }}>
              <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 0.25 }}>
                Practice
              </Typography>
              <Typography variant="body2">{drillDisplay.practice}</Typography>
            </Box>
          ) : null}
          {drillDisplay.review ? (
            <Box>
              <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 0.25 }}>
                Review in your games
              </Typography>
              <Typography variant="body2">{drillDisplay.review}</Typography>
            </Box>
          ) : null}
        </Box>

        {linkedGames.length > 0 && (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
            {linkedGames.map((gameId) => {
              const platformUrl = getGamePlatformUrl(per_game_results, gameId);
              return (
                <Box key={gameId} sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  <Button
                    size="small"
                    variant="text"
                    onClick={() => scrollToBatchGame(gameId)}
                  >
                    View {formatGameLabelById(per_game_results, gameId)}
                  </Button>
                  {platformUrl ? (
                    <Button
                      size="small"
                      variant="outlined"
                      href={platformUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      endIcon={<OpenInNewIcon fontSize="small" />}
                    >
                      Open on {getGamePlatformLabel(per_game_results, gameId)}
                    </Button>
                  ) : null}
                </Box>
              );
            })}
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default PriorityCard;
