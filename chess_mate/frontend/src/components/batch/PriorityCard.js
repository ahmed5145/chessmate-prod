/**
 * PriorityCard.js — single top-3 priority with practice + game review drills.
 */

import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
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
  findGameResultById,
  formatGameLabelById,
  humanizeGameIdInText,
} from '../../utils/formatGameLabel';
import { buildSingleGameAnalysisLink } from '../../utils/singleGameAnalysisLinks';
import { buildPriorityDrillDisplay } from '../../utils/priorityDrillDisplay';
import { resolvePriorityLichessLink } from '../../utils/lichessStudyLinks';
import {
  getGamePlatformLabel,
  getGamePlatformUrl,
  scrollToBatchGame,
} from '../../utils/batchGameLinks';
import LichessActionButton from './LichessActionButton';
import { useTheme } from '../../context/ThemeContext';

const extractGameIds = (...parts) => {
  const text = parts.filter(Boolean).join(' ');
  const matches = text.match(/game_\d+/gi) || [];
  return [...new Set(matches.map((id) => id.toLowerCase()))];
};

const PriorityCard = ({
  priority,
  per_game_results = [],
  batch_summary = null,
  batchId = null,
  showLichessLink = true,
}) => {
  const { isDarkMode } = useTheme();

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
  const drillText = buildPriorityDrillDisplay(priority, per_game_results);
  const lichessLink = resolvePriorityLichessLink(priority, {
    batch_summary,
    per_game_results,
  });
  const deepReviewTarget = linkedGames
    .map((gameId) => {
      const gameRow = findGameResultById(per_game_results, gameId);
      return gameRow?.saved_game_id
        ? { gameId: gameRow.saved_game_id, labelGameId: gameId }
        : null;
    })
    .find(Boolean);

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

        {drillText ? (
          <Box sx={{ mb: 3 }}>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ display: 'block', fontWeight: 600, mb: 0.5 }}
            >
              Drill
            </Typography>
            <Typography variant="body2">{drillText}</Typography>
          </Box>
        ) : null}

        {((showLichessLink && lichessLink) || linkedGames.length > 0 || deepReviewTarget) && (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
            {deepReviewTarget && batchId ? (
              <Button
                size="small"
                variant="contained"
                component={RouterLink}
                to={buildSingleGameAnalysisLink({
                  gameId: deepReviewTarget.gameId,
                  batchId,
                  priority: rank,
                })}
                sx={{
                  textTransform: 'none',
                  fontWeight: 600,
                  bgcolor: isDarkMode ? '#4f46e5' : '#4f46e5',
                  color: '#ffffff',
                  boxShadow: 'none',
                  '&:hover': {
                    bgcolor: isDarkMode ? '#4338ca' : '#4338ca',
                    color: '#ffffff',
                  },
                }}
              >
                Deep review {formatGameLabelById(per_game_results, deepReviewTarget.labelGameId)}
              </Button>
            ) : null}
            {showLichessLink && lichessLink ? (
              <LichessActionButton
                label={lichessLink.label}
                url={lichessLink.url}
                kind={lichessLink.kind}
              />
            ) : null}
            {linkedGames.map((gameId) => {
              const platformUrl = getGamePlatformUrl(per_game_results, gameId);
              return (
                <Box key={gameId} sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  <Button
                    size="small"
                    variant="text"
                    onClick={() => scrollToBatchGame(gameId)}
                    sx={{ textTransform: 'none', fontWeight: 600 }}
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
                      sx={{ textTransform: 'none', fontWeight: 600 }}
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
