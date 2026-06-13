import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { CheckCircle } from 'lucide-react';
import {
  Box,
  Chip,
  Paper,
  Tooltip,
  Typography,
} from '@mui/material';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import { toTitleCase } from '../../utils/formatLabel';
import { buildSingleGameAnalysisLink } from '../../utils/singleGameAnalysisLinks';

const FixRateTailwindCard = ({ fixRate, batchId = null }) => {
  const persisting = (fixRate.patterns || []).filter(
    (row) => row.status === 'persisting'
  );
  const fixed = (fixRate.patterns || []).filter(
    (row) => row.status === 'fixed' || row.status === 'improved'
  );

  return (
    <section
      aria-label="Pattern fix rate"
      className="rounded-xl border border-green-200 bg-green-50/80 dark:bg-green-950/20 dark:border-green-900/60 p-4"
    >
      <div className="flex gap-2 items-start">
        <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400 shrink-0 mt-0.5" />
        <div className="min-w-0 flex-1">
          <p
            className="text-sm font-semibold text-gray-900 dark:text-gray-100"
            title={fixRate.tooltip || ''}
          >
            {fixRate.headline}
          </p>
          {fixed.length > 0 ? (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {fixed.map((row) => (
                <span
                  key={row.signature}
                  className="inline-flex rounded-full border border-green-300 dark:border-green-700 px-2 py-0.5 text-xs font-medium text-green-800 dark:text-green-200"
                >
                  {toTitleCase(row.label)}
                </span>
              ))}
            </div>
          ) : null}
          {persisting.length > 0 ? (
            <div className="mt-2">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Still needs work</p>
              <div className="flex flex-wrap gap-1.5">
                {persisting.map((row) => {
                  const href = row.proof_game_id
                    ? buildSingleGameAnalysisLink({
                        gameId: row.proof_game_id,
                        batchId,
                      })
                    : null;
                  const chipClass = 'inline-flex rounded-full border border-amber-300 dark:border-amber-700 px-2 py-0.5 text-xs font-medium text-amber-900 dark:text-amber-200';
                  if (href) {
                    return (
                      <RouterLink key={row.signature} to={href} className={`${chipClass} hover:opacity-90`}>
                        {toTitleCase(row.label)}
                      </RouterLink>
                    );
                  }
                  return (
                    <span key={row.signature} className={chipClass}>
                      {toTitleCase(row.label)}
                    </span>
                  );
                })}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
};

const FixRateCard = ({ fixRate, batchId = null, compact = false, variant = 'mui' }) => {
  if (!fixRate?.show) {
    return null;
  }

  if (variant === 'dashboard') {
    return <FixRateTailwindCard fixRate={fixRate} batchId={batchId} />;
  }

  const persisting = (fixRate.patterns || []).filter(
    (row) => row.status === 'persisting'
  );
  const fixed = (fixRate.patterns || []).filter(
    (row) => row.status === 'fixed' || row.status === 'improved'
  );

  return (
    <Paper
      variant="outlined"
      aria-label="Pattern fix rate"
      sx={{
        p: compact ? 1.5 : 2,
        mb: compact ? 0 : 2,
        borderColor: 'success.light',
        bgcolor: 'action.hover',
      }}
    >
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
        <CheckCircleOutlineIcon color="success" fontSize="small" sx={{ mt: 0.25 }} />
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Tooltip title={fixRate.tooltip || ''} placement="top">
            <Typography variant={compact ? 'body2' : 'subtitle1'} sx={{ fontWeight: 700 }}>
              {fixRate.headline}
            </Typography>
          </Tooltip>
          {fixed.length > 0 ? (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
              {fixed.map((row) => (
                <Chip
                  key={row.signature}
                  size="small"
                  color="success"
                  variant="outlined"
                  label={toTitleCase(row.label)}
                />
              ))}
            </Box>
          ) : null}
          {persisting.length > 0 ? (
            <Box sx={{ mt: 1 }}>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                Still needs work
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {persisting.map((row) => (
                  <Chip
                    key={row.signature}
                    size="small"
                    color="warning"
                    variant="outlined"
                    label={toTitleCase(row.label)}
                    component={row.proof_game_id ? RouterLink : 'div'}
                    to={
                      row.proof_game_id
                        ? buildSingleGameAnalysisLink({
                            gameId: row.proof_game_id,
                            batchId,
                          })
                        : undefined
                    }
                    clickable={Boolean(row.proof_game_id)}
                  />
                ))}
              </Box>
            </Box>
          ) : null}
        </Box>
      </Box>
    </Paper>
  );
};

export default FixRateCard;
