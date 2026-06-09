import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
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

const statusColor = (status) => {
  if (status === 'fixed' || status === 'improved') return 'success';
  if (status === 'persisting') return 'warning';
  return 'default';
};

const FixRateCard = ({ fixRate, batchId = null, compact = false }) => {
  if (!fixRate?.show) {
    return null;
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
