/**
 * Above-the-fold report hero: games, date, takeaway, do-today, CTA to priorities.
 */

import React from 'react';
import {
  Box,
  Button,
  Chip,
  Paper,
  Typography,
} from '@mui/material';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import {
  extractExecutiveTakeaway,
  hasCoachingPriorities,
} from '../../utils/batchReportText';
import { humanizeGameIdInText } from '../../utils/formatGameLabel';
import { scrollToBatchSection } from '../../utils/batchReportScroll';

const BatchReportHero = ({
  batch_summary,
  games_count,
  coaching_report,
  per_game_results = [],
  status = 'completed',
  marketingMode = false,
}) => {
  const analyzed = batch_summary?.games_analyzed ?? games_count ?? 0;
  const dateRange = batch_summary?.date_range;
  const takeaway = extractExecutiveTakeaway(coaching_report);
  const showPriorityCta = hasCoachingPriorities(coaching_report);
  const isPartial = status === 'partial';
  const doToday = coaching_report?.one_thing_to_do_today?.trim();

  return (
    <Box sx={{ py: 0, pb: 1 }}>
      <Paper
        elevation={0}
        sx={(theme) => ({
          p: { xs: 2, sm: 2.5 },
          borderRadius: 2,
          border: '1px solid',
          borderColor: theme.palette.mode === 'dark' ? 'rgba(99, 102, 241, 0.35)' : 'rgba(99, 102, 241, 0.25)',
          background:
            theme.palette.mode === 'dark'
              ? 'linear-gradient(135deg, #1e1b4b 0%, #312e81 40%, #1f2937 100%)'
              : 'linear-gradient(135deg, #eef2ff 0%, #ffffff 55%, #f8fafc 100%)',
        })}
      >
        <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1, mb: 1 }}>
          <CheckCircleOutlineIcon color="primary" fontSize="small" />
          <Typography variant="overline" sx={{ fontWeight: 700, letterSpacing: '0.06em' }}>
            {marketingMode ? 'Example Batch Coach report' : 'Your Batch Coach report is ready'}
          </Typography>
          {isPartial ? (
            <Chip size="small" label="Partial batch" color="warning" variant="outlined" />
          ) : null}
        </Box>

        <Typography variant="h5" sx={{ fontWeight: 800, mb: 0.5, lineHeight: 1.25 }}>
          {analyzed} game{analyzed === 1 ? '' : 's'} analyzed
          {dateRange ? ` · ${dateRange}` : ''}
        </Typography>

        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ mb: 1.5, lineHeight: 1.55, maxWidth: 720 }}
        >
          Personalized coaching from your real games — Stockfish engine stats plus AI guidance on
          recurring mistakes, opening gaps, and a training plan tied to actual positions.
        </Typography>

        {doToday ? (
          <Paper
            variant="outlined"
            sx={{
              p: 1.5,
              mb: 2,
              bgcolor: 'rgba(99, 102, 241, 0.08)',
              borderColor: 'rgba(99, 102, 241, 0.35)',
            }}
          >
            <Typography
              variant="caption"
              sx={{ fontWeight: 700, color: 'primary.main', display: 'block', mb: 0.5 }}
            >
              Do today
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.55, wordBreak: 'break-word' }}>
              {humanizeGameIdInText(doToday, per_game_results)}
            </Typography>
          </Paper>
        ) : null}

        {takeaway ? (
          <Typography variant="body1" color="text.secondary" sx={{ mb: 2, lineHeight: 1.6, maxWidth: 720 }}>
            {takeaway}
          </Typography>
        ) : (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Review your priorities and phase scores below, then drill into individual games.
          </Typography>
        )}

        {showPriorityCta && !marketingMode ? (
          <Button
            variant="contained"
            size="small"
            endIcon={<ArrowDownwardIcon />}
            onClick={() => scrollToBatchSection('batch-section-priorities')}
            sx={{ textTransform: 'none', fontWeight: 700 }}
          >
            Start with priority #1
          </Button>
        ) : !marketingMode ? (
          <Button
            variant="outlined"
            size="small"
            endIcon={<ArrowDownwardIcon />}
            onClick={() => scrollToBatchSection('batch-section-phases')}
            sx={{ textTransform: 'none', fontWeight: 600 }}
          >
            View phase breakdown
          </Button>
        ) : null}
      </Paper>
    </Box>
  );
};

export default BatchReportHero;
