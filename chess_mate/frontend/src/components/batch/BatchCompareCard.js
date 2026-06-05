/**
 * BatchCompareCard — delta vs previous batch (weaknesses + headline metrics).
 */

import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Chip,
  Paper,
  Typography
} from '@mui/material';
import { fetchBatchCompare } from '../../services/apiRequests';

const formatDelta = (value, suffix = '') => {
  if (value == null || Number.isNaN(Number(value))) {
    return '—';
  }
  const num = Number(value);
  const sign = num > 0 ? '+' : '';
  return `${sign}${num.toFixed(1)}${suffix}`;
};

const BatchCompareCard = ({ batchId }) => {
  const [compare, setCompare] = useState(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const data = await fetchBatchCompare(batchId, 'previous');
        if (active) {
          setCompare(data);
          setMissing(false);
        }
      } catch (error) {
        if (!active) {
          return;
        }
        if (error?.status === 404 || error?.response?.status === 404) {
          setMissing(true);
        }
      }
    };

    if (batchId) {
      load();
    }

    return () => {
      active = false;
    };
  }, [batchId]);

  if (missing || !compare) {
    return null;
  }

  const { metrics = {}, weaknesses = {} } = compare;
  const accDelta = metrics.overall_accuracy_pct_delta;
  const stabDelta =
    metrics.overall_eval_stability_delta != null
      ? Number(metrics.overall_eval_stability_delta) * 100
      : null;

  return (
    <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
      <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 0.5 }}>
        vs previous batch (#{compare.other_batch_id})
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
        Accuracy {formatDelta(accDelta, '%')} · eval stability {formatDelta(stabDelta, '%')}
      </Typography>
      {compare.narrative && (
        <Typography variant="body2" sx={{ mb: 1.5 }}>
          {compare.narrative}
        </Typography>
      )}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {Array.isArray(weaknesses.persisting) && weaknesses.persisting.length > 0 && (
          <Alert severity="warning" icon={false} sx={{ py: 0.5 }}>
            <Typography variant="caption" sx={{ fontWeight: 600 }}>
              Still recurring
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
              {weaknesses.persisting.map((item) => (
                <Chip key={item} size="small" label={String(item).replace(/_/g, ' ')} />
              ))}
            </Box>
          </Alert>
        )}
        {Array.isArray(weaknesses.resolved) && weaknesses.resolved.length > 0 && (
          <Alert severity="success" icon={false} sx={{ py: 0.5 }}>
            <Typography variant="caption" sx={{ fontWeight: 600 }}>
              Improved
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
              {weaknesses.resolved.map((item) => (
                <Chip key={item} size="small" label={String(item).replace(/_/g, ' ')} color="success" />
              ))}
            </Box>
          </Alert>
        )}
        {Array.isArray(weaknesses.new) && weaknesses.new.length > 0 && (
          <Alert severity="info" icon={false} sx={{ py: 0.5 }}>
            <Typography variant="caption" sx={{ fontWeight: 600 }}>
              New patterns
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
              {weaknesses.new.map((item) => (
                <Chip key={item} size="small" label={String(item).replace(/_/g, ' ')} color="info" />
              ))}
            </Box>
          </Alert>
        )}
      </Box>
    </Paper>
  );
};

export default BatchCompareCard;
