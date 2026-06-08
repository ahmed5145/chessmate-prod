/**
 * Public read-only batch report (share link, no login).
 */

import React, { useEffect, useState } from 'react';
import { useParams, Link as RouterLink } from 'react-router-dom';
import { Alert, Box, Button, Container, Paper, Typography } from '@mui/material';
import BatchReportSections from './BatchReportSections';
import { getPublicBatchReport } from '../../services/apiRequests';
import { buildRegisterHref, MARKETING_SOURCES } from '../../utils/marketingLinks';

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
    <Box
      className="batch-report-page"
      sx={{ minHeight: '100vh', py: 4, bgcolor: 'background.default', width: '100%', maxWidth: '100%', overflowX: 'clip' }}
    >
      <Container maxWidth="lg">
        <Paper
          className="batch-report-no-print"
          elevation={0}
          sx={(theme) => ({
            p: { xs: 2, sm: 2.5 },
            mb: 3,
            borderRadius: 2,
            border: '1px solid',
            borderColor: theme.palette.mode === 'dark' ? 'rgba(99, 102, 241, 0.35)' : 'rgba(99, 102, 241, 0.25)',
            background:
              theme.palette.mode === 'dark'
                ? 'linear-gradient(135deg, #1e1b4b 0%, #312e81 45%, #1f2937 100%)'
                : 'linear-gradient(135deg, #eef2ff 0%, #ffffff 55%, #f8fafc 100%)',
            color: theme.palette.mode === 'dark' ? 'grey.100' : 'grey.900',
          })}
        >
          <Typography
            variant="overline"
            sx={{
              color: (theme) =>
                theme.palette.mode === 'dark' ? 'indigo.200' : 'indigo.700',
              letterSpacing: 1.2,
            }}
          >
            ChessMate Batch Coach
          </Typography>
          <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5, mt: 0.5 }}>
            Personalized coaching from your real games
          </Typography>
          <Typography
            variant="body2"
            sx={{
              mb: 2,
              color: (theme) =>
                theme.palette.mode === 'dark' ? 'grey.300' : 'grey.700',
              maxWidth: 640,
            }}
          >
            This report combines Stockfish engine analysis with AI coaching across
            {gamesCount ? ` ${gamesCount} games` : ' a batch of games'} — recurring mistakes,
            opening gaps, and a training plan tied to actual positions.
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            <Button
              component={RouterLink}
              to={buildRegisterHref(MARKETING_SOURCES.SHARED_REPORT)}
              variant="contained"
              size="small"
              sx={{
                bgcolor: '#4f46e5',
                color: '#fff',
                fontWeight: 600,
                textTransform: 'none',
                '&:hover': { bgcolor: '#4338ca' },
              }}
            >
              Get your own batch report
            </Button>
            <Button
              component={RouterLink}
              to="/example/batch-report"
              variant="outlined"
              size="small"
              sx={(theme) => ({
                textTransform: 'none',
                fontWeight: 600,
                borderColor: theme.palette.mode === 'dark' ? 'grey.600' : 'grey.400',
                color: theme.palette.mode === 'dark' ? 'grey.200' : 'grey.800',
                '&:hover': {
                  borderColor: theme.palette.mode === 'dark' ? 'grey.500' : 'grey.600',
                  bgcolor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
                },
              })}
            >
              See example report
            </Button>
            <Button
              component={RouterLink}
              to="/how-batch-coach-works"
              variant="outlined"
              size="small"
              sx={(theme) => ({
                textTransform: 'none',
                fontWeight: 600,
                borderColor: theme.palette.mode === 'dark' ? 'indigo.300' : 'indigo.400',
                color: theme.palette.mode === 'dark' ? 'indigo.100' : 'indigo.800',
                '&:hover': {
                  borderColor: theme.palette.mode === 'dark' ? 'indigo.200' : 'indigo.600',
                  bgcolor:
                    theme.palette.mode === 'dark'
                      ? 'rgba(99, 102, 241, 0.15)'
                      : 'rgba(99, 102, 241, 0.08)',
                },
              })}
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
