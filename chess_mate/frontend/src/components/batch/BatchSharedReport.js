/**
 * Public read-only batch report (share link, no login).
 */

import React, { useEffect, useState } from 'react';
import { useParams, Link as RouterLink } from 'react-router-dom';
import { Alert, Box, Button, Container, Paper, Typography } from '@mui/material';
import BatchReportSections from './BatchReportSections';
import { getPublicBatchReport } from '../../services/apiRequests';

const BatchSharedReport = () => {
  const { shareToken } = useParams();
  const [batchReport, setBatchReport] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const report = await getPublicBatchReport(shareToken);
        if (active) {
          setBatchReport(report);
          setError(null);
        }
      } catch (loadError) {
        if (active) {
          setError(loadError?.detail || loadError?.message || 'Shared report not found.');
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    if (shareToken) {
      load();
    } else {
      setError('Invalid share link.');
      setLoading(false);
    }

    return () => {
      active = false;
    };
  }, [shareToken]);

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 6 }}>
        <Typography>Loading shared report…</Typography>
      </Container>
    );
  }

  const gamesCount = batchReport?.games_count || batchReport?.batch_summary?.games_analyzed;

  return (
    <Box sx={{ minHeight: '100vh', py: 4, bgcolor: 'background.default' }}>
      <Container maxWidth="lg">
        <Paper
          className="batch-report-no-print"
          elevation={0}
          sx={(theme) => ({
            p: 2.5,
            mb: 3,
            border: '1px solid',
            borderColor: theme.palette.mode === 'dark' ? 'grey.700' : 'divider',
            bgcolor: theme.palette.mode === 'dark' ? 'grey.900' : 'background.paper',
            color: 'text.primary',
            borderRadius: 2,
          })}
        >
          <Typography variant="overline" sx={{ opacity: 0.9 }}>
            ChessMate Batch Coach
          </Typography>
          <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>
            Personalized coaching from your real games
          </Typography>
          <Typography variant="body2" sx={{ mb: 2, opacity: 0.95 }}>
            This report combines Stockfish engine analysis with AI coaching across
            {gamesCount ? ` ${gamesCount} games` : ' a batch of games'} — recurring mistakes,
            opening gaps, and a training plan tied to actual positions.
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            <Button
              component={RouterLink}
              to="/login"
              variant="contained"
              color="secondary"
              size="small"
            >
              Get your own batch report
            </Button>
            <Button
              component={RouterLink}
              to="/batch-analysis"
              variant="outlined"
              size="small"
              sx={{ borderColor: 'primary.contrastText', color: 'primary.contrastText' }}
            >
              See how it works
            </Button>
          </Box>
        </Paper>

        <Box className="batch-report-no-print" sx={{ mb: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Shared coaching report (read-only) · engine depth 14
          </Typography>
        </Box>

        {error ? (
          <Alert severity="error">{error}</Alert>
        ) : (
          <BatchReportSections
            batchReport={batchReport}
            status={batchReport?.status || 'completed'}
            readOnly
          />
        )}
      </Container>
    </Box>
  );
};

export default BatchSharedReport;
