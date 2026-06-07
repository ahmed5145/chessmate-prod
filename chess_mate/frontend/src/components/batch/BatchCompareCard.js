/**
 * BatchCompareCard — delta vs previous batch (weaknesses + headline metrics).
 */

import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Chip,
  Container,
  Paper,
  Typography,
} from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import { fetchBatchCompare } from '../../services/apiRequests';
import { toTitleCase } from '../../utils/formatLabel';

const CompareEmptyState = () => (
  <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: 'action.hover' }}>
    <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
      <TrendingUpIcon color="action" fontSize="small" sx={{ mt: 0.25 }} />
      <Box>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
          Track progress over time
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Run another batch later to see which weaknesses improved, persisted, or appeared new
          compared to your last report.
        </Typography>
      </Box>
    </Box>
  </Paper>
);

const BatchCompareCard = ({ batchId }) => {
  const [compare, setCompare] = useState(null);
  const [missing, setMissing] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    const load = async () => {
      setLoading(true);
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
        setCompare(null);
        if (error?.status === 404 || error?.response?.status === 404) {
          setMissing(true);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    if (batchId) {
      load();
    } else {
      setLoading(false);
      setMissing(true);
    }

    return () => {
      active = false;
    };
  }, [batchId]);

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 0 }}>
        <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Loading comparison with your previous batch…
          </Typography>
        </Paper>
      </Container>
    );
  }

  if (missing || !compare) {
    return (
      <Container maxWidth="lg" sx={{ py: 0 }}>
        <CompareEmptyState />
      </Container>
    );
  }

  const { weaknesses = {} } = compare;
  const narrative = compare.narrative || '';
  const narrativeLower = narrative.toLowerCase();
  const persisting = (weaknesses.persisting || []).filter(
    (item) => !narrativeLower.includes(String(item).replace(/_/g, ' ').toLowerCase())
  );

  return (
    <Container maxWidth="lg" sx={{ py: 0 }}>
      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 0.5 }}>
          vs previous batch (#{compare.other_batch_id})
        </Typography>
        {narrative ? (
          <Typography variant="body2" sx={{ mb: 1.5 }}>
            {narrative}
          </Typography>
        ) : null}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {persisting.length > 0 && (
            <Alert severity="warning" icon={false} sx={{ py: 0.5 }}>
              <Typography variant="caption" sx={{ fontWeight: 600 }}>
                Still recurring
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                {persisting.map((item) => (
                  <Chip key={item} size="small" label={toTitleCase(item)} />
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
                  <Chip key={item} size="small" label={toTitleCase(item)} color="success" />
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
                  <Chip key={item} size="small" label={toTitleCase(item)} color="info" />
                ))}
              </Box>
            </Alert>
          )}
        </Box>
      </Paper>
    </Container>
  );
};

export default BatchCompareCard;
