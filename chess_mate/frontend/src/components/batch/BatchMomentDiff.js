/**
 * BatchMomentDiff — pattern swing trends vs previous batch (SRG-20).
 */

import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import { Sparkline } from '../shared/MomentTimelineStrip';
import { formatNumber } from '../../utils/formatNumber';
import { toTitleCase } from '../../utils/formatLabel';
import { buildSingleGameAnalysisLink } from '../../utils/singleGameAnalysisLinks';

const statusChip = (status) => {
  if (status === 'resolved') {
    return { label: 'Resolved', color: 'success' };
  }
  if (status === 'new') {
    return { label: 'New', color: 'info' };
  }
  return { label: 'Unchanged', color: 'warning' };
};

const formatSwing = (value) => {
  if (value == null || Number.isNaN(Number(value))) {
    return '—';
  }
  return formatNumber(value, 2);
};

const BatchMomentDiff = ({ momentDiff, batchId = null }) => {
  if (!momentDiff?.show || !Array.isArray(momentDiff.rows) || momentDiff.rows.length === 0) {
    return null;
  }

  const counts = momentDiff.counts || {};
  const summaryParts = [
    counts.resolved ? `${counts.resolved} resolved` : null,
    counts.unchanged ? `${counts.unchanged} unchanged` : null,
    counts.new ? `${counts.new} new` : null,
  ].filter(Boolean);

  return (
    <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start', mb: 1.5 }}>
        <CompareArrowsIcon color="primary" fontSize="small" sx={{ mt: 0.25 }} />
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            {momentDiff.title || 'Compared to last batch'}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            vs batch #{momentDiff.previous_batch_id}
            {momentDiff.previous_batch_month ? ` (${momentDiff.previous_batch_month})` : ''}
            {summaryParts.length ? ` · ${summaryParts.join(' · ')}` : ''}
          </Typography>
        </Box>
      </Box>

      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Pattern</TableCell>
            <TableCell align="right">Then</TableCell>
            <TableCell align="right">Now</TableCell>
            <TableCell align="center">Trend</TableCell>
            <TableCell>Status</TableCell>
            <TableCell align="right">Proof</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {momentDiff.rows.map((row) => {
            const chip = statusChip(row.status);
            return (
              <TableRow key={row.signature}>
                <TableCell sx={{ fontWeight: 600 }}>
                  {toTitleCase(row.label)}
                </TableCell>
                <TableCell align="right">{formatSwing(row.previous_swing)}</TableCell>
                <TableCell align="right">{formatSwing(row.current_swing)}</TableCell>
                <TableCell align="center">
                  <Box
                    sx={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'text.secondary',
                      minWidth: 80,
                    }}
                  >
                    <Sparkline values={row.sparkline} />
                  </Box>
                </TableCell>
                <TableCell>
                  <Chip size="small" label={chip.label} color={chip.color} variant="outlined" />
                </TableCell>
                <TableCell align="right">
                  {row.proof_game_id ? (
                    <Button
                      size="small"
                      component={RouterLink}
                      to={buildSingleGameAnalysisLink({
                        gameId: row.proof_game_id,
                        batchId,
                      })}
                      sx={{ textTransform: 'none', fontWeight: 600 }}
                    >
                      Review game
                    </Button>
                  ) : (
                    <Typography variant="caption" color="text.secondary">
                      —
                    </Typography>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </Paper>
  );
};

export default BatchMomentDiff;
