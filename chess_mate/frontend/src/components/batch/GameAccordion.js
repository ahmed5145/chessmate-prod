/**
 * GameAccordion.js — per-game breakdown from Stockfish analysis (critical moments, phases).
 */

import React, { useEffect, useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Box,
  Divider,
  Link,
  Button
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import FenBoardImage from './FenBoardImage';
import ReportSectionShell from './ReportSectionShell';
import { formatGameLabel, humanizeGameIdInText } from '../../utils/formatGameLabel';
import { BATCH_GAME_FOCUS_EVENT, getGamePlatformLabel } from '../../utils/batchGameLinks';
import { buildSingleGameAnalysisLink } from '../../utils/singleGameAnalysisLinks';
import { formatNumber } from '../../utils/formatNumber';
import { sanitizeReportFloats } from '../../utils/sanitizeReportText';

const HIGHLIGHT_MS = 2000;

const truncateOpening = (name, maxLength = 36) => {
  const text = String(name || '').trim();
  if (!text || text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength - 1)}…`;
};

const buildDefaultExpandedIds = (games = []) => {
  const ids = new Set();
  games.forEach((game, index) => {
    if (!game?.game_id) {
      return;
    }
    const criticalMoments = Array.isArray(game.critical_moments) ? game.critical_moments : [];
    if (index === 0 || criticalMoments.length > 0) {
      ids.add(game.game_id);
    }
  });
  return ids;
};

const GameAccordion = ({ per_game_results, readOnly = false, batchId = null }) => {
  const [expandedIds, setExpandedIds] = useState(() => buildDefaultExpandedIds(per_game_results));
  const [highlightedId, setHighlightedId] = useState(null);

  useEffect(() => {
    setExpandedIds(buildDefaultExpandedIds(per_game_results));
  }, [per_game_results]);

  useEffect(() => {
    let highlightTimer;

    const handleFocus = (event) => {
      const gameId = event?.detail?.gameId;
      if (!gameId) {
        return;
      }

      setExpandedIds((previous) => new Set([...previous, gameId]));
      setHighlightedId(gameId);

      if (highlightTimer) {
        window.clearTimeout(highlightTimer);
      }
      highlightTimer = window.setTimeout(() => {
        setHighlightedId((current) => (current === gameId ? null : current));
      }, HIGHLIGHT_MS);
    };

    window.addEventListener(BATCH_GAME_FOCUS_EVENT, handleFocus);
    return () => {
      window.removeEventListener(BATCH_GAME_FOCUS_EVENT, handleFocus);
      if (highlightTimer) {
        window.clearTimeout(highlightTimer);
      }
    };
  }, []);

  const games = useMemo(
    () => (Array.isArray(per_game_results) ? per_game_results : []),
    [per_game_results]
  );

  if (games.length === 0) {
    return (
      <ReportSectionShell title="Game-by-game breakdown">
        <Typography variant="body1">No game data available.</Typography>
      </ReportSectionShell>
    );
  }

  const getResultLabel = (result, playerColor) => {
    if (result === '1/2-1/2' || result === '*') return 'D';
    const playedWhite = playerColor === 'white';
    if (result === '1-0') return playedWhite ? 'W' : 'L';
    if (result === '0-1') return playedWhite ? 'L' : 'W';
    return 'D';
  };

  const getResultChipColor = (result, playerColor) => {
    const label = getResultLabel(result, playerColor);
    if (label === 'W') return 'success';
    if (label === 'L') return 'error';
    return 'default';
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

  const handleAccordionChange = (gameId) => (_, isExpanded) => {
    setExpandedIds((previous) => {
      const next = new Set(previous);
      if (isExpanded) {
        next.add(gameId);
      } else {
        next.delete(gameId);
      }
      return next;
    });
  };

  return (
    <ReportSectionShell
      title="Game-by-game breakdown"
      subtitle="Engine-derived stats and critical moments from each game in this batch."
    >
      {games.map((game, index) => {
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
        const gameAccuracy = game.accuracy;
        const openingLabel = game.opening_name
          && !['unknown', 'unknown opening'].includes(String(game.opening_name).toLowerCase())
          ? truncateOpening(game.opening_name)
          : null;
        const isHighlighted = highlightedId === game.game_id;

        return (
          <Accordion
            id={game.game_id ? `batch-game-${game.game_id}` : undefined}
            data-testid={game.game_id ? `batch-game-${game.game_id}` : undefined}
            key={game.game_id || index}
            expanded={game.game_id ? expandedIds.has(game.game_id) : false}
            onChange={game.game_id ? handleAccordionChange(game.game_id) : undefined}
            className={isHighlighted ? 'batch-game-highlight' : undefined}
            sx={{
              mb: 2,
              ...(isHighlighted
                ? {
                    border: '2px solid',
                    borderColor: 'primary.main',
                    boxShadow: '0 0 0 4px rgba(99, 102, 241, 0.18)',
                  }
                : {}),
            }}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  flexWrap: 'wrap',
                  width: '100%',
                  minWidth: 0,
                }}
              >
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                  {formatGameLabel(game)}
                </Typography>
                <Chip
                  label={getResultLabel(game.result, game.player_color)}
                  color={getResultChipColor(game.result, game.player_color)}
                  size="small"
                />
                {openingLabel ? (
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      maxWidth: { xs: 180, sm: 280 },
                    }}
                  >
                    {openingLabel}
                  </Typography>
                ) : null}
              </Box>
            </AccordionSummary>

            <AccordionDetails>
              <Box sx={{ display: 'grid', gap: 2 }}>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5, alignItems: 'center' }}>
                  {game.player_color ? (
                    <Typography variant="caption" color="text.secondary">
                      Played as {game.player_color}
                    </Typography>
                  ) : null}
                  {elo != null ? (
                    <Typography variant="caption" color="text.secondary">
                      {elo} elo
                    </Typography>
                  ) : null}
                  {gameAccuracy != null ? (
                    <Typography variant="caption" color="text.secondary">
                      {Number(gameAccuracy).toFixed(1)}% move match
                    </Typography>
                  ) : null}
                  <Typography variant="caption" color="text.secondary">
                    {game.total_moves || 0} moves · {moveQuality.blunder || 0} blunders
                  </Typography>
                  {!readOnly && game.saved_game_id ? (
                    <Link
                      component={RouterLink}
                      to={buildSingleGameAnalysisLink({
                        gameId: game.saved_game_id,
                        batchId,
                      })}
                      variant="caption"
                      sx={{ ml: { sm: 'auto' } }}
                    >
                      Deep review this game
                    </Link>
                  ) : null}
                </Box>

                <Box>
                  {game.platform_game_url ? (
                    <Button
                      size="small"
                      variant="outlined"
                      href={game.platform_game_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      endIcon={<OpenInNewIcon fontSize="small" />}
                    >
                      Open on {getGamePlatformLabel(per_game_results, game.game_id)}
                    </Button>
                  ) : (
                    <Typography variant="caption" color="text.secondary">
                      Original game link unavailable for this entry. Re-run the batch from
                      Chess.com/Lichess imports to attach platform URLs.
                    </Typography>
                  )}
                </Box>
                {game.coach_note ? (
                  <Box
                    sx={{
                      p: 1.5,
                      borderRadius: 1,
                      bgcolor: 'action.hover',
                      border: '1px solid',
                      borderColor: 'divider'
                    }}
                  >
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                      Coach note (worst moment)
                    </Typography>
                    <Typography variant="body2" sx={{ mt: 0.5 }}>
                      {humanizeGameIdInText(game.coach_note, per_game_results, {
                        inThisGameId: game.game_id,
                      })}
                    </Typography>
                  </Box>
                ) : null}
                {game.time_management?.has_clock_data ? (
                  <Typography variant="body2" color="text.secondary">
                    Clock: {game.time_management.avg_seconds_per_move}s avg per move
                    {game.time_management.rushed_critical_count
                      ? ` · ${game.time_management.rushed_critical_count} rushed critical move(s)`
                      : ''}
                  </Typography>
                ) : null}
                <Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                    Move quality
                  </Typography>
                  <Typography variant="body2">
                    {moveQuality.blunder || 0} blunders · {moveQuality.mistake || 0} mistakes ·{' '}
                    {moveQuality.inaccuracy || 0} inaccuracies · {moveQuality.good || 0} good moves
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 0.5 }}>
                    Engine line match (opening): {formatPercent(game.opening_accuracy)}
                  </Typography>
                </Box>

                <Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                    Phase accuracy
                  </Typography>
                  {['opening', 'middlegame', 'endgame'].map((phase) => {
                    const phaseData = phaseBreakdown[phase] || {};
                    const acc = phaseData.accuracy;
                    const label =
                      acc != null
                        ? `${Number(acc).toFixed(1)}%`
                        : formatPercent(getPhaseScore(phaseData.avg_eval_drop));
                    return (
                      <Typography key={phase} variant="body2">
                        {phase.charAt(0).toUpperCase() + phase.slice(1)}: {label}
                        {phaseData.moves != null ? ` (${phaseData.moves} moves)` : ''}
                      </Typography>
                    );
                  })}
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
                        {moment.fen ? (
                          <Box sx={{ mb: 1 }}>
                            <FenBoardImage
                              fen={moment.fen}
                              size={200}
                              orientation={game.player_color || 'white'}
                              playedMoveUci={moment.played_move_uci}
                              bestMoveUci={moment.best_move_uci}
                            />
                          </Box>
                        ) : null}
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
                          {moment.endgame_material && (
                            <Chip
                              size="small"
                              label={String(moment.endgame_material).replace(/_/g, ' ')}
                              color="info"
                              variant="outlined"
                            />
                          )}
                        </Box>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          You played {moment.played_move || '?'} · best for you {moment.best_move || '?'} · swing{' '}
                          {formatNumber(moment.eval_swing, 2)}
                        </Typography>
                        {moment.explanation && (
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                            {sanitizeReportFloats(moment.explanation)}
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
    </ReportSectionShell>
  );
};

export default GameAccordion;
