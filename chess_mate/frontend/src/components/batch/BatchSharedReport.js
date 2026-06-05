/**
 * Public read-only batch report (share link, no login).
 */

import React, { useEffect, useState } from 'react';
import { useParams, Link as RouterLink } from 'react-router-dom';
import { Alert, Box, Container, Link, Typography } from '@mui/material';
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

  return (
    <Box sx={{ minHeight: '100vh', py: 4 }}>
      <Container maxWidth="lg">
        <Box className="batch-report-no-print" sx={{ mb: 2 }}>
          <Typography variant="overline" color="text.secondary">
            ChessMate · shared coaching report (read-only)
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Engine analysis + AI coaching narrative.{' '}
            <Link component={RouterLink} to="/login">
              Sign in
            </Link>{' '}
            to run your own batch.
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
