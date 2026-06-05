/**
 * BatchReport.js
 *
 * Page that polls batch status, loads the final report, and renders the
 * analysis sections in the approved order.
 *
 * Route params:
 *   - batchId: string
 *
 * State:
 *   - batchReport: object | null
 *   - status: string
 *   - progress: string
 *   - completedGames: number
 *   - totalGames: number
 *   - error: string | null
 *
 * Pure page component with polling side effects only.
 */

import React, { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import {
  Alert,
  Box,
  Button,
  Container,
  Stack,
  Typography
} from '@mui/material';
import BatchLoadingScreen from './BatchLoadingScreen';
import BatchReportHeader from './BatchReportHeader';
import ExecutiveSummary from './ExecutiveSummary';
import PhaseBreakdown from './PhaseBreakdown';
import RecurringPatterns from './RecurringPatterns';
import CoachingNarrative from './CoachingNarrative';
import TopPriorities from './TopPriorities';
import TrainingPlan from './TrainingPlan';
import GameAccordion from './GameAccordion';
import { getBatchStatus, getBatchReport, regenerateBatchCoaching } from '../../services/apiRequests';

const BatchReport = () => {
  const { batchId } = useParams();
  const [batchReport, setBatchReport] = useState(null);
  const [status, setStatus] = useState('pending');
  const [progress, setProgress] = useState('');
  const [completedGames, setCompletedGames] = useState(0);
  const [totalGames, setTotalGames] = useState(0);
  const [error, setError] = useState(null);
  const [failedReport, setFailedReport] = useState(null);
  const [regenerating, setRegenerating] = useState(false);
  const intervalRef = useRef(null);
  const loadingReportRef = useRef(false);
  const finishedRef = useRef(false);
  const pollingErrorCountRef = useRef(0);

  useEffect(() => {
    let isMounted = true;

    const clearPolling = () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };

    const loadBatchReport = async () => {
      if (loadingReportRef.current || finishedRef.current) {
        return;
      }

      loadingReportRef.current = true;
      clearPolling();

      try {
        const report = await getBatchReport(batchId);
        if (!isMounted) {
          return;
        }
        if (report?.status === 'failed') {
          setFailedReport(report);
          setBatchReport(null);
        } else {
          setFailedReport(null);
          setBatchReport(report);
        }
      } catch (reportError) {
        if (!isMounted) {
          return;
        }
        const message = reportError?.message || reportError?.detail || 'Failed to load batch report.';
        setError(message);
      } finally {
        loadingReportRef.current = false;
        finishedRef.current = true;
      }
    };

    const pollStatus = async () => {
      if (!batchId || finishedRef.current) {
        return;
      }

      try {
        const response = await getBatchStatus(batchId);
        if (!isMounted) {
          return;
        }

        pollingErrorCountRef.current = 0;
        setStatus(response?.status || 'failed');
        setProgress(response?.progress || '');
        setCompletedGames(Number(response?.completed_games) || 0);
        setTotalGames(Number(response?.games_count) || 0);

        if (['completed', 'partial', 'failed'].includes(response?.status)) {
          await loadBatchReport();
        }
      } catch (pollError) {
        if (!isMounted) {
          return;
        }

        pollingErrorCountRef.current += 1;
        if (pollingErrorCountRef.current >= 3) {
          clearPolling();
          finishedRef.current = true;
          setError('Unable to reach server. Please refresh the page.');
        }
      }
    };

    if (!batchId) {
      setError('Missing batch ID.');
      return () => {
        isMounted = false;
        clearPolling();
      };
    }

    pollStatus();
    intervalRef.current = setInterval(pollStatus, 3000);

    return () => {
      isMounted = false;
      clearPolling();
    };
  }, [batchId]);

  const showReport = batchReport && ['completed', 'partial'].includes(status);
  const canRegenerate =
    showReport &&
    Array.isArray(batchReport?.per_game_results) &&
    batchReport.per_game_results.length >= 5;

  const handleRegenerateCoaching = async () => {
    if (!canRegenerate || regenerating) {
      return;
    }

    const confirmed = window.confirm(
      'Regenerate the coaching report from your saved game analysis? Stockfish will not re-run (about 10–30 seconds).'
    );
    if (!confirmed) {
      return;
    }

    setRegenerating(true);
    try {
      const updated = await regenerateBatchCoaching(batchId);
      setBatchReport(updated);
      setStatus(updated?.status || status);
      toast.success('Coaching report updated.');
    } catch (regenError) {
      const message =
        regenError?.detail || regenError?.message || 'Could not regenerate coaching. Try again later.';
      toast.error(message);
    } finally {
      setRegenerating(false);
    }
  };

  return (
    <Box sx={{ minHeight: '100vh' }}>
      <BatchLoadingScreen
        status={status}
        progress={progress}
        completed_games={completedGames}
        total_games={totalGames}
      />

      <Container maxWidth="lg" sx={{ py: 4 }}>
        {error ? (
          <Alert severity="error" sx={{ mb: 3, width: '100%' }}>
            {error}
          </Alert>
        ) : null}

        {status === 'failed' ? (
          <Alert severity="error" sx={{ mb: 3, width: '100%' }}>
            {failedReport?.message ||
              'Analysis failed — insufficient games succeeded. Please try again with at least 5 games.'}
            {failedReport?.credits_refunded && failedReport?.credits_refunded_amount ? (
              <>
                {' '}
                Your account was refunded {failedReport.credits_refunded_amount} credit
                {failedReport.credits_refunded_amount === 1 ? '' : 's'} for this batch.
              </>
            ) : failedReport?.credits_refunded ? (
              <> Your credits for this batch were refunded.</>
            ) : null}
          </Alert>
        ) : null}

        {showReport ? (
          <Box sx={{ display: 'grid', gap: 2 }}>
            <Stack
              direction={{ xs: 'column', sm: 'row' }}
              alignItems={{ xs: 'stretch', sm: 'center' }}
              justifyContent="space-between"
              spacing={1}
              sx={{ px: { xs: 0, sm: 1 } }}
            >
              <Typography variant="body2" color="text.secondary">
                {batchReport.coaching_report
                  ? 'Coaching is AI-generated from your engine analysis.'
                  : 'Coaching unavailable — regenerate to try again.'}
              </Typography>
              {canRegenerate ? (
                <Button
                  variant="outlined"
                  size="small"
                  disabled={regenerating}
                  onClick={handleRegenerateCoaching}
                >
                  {regenerating ? 'Regenerating…' : 'Regenerate coaching'}
                </Button>
              ) : null}
            </Stack>
            <BatchReportHeader
              batch_summary={batchReport.batch_summary}
              games_count={batchReport.games_count}
            />
            <ExecutiveSummary coaching_report={batchReport.coaching_report} />
            <PhaseBreakdown batch_summary={batchReport.batch_summary} />
            <RecurringPatterns batch_summary={batchReport.batch_summary} />
            <CoachingNarrative coaching_report={batchReport.coaching_report} />
            <TopPriorities coaching_report={batchReport.coaching_report} />
            <TrainingPlan coaching_report={batchReport.coaching_report} />
            <GameAccordion per_game_results={batchReport.per_game_results} />
          </Box>
        ) : null}
      </Container>
    </Box>
  );
};

export default BatchReport;
