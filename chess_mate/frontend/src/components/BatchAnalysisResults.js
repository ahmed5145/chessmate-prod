import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { useTheme } from '../context/ThemeContext';
import { getBatchReport, getBatchStatus, retryFailedGames } from '../services/apiRequests';
import FailedGamesList, { normalizeFailedGames } from './batch/FailedGamesList';
import {
  Box,
  Typography,
  CircularProgress,
  Button,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Tabs,
  Tab,
  Grid,
  Card,
  CardContent,
  Divider,
  List,
  ListItem,
  ListItemText,
  LinearProgress,
  Container
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip as ChartJSTooltip,
  Legend,
  ArcElement,
  RadialLinearScale
} from 'chart.js';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  ChartJSTooltip,
  Legend,
  ArcElement,
  RadialLinearScale
);

const formatFrequency = (frequency) => {
  if (frequency === null || frequency === undefined || frequency === '') {
    return '';
  }
  return typeof frequency === 'string' ? frequency : String(frequency);
};

const normalizeBatchReport = (report) => {
  const batchSummary = report?.batch_summary || {};
  const coachingReport = report?.coaching_report || {};
  const perGameResults = Array.isArray(report?.per_game_results) ? report.per_game_results : [];
  const phasePerformance = batchSummary.phase_performance || {};
  const recurringWeaknesses = Array.isArray(batchSummary.recurring_weaknesses) ? batchSummary.recurring_weaknesses : [];
  const strengthPatterns = Array.isArray(batchSummary.strength_patterns) ? batchSummary.strength_patterns : [];
  const topPriorities = Array.isArray(coachingReport.top_3_priorities) ? coachingReport.top_3_priorities : [];

  const totals = perGameResults.reduce(
    (accumulator, result) => {
      const moveQuality = result?.move_quality || {};
      accumulator.blunders += Number(moveQuality.blunder || 0);
      accumulator.mistakes += Number(moveQuality.mistake || 0);
      accumulator.inaccuracies += Number(moveQuality.inaccuracy || 0);
      accumulator.totalMoves += Number(result?.total_moves || 0);
      return accumulator;
    },
    { blunders: 0, mistakes: 0, inaccuracies: 0, totalMoves: 0 }
  );

  const openingCounts = perGameResults.reduce((accumulator, result) => {
    const openingName = result?.opening_name || 'Unknown';
    if (openingName && openingName !== 'Unknown') {
      accumulator[openingName] = (accumulator[openingName] || 0) + 1;
    }
    return accumulator;
  }, {});

  const criticalMoments = perGameResults.flatMap((result) =>
    (Array.isArray(result?.critical_moments) ? result.critical_moments : []).map((moment) => ({
      ...moment,
      game_id: result?.game_id,
    }))
  );

  const openingScore = Number(phasePerformance.opening?.score || 0);
  const middlegameScore = Number(phasePerformance.middlegame?.score || 0);
  const endgameScore = Number(phasePerformance.endgame?.score || 0);
  const overallAccuracy = Number(batchSummary.overall_accuracy || 0) * 100;
  const accuracyGap = Math.max(0, (openingScore - Math.min(middlegameScore, endgameScore)) * 100);
  const confidence = perGameResults.length >= 10 ? 'high' : 'medium';

  const legacyCoachReport = {
    summary: coachingReport.executive_summary || 'No summary available.',
    coach_summary: coachingReport.executive_summary || 'No summary available.',
    opening: {
      analysis: coachingReport.coaching_narrative?.opening || '',
    },
    middlegame: {
      analysis: coachingReport.coaching_narrative?.middlegame || '',
    },
    endgame: {
      analysis: coachingReport.coaching_narrative?.endgame || '',
    },
    strengths: strengthPatterns.map((item) => item.pattern || item.detail || String(item)),
    weaknesses: recurringWeaknesses.map((item) => item.pattern || String(item)),
    top_strengths: strengthPatterns.map((item) => {
      const label = item.pattern || item.detail || String(item);
      const frequency = formatFrequency(item.frequency);
      return frequency ? `${label} (${frequency})` : label;
    }),
    top_weaknesses: recurringWeaknesses.map((item) => {
      const label = item.pattern || String(item);
      const frequency = formatFrequency(item.frequency);
      return frequency ? `${label} (${frequency})` : label;
    }),
    improvement_areas: topPriorities.map((item) => item.title || item.specific_drill || 'Improvement area'),
    action_plan: [
      coachingReport.training_plan?.week_1,
      coachingReport.training_plan?.week_2,
      coachingReport.training_plan?.week_3,
      coachingReport.training_plan?.week_4,
      coachingReport.one_thing_to_do_today,
    ].filter(Boolean),
    openings_seen: Array.isArray(phasePerformance.opening?.primary_openings) ? phasePerformance.opening.primary_openings : [],
    critical_moments: criticalMoments,
    training_block: {
      focus_areas: topPriorities.map((item) => item.title || 'Focus area'),
      weekly_target: {
        goal: coachingReport.one_thing_to_do_today || topPriorities[0]?.title || 'Work on your biggest weakness',
        measure: topPriorities[0]?.estimated_study_hours ? `${topPriorities[0].estimated_study_hours} hours` : '4 hours',
        confidence,
      },
      drills: topPriorities.map((item) => item.specific_drill).filter(Boolean),
      checklist: [
        coachingReport.training_plan?.week_1,
        coachingReport.training_plan?.week_2,
        coachingReport.training_plan?.week_3,
        coachingReport.training_plan?.week_4,
      ].filter(Boolean),
    },
    phase_motifs: {
      weakest_phase: batchSummary.worst_phase || '',
      correction_rule: topPriorities[0]?.how_to_fix || '',
      motifs: recurringWeaknesses.map((item) => ({
        name: item.pattern || 'Pattern',
        count: item.frequency || 0,
        correction_rule: item.impact || item.detail || '',
        evidence: item.example_game_ids || [],
      })),
    },
    impact_metrics: {
      critical_error_rate: perGameResults.length > 0 ? Number(((totals.blunders + totals.mistakes) / perGameResults.length).toFixed(2)) : 0,
      phase_risk_index: Number((100 - Math.min(openingScore, middlegameScore, endgameScore) * 100).toFixed(1)),
      accuracy_gap: Number(accuracyGap.toFixed(1)),
      phase_risk: {
        opening: Number((100 - openingScore * 100).toFixed(1)),
        middlegame: Number((100 - middlegameScore * 100).toFixed(1)),
        endgame: Number((100 - endgameScore * 100).toFixed(1)),
      },
    },
    performance_tier: batchSummary.estimated_elo_range || 'unknown',
    confidence,
    sample_size_note: `Analyzed ${perGameResults.length} games across the batch.`,
    key_takeaway: coachingReport.executive_summary || 'No key takeaway available.',
  };

  return {
    overall: {
      accuracy: overallAccuracy,
      blunders: totals.blunders,
      mistakes: totals.mistakes,
      inaccuracies: totals.inaccuracies,
      total_moves: totals.totalMoves,
    },
    opening: {
      accuracy: openingScore * 100,
      opportunities: 0,
      best_moves: 0,
      critical_best_moves: 0,
      repertoire: openingCounts,
    },
    middlegame: {
      accuracy: middlegameScore * 100,
      opportunities: 0,
      best_moves: 0,
      critical_best_moves: 0,
    },
    endgame: {
      accuracy: endgameScore * 100,
      opportunities: 0,
      best_moves: 0,
      critical_best_moves: 0,
    },
    phase_motifs: {
      weakest_phase: batchSummary.worst_phase || '',
      correction_rule: topPriorities[0]?.how_to_fix || '',
      motifs: recurringWeaknesses.map((item) => ({
        name: item.pattern || 'Pattern',
        count: item.frequency || 0,
        correction_rule: item.impact || item.detail || '',
        evidence: item.example_game_ids || [],
      })),
    },
    time_management: batchSummary.time_management || null,
    coach_report: legacyCoachReport,
    ai_feedback: legacyCoachReport,
  };
};

const applyBatchReport = (setResults, setFailedGames, setAggregateMetrics, report) => {
  const perGameResults = Array.isArray(report?.per_game_results) ? report.per_game_results : [];
  setResults(perGameResults);
  const failures = normalizeFailedGames(
    Array.isArray(report?.errors) && report.errors.length > 0 ? report.errors : report?.failed_games
  );
  setFailedGames((prev) => (failures.length > 0 ? failures : prev));
  setAggregateMetrics(normalizeBatchReport(report));
};

const BatchAnalysisResults = () => {
  const { taskId, reportId } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('PROGRESS');
  const [isLoadingReport, setIsLoadingReport] = useState(false);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('Initializing analysis...');
  const [results, setResults] = useState([]);
  const [failedGames, setFailedGames] = useState([]);
  const [error, setError] = useState(null);
  const [meta, setMeta] = useState({ total: 0, current: 0, progress: 0 });
  const [currentTab, setCurrentTab] = useState(0);
  const [aggregateMetrics, setAggregateMetrics] = useState(null);
  const [isRetrying, setIsRetrying] = useState(false);
  const [openAddDialog, setOpenAddDialog] = useState(false);
  const [extraInput, setExtraInput] = useState('');
  const [openConfirmDialog, setOpenConfirmDialog] = useState(false);
  const [confirmActionName, setConfirmActionName] = useState('');
  const [confirmItems, setConfirmItems] = useState([]);
  const [confirmUsing, setConfirmUsing] = useState('');
  const [confirmPayload, setConfirmPayload] = useState(null);
  const [hasRawCoach, setHasRawCoach] = useState(false);
  const { isDarkMode } = useTheme();

  // Helper: create friendly user message from an Error/Axios error
  const extractUserMessage = (err, fallback) => {
    if (!err) return fallback || 'Something went wrong';
    // Axios-style response message
    const dataMsg = err?.response?.data?.message || err?.response?.data?.detail;
    if (dataMsg) return dataMsg;
    // Map some known HTTP status codes
    const status = err?.response?.status;
    if (status === 401) return 'Your session expired — please sign in again.';
    if (status === 403) return "You don't have permission to perform this action.";
    if (status === 402) return 'Insufficient credits to perform this action.';
    if (status === 404) return 'Requested report not found.';
    // Fall back to the Error message or provided fallback
    if (err?.message) return err.message;
    return fallback || 'Something went wrong. Please try again.';
  };

  const cardSx = {
    mb: 4,
    bgcolor: isDarkMode ? 'rgba(15, 23, 42, 0.9)' : 'background.paper',
    color: isDarkMode ? '#e2e8f0' : 'inherit',
    border: isDarkMode ? '1px solid rgba(148, 163, 184, 0.25)' : 'none',
  };

  const listTextSx = {
    '& .MuiListItemText-primary': {
      color: isDarkMode ? '#e2e8f0' : 'inherit',
    },
    '& .MuiListItemText-secondary': {
      color: isDarkMode ? 'rgba(203, 213, 225, 0.85)' : 'text.secondary',
    },
  };

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

  useEffect(() => {
    const loadReportWithRetry = async (batchIdentifier) => {
      let report = null;
      let lastError = null;

      for (let attempt = 1; attempt <= 5; attempt += 1) {
        try {
          report = await getBatchReport(batchIdentifier);
          break;
        } catch (fetchErr) {
          lastError = fetchErr;
          if (attempt < 5) {
            await new Promise((resolve) => setTimeout(resolve, 600));
          }
        }
      }

      if (!report) {
        throw lastError || new Error('Failed to load batch report');
      }

      return report;
    };

    if (reportId) {
      const loadSavedReport = async () => {
        setIsLoadingReport(true);
        setMessage('Loading saved batch report...');
        setError(null);
        try {
          const report = await loadReportWithRetry(reportId);

          if (String(report.status || '').toLowerCase() === 'failed') {
            setStatus('FAILURE');
            setError(report.message || 'Analysis failed');
            setMessage(report.message || 'Analysis failed');
            setProgress(100);
          } else {
            applyBatchReport(setResults, setFailedGames, setAggregateMetrics, report);
            setHasRawCoach(Boolean(report.coaching_report));
            setMeta({
              total: report.games_count || (Array.isArray(report.per_game_results) ? report.per_game_results.length : 0),
              current: Array.isArray(report.per_game_results) ? report.per_game_results.length : 0,
              progress: 100,
            });
            setProgress(100);
            setMessage('Loaded saved batch report');
            setStatus(String(report.status || 'completed').toUpperCase());
          }
        } catch (err) {
          console.error('Error loading saved report:', err);
          const msg = extractUserMessage(err, 'Failed to load saved batch report.');
          setError(msg);
          toast.error(msg);
        } finally {
          setIsLoadingReport(false);
        }
      };

      loadSavedReport();
      return;
    }

    if (!taskId) {
      navigate('/batch-analysis');
      return;
    }

    const pollStatus = async () => {
      try {
        const response = await getBatchStatus(taskId);

        if (!response) {
          setError('Failed to fetch analysis status');
          return true;
        }

        const statusValue = String(response.status || 'pending').toUpperCase();
        const completedCount = Number(response.completed_games || 0);
        const totalCount = Number(response.games_count || 0);
        const progressValue = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

        setStatus(statusValue);
        setMeta((prevMeta) => ({
          ...prevMeta,
          total: totalCount || prevMeta.total,
          current: completedCount || prevMeta.current,
          progress: progressValue || prevMeta.progress,
        }));
        setProgress(progressValue);
        setMessage(response.progress || response.message || '');

        if (statusValue === 'PENDING' || statusValue === 'IN_PROGRESS' || statusValue === 'STARTED' || statusValue === 'PROGRESS') {
          if (Array.isArray(response.errors) && response.errors.length > 0) {
            setFailedGames(normalizeFailedGames(response.errors));
          }
          return false;
        }

        try {
          const report = await loadReportWithRetry(taskId);
          if (String(report.status || '').toLowerCase() === 'failed') {
            setStatus('FAILURE');
            const msg = report.message || 'Analysis failed — insufficient successful games. Try adding more games and retry.';
            setError(msg);
            toast.error(msg);
            return true;
          }

          applyBatchReport(setResults, setFailedGames, setAggregateMetrics, report);
          setHasRawCoach(Boolean(report.coaching_report));
          setHasRawCoach(Boolean(report.coaching_report));
          setMeta({
            total: report.games_count || totalCount,
            current: Array.isArray(report.per_game_results) ? report.per_game_results.length : completedCount,
            progress: 100,
          });
          setProgress(100);
          setMessage('Analysis completed successfully!');
          setStatus(String(report.status || 'completed').toUpperCase());
          toast.success('Analysis completed successfully!');
          return true;
        } catch (reportErr) {
          console.error('Error loading batch report:', reportErr);
          const msg = extractUserMessage(reportErr, 'Failed to load batch report.');
          setError(msg);
          toast.error(msg);
          return true;
        }

      } catch (err) {
        console.error('Error polling status:', err);
        const msg = extractUserMessage(err, 'Error checking analysis progress.');
        setError(msg);
        toast.error(msg);
        return true;
      }
    };

    const interval = setInterval(async () => {
      const shouldStop = await pollStatus();
      if (shouldStop) {
        clearInterval(interval);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [taskId, reportId, navigate]);

  const renderProgress = () => (
    <Box sx={{ textAlign: 'center', py: 4 }}>
      <CircularProgress size={60} thickness={4} />
      <Typography variant="h6" sx={{ mt: 2 }}>
        {message}
      </Typography>
      <Box sx={{ width: '100%', mt: 2 }}>
        <LinearProgress variant="determinate" value={progress} />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          {meta.current} of {meta.total} games analyzed
        </Typography>
      </Box>
    </Box>
  );

  const renderOverallMetrics = () => {
    if (!aggregateMetrics?.overall) return null;

    const overall = aggregateMetrics.overall;
    const gamesCount = Math.max(results.length, 1);
    const impactMetrics = aggregateMetrics?.impact_metrics || aggregateMetrics?.coach_report?.impact_metrics || null;
    const chartData = [
      { name: 'Blunders', value: overall.blunders || 0 },
      { name: 'Mistakes', value: overall.mistakes || 0 },
      { name: 'Inaccuracies', value: overall.inaccuracies || 0 }
    ];

    return (
      <Card sx={cardSx}>
        <CardContent>
          <Typography variant="h5" gutterBottom>Overall Performance</Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Box sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>Average Accuracy</Typography>
                <Typography variant="h3" color="primary">
                  {(overall.accuracy || 0).toFixed(1)}%
      </Typography>
                <Box sx={{ height: 300, mt: 2 }}>
                  <PieChart>
                    <Pie
                      data={chartData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label
                    >
                      {chartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </Box>
              </Box>
            </Grid>
            <Grid item xs={12} md={6}>
              <Box sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>Statistics per Game</Typography>
                <List>
                  <ListItem>
                    <ListItemText
                      primary="Blunders"
                      secondary={`${((overall.blunders || 0) / gamesCount).toFixed(1)} per game`}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Mistakes"
                      secondary={`${((overall.mistakes || 0) / gamesCount).toFixed(1)} per game`}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Inaccuracies"
                      secondary={`${((overall.inaccuracies || 0) / gamesCount).toFixed(1)} per game`}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Average Moves"
                      secondary={`${((overall.total_moves || 0) / gamesCount).toFixed(1)} moves`}
                    />
                  </ListItem>
                </List>
              </Box>
            </Grid>

            {impactMetrics && (
              <Grid item xs={12}>
                <Divider sx={{ my: 1 }} />
                <Typography variant="h6" gutterBottom>Impact-Weighted Errors</Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={4}>
                    <Card sx={{ bgcolor: isDarkMode ? 'rgba(15, 23, 42, 0.6)' : 'grey.50' }}>
                      <CardContent>
                        <Typography variant="subtitle2" color="text.secondary">Critical Errors per Game</Typography>
                        <Typography variant="h4">{Number(impactMetrics.critical_error_rate || 0).toFixed(2)}</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Card sx={{ bgcolor: isDarkMode ? 'rgba(15, 23, 42, 0.6)' : 'grey.50' }}>
                      <CardContent>
                        <Typography variant="subtitle2" color="text.secondary">Phase Risk Index</Typography>
                        <Typography variant="h4">{Number(impactMetrics.phase_risk_index || 0).toFixed(1)}</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Card sx={{ bgcolor: isDarkMode ? 'rgba(15, 23, 42, 0.6)' : 'grey.50' }}>
                      <CardContent>
                        <Typography variant="subtitle2" color="text.secondary">Accuracy Gap</Typography>
                        <Typography variant="h4">{Number(impactMetrics.accuracy_gap || 0).toFixed(1)}%</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12}>
                    <List dense sx={listTextSx}>
                      {Object.entries(impactMetrics.phase_risk || {}).map(([phase, score]) => (
                        <ListItem key={phase}>
                          <ListItemText
                            primary={`${phase.charAt(0).toUpperCase() + phase.slice(1)} risk`}
                            secondary={Number(score || 0).toFixed(1)}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Grid>
                </Grid>
              </Grid>
            )}

            </Grid>
        </CardContent>
      </Card>
    );
  };

  const renderCoachReport = () => {
    const coachReport = aggregateMetrics?.coach_report;
    if (!coachReport) return null;

    const strengths = Array.isArray(coachReport.top_strengths) ? coachReport.top_strengths : Array.isArray(coachReport.strengths) ? coachReport.strengths : [];
    const weaknesses = Array.isArray(coachReport.top_weaknesses) ? coachReport.top_weaknesses : Array.isArray(coachReport.weaknesses) ? coachReport.weaknesses : [];
    const actionPlan = Array.isArray(coachReport.action_plan) ? coachReport.action_plan : [];
    const improvements = Array.isArray(coachReport.improvement_areas) ? coachReport.improvement_areas : [];
    const openingsSeen = Array.isArray(coachReport.openings_seen) ? coachReport.openings_seen : [];
    const criticalMoments = Array.isArray(coachReport.critical_moments) ? coachReport.critical_moments : [];
    const trainingBlock = coachReport.training_block || null;
    const phaseMotifs = coachReport.phase_motifs || null;
    const impactMetrics = coachReport.impact_metrics || null;
    const sampleSizeNote = coachReport.sample_size_note || '';

    return (
      <Card sx={cardSx}>
        <CardContent>
          <Typography variant="h5" gutterBottom>Combined Coaching Report</Typography>
          {sampleSizeNote && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {sampleSizeNote}
            </Typography>
          )}
          <Typography variant="body1" sx={{ mb: 3 }}>
            {coachReport.summary || coachReport.key_takeaway || 'No summary available yet.'}
          </Typography>

          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>Top Strengths</Typography>
              <List dense sx={listTextSx}>
                {strengths.length > 0 ? strengths.map((item, idx) => (
                  <ListItem key={`strength-${idx}`}>
                    <ListItemText primary={typeof item === 'string' ? item : item.label || item.pattern || String(item)} />
                  </ListItem>
                )) : <ListItem><ListItemText primary="No strengths detected yet" /></ListItem>}
              </List>
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>Recurring Weaknesses</Typography>
              <List dense sx={listTextSx}>
                {weaknesses.length > 0 ? weaknesses.map((item, idx) => (
                  <ListItem key={`weakness-${idx}`}>
                    <ListItemText primary={typeof item === 'string' ? item : item.label || item.pattern || String(item)} />
                  </ListItem>
                )) : <ListItem><ListItemText primary="No weaknesses detected yet" /></ListItem>}
              </List>
            </Grid>

            <Grid item xs={12}>
              <Divider sx={{ my: 1 }} />
              <Typography variant="h6" gutterBottom>Action Plan</Typography>
              <List dense>
                {actionPlan.length > 0 ? actionPlan.map((item, idx) => (
                  <ListItem key={`plan-${idx}`}>
                    <ListItemText primary={item} />
                  </ListItem>
                )) : <ListItem><ListItemText primary="No action plan available yet" /></ListItem>}
              </List>
            </Grid>

            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Areas To Improve</Typography>
              <List dense sx={listTextSx}>
                {improvements.length > 0 ? improvements.map((item, idx) => (
                  <ListItem key={`improvement-${idx}`}>
                    <ListItemText primary={item} />
                  </ListItem>
                )) : <ListItem><ListItemText primary="No improvement areas identified yet" /></ListItem>}
              </List>
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>Openings Seen</Typography>
              <List dense sx={listTextSx}>
                {openingsSeen.length > 0 ? openingsSeen.map((item, idx) => (
                  <ListItem key={`opening-${idx}`}>
                    <ListItemText primary={item} />
                  </ListItem>
                )) : <ListItem><ListItemText primary="No opening patterns available" /></ListItem>}
              </List>
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>Critical Moments</Typography>
              <List dense sx={listTextSx}>
                {criticalMoments.length > 0 ? criticalMoments.map((item, idx) => (
                  <ListItem key={`moment-${idx}`}>
                    <ListItemText
                      primary={`Game ${item.game_id || '?'} • Move ${item.move_number || '?'} • ${item.san || '-'}`}
                      secondary={`${item.classification || 'unknown'} • eval change ${Number(item.eval_change || 0).toFixed(2)}`}
                    />
                  </ListItem>
                )) : <ListItem><ListItemText primary="No critical moments detected" /></ListItem>}
              </List>
            </Grid>

            {trainingBlock && (
              <Grid item xs={12}>
                <Divider sx={{ my: 1 }} />
                <Typography variant="h6" gutterBottom>Training Block</Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" gutterBottom>Focus Areas</Typography>
                    <List dense sx={listTextSx}>
                      {(Array.isArray(trainingBlock.focus_areas) ? trainingBlock.focus_areas : []).map((item, idx) => (
                        <ListItem key={`focus-${idx}`}>
                          <ListItemText primary={item} />
                        </ListItem>
                      ))}
                    </List>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" gutterBottom>Weekly Target</Typography>
                    <List dense sx={listTextSx}>
                      <ListItem>
                        <ListItemText primary={trainingBlock.weekly_target?.goal || 'No weekly goal available'} />
                      </ListItem>
                      <ListItem>
                        <ListItemText primary={trainingBlock.weekly_target?.measure || 'No weekly measure available'} />
                      </ListItem>
                      <ListItem>
                        <ListItemText primary={`Confidence: ${trainingBlock.weekly_target?.confidence || 'medium'}`} />
                      </ListItem>
                    </List>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" gutterBottom>Drills</Typography>
                    <List dense sx={listTextSx}>
                      {(Array.isArray(trainingBlock.drills) ? trainingBlock.drills : []).map((item, idx) => (
                        <ListItem key={`drill-${idx}`}>
                          <ListItemText primary={item} />
                        </ListItem>
                      ))}
                    </List>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" gutterBottom>Checklist</Typography>
                    <List dense sx={listTextSx}>
                      {(Array.isArray(trainingBlock.checklist) ? trainingBlock.checklist : []).map((item, idx) => (
                        <ListItem key={`checklist-${idx}`}>
                          <ListItemText primary={item} />
                        </ListItem>
                      ))}
                    </List>
                  </Grid>
                </Grid>
              </Grid>
            )}

            {phaseMotifs && (
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Weakest Phase Motifs{phaseMotifs.weakest_phase ? ` - ${phaseMotifs.weakest_phase.charAt(0).toUpperCase() + phaseMotifs.weakest_phase.slice(1)}` : ''}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {phaseMotifs.correction_rule || 'Review this phase with a repeatable correction rule.'}
                </Typography>
                <List dense sx={listTextSx}>
                  {(Array.isArray(phaseMotifs.motifs) ? phaseMotifs.motifs : []).slice(0, 2).map((item, idx) => (
                    <ListItem key={`motif-${idx}`}>
                      <ListItemText
                        primary={`${item.name || 'Motif'} • ${item.count || 0} occurrences`}
                        secondary={`${item.correction_rule || 'No correction rule available'}${Array.isArray(item.evidence) && item.evidence.length > 0 ? ` • evidence: ${item.evidence.map((e) => `move ${e.move || '?'} ${e.san || ''}`.trim()).join(', ')}` : ''}`}
                      />
                    </ListItem>
                  ))}
                </List>
              </Grid>
            )}

            {impactMetrics && (
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>Impact Snapshot</Typography>
                <List dense sx={listTextSx}>
                  <ListItem>
                    <ListItemText primary="Critical Errors per Game" secondary={Number(impactMetrics.critical_error_rate || 0).toFixed(2)} />
                  </ListItem>
                  <ListItem>
                    <ListItemText primary="Phase Risk Index" secondary={Number(impactMetrics.phase_risk_index || 0).toFixed(1)} />
                  </ListItem>
                  <ListItem>
                    <ListItemText primary="Accuracy Gap" secondary={`${Number(impactMetrics.accuracy_gap || 0).toFixed(1)}%`} />
                  </ListItem>
                </List>
              </Grid>
            )}
          </Grid>
        </CardContent>
      </Card>
    );
  };

  const renderPhaseAnalysis = () => {
    if (!aggregateMetrics) return null;

    const phases = ['opening', 'middlegame', 'endgame'];
    const phaseData = phases.map(phase => ({
      name: phase.charAt(0).toUpperCase() + phase.slice(1),
      accuracy: aggregateMetrics[phase]?.accuracy || 0
    }));
    const phaseMotifs = aggregateMetrics?.phase_motifs || aggregateMetrics?.coach_report?.phase_motifs || aggregateMetrics?.training_block?.phase_motifs || null;

    return (
      <Card sx={cardSx}>
        <CardContent>
          <Typography variant="h5" gutterBottom>Phase Analysis</Typography>
          <Box sx={{ height: 300, mt: 2 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={phaseData}>
                <CartesianGrid strokeDasharray="3 3" stroke={isDarkMode ? 'rgba(148,163,184,0.25)' : '#d1d5db'} />
                <XAxis dataKey="name" stroke={isDarkMode ? '#cbd5e1' : '#374151'} />
                <YAxis domain={[0, 100]} stroke={isDarkMode ? '#cbd5e1' : '#374151'} />
                <Tooltip />
                <Bar dataKey="accuracy" fill={isDarkMode ? '#7c83ff' : '#8884d8'} name="Accuracy %" />
              </BarChart>
            </ResponsiveContainer>
          </Box>
          <List dense sx={{ mt: 2 }}>
            {phases.map((phase) => {
              const opportunities = aggregateMetrics[phase]?.opportunities || 0;
              const bestMoves = aggregateMetrics[phase]?.best_moves || 0;
              const criticalBestMoves = aggregateMetrics[phase]?.critical_best_moves || 0;
              const opportunitiesText = opportunities > 0
                ? `${criticalBestMoves} / ${opportunities} opportunities`
                : `${bestMoves}`;
              return (
                <ListItem key={phase}>
                  <ListItemText
                    primary={phase.charAt(0).toUpperCase() + phase.slice(1)}
                    secondary={`Accuracy ${(aggregateMetrics[phase]?.accuracy || 0).toFixed(1)}% • ${opportunities > 0 ? 'Critical best moves' : 'Best moves'} ${opportunitiesText}`}
                  />
                </ListItem>
              );
            })}
          </List>
          {phaseMotifs?.motifs?.length ? (
            <Box sx={{ mt: 3 }}>
              <Typography variant="h6" gutterBottom>
                Weakest Phase Motifs
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {phaseMotifs.correction_rule || 'Use one repeatable correction rule when reviewing this phase.'}
              </Typography>
              <List dense sx={listTextSx}>
                {phaseMotifs.motifs.slice(0, 2).map((motif, index) => (
                  <ListItem key={`phase-motif-${index}`}>
                    <ListItemText
                      primary={`${motif.name || 'Motif'} • ${motif.count || 0} occurrences`}
                      secondary={motif.correction_rule || 'No correction rule available'}
                    />
                  </ListItem>
                ))}
              </List>
            </Box>
          ) : null}
          {aggregateMetrics.opening?.repertoire && (
            <Box sx={{ mt: 3 }}>
              <Typography variant="h6" gutterBottom>Opening Repertoire</Typography>
              <List>
                {Object.entries(aggregateMetrics.opening.repertoire)
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 5)
                  .map(([move, frequency]) => (
                    <ListItem key={move}>
                      <ListItemText
                        primary={move}
                        secondary={`${frequency.toFixed(1)}% of games`}
                      />
                    </ListItem>
                  ))}
              </List>
        </Box>
      )}
        </CardContent>
      </Card>
    );
  };

  const renderTimeManagement = () => {
    if (!aggregateMetrics?.time_management) return null;

    const timeMetrics = aggregateMetrics.time_management;
    const gamesCount = Math.max(results.length, 1);
    const timeDataUnavailable = String(timeMetrics.data_status || '').toLowerCase() !== 'available';
    return (
      <Card sx={cardSx}>
        <CardContent>
          <Typography variant="h5" gutterBottom>Time Management</Typography>
          {timeDataUnavailable ? (
            <Typography variant="body2" color="text.secondary">
              Time data is unavailable for this batch (clock metadata was not present in the analyzed games).
            </Typography>
          ) : (
          <List>
            <ListItem>
              <ListItemText
                primary="Average Time per Move"
                secondary={`${(timeMetrics.avg_time_per_move || 0).toFixed(1)} seconds`}
              />
            </ListItem>
            <ListItem>
              <ListItemText
                primary="Time Pressure Mistakes"
                secondary={`${((timeMetrics.time_pressure_mistakes || 0) / gamesCount).toFixed(1)} per game`}
              />
            </ListItem>
            <ListItem>
              <ListItemText
                primary="Early Game Time Usage"
                secondary={`${(timeMetrics.early_game_time || 0).toFixed(1)}% of total time`}
              />
            </ListItem>
            <ListItem>
              <ListItemText
                primary="Endgame Time Usage"
                secondary={`${(timeMetrics.endgame_time || 0).toFixed(1)}% of total time`}
              />
            </ListItem>
          </List>
          )}
        </CardContent>
      </Card>
    );
  };

  const renderAIFeedback = () => {
    const aiFeedback = aggregateMetrics?.ai_feedback;
    if (!aiFeedback) return null;

    const isStructured = typeof aiFeedback === 'object' && !Array.isArray(aiFeedback);
    const aiTrainingBlock = isStructured ? aiFeedback.training_block || null : null;
    const aiPhaseMotifs = isStructured ? aiFeedback.phase_motifs || null : null;
    const aiImpactMetrics = isStructured ? aiFeedback.impact_metrics || null : null;

    return (
      <Card sx={cardSx}>
        <CardContent>
          <Typography variant="h5" gutterBottom>AI Analysis & Recommendations</Typography>
          {isStructured ? (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  {aiFeedback.summary || aiFeedback.coach_summary || 'No AI summary available.'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Source: {aiFeedback.source || 'statistical'}
                </Typography>
              </Grid>

              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>Strengths</Typography>
                <List dense sx={listTextSx}>
                  {(Array.isArray(aiFeedback.strengths) ? aiFeedback.strengths : []).map((item, idx) => (
                    <ListItem key={`ai-strength-${idx}`}>
                      <ListItemText primary={item} />
                    </ListItem>
                  ))}
                </List>
              </Grid>

              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>Weaknesses</Typography>
                <List dense sx={listTextSx}>
                  {(Array.isArray(aiFeedback.weaknesses) ? aiFeedback.weaknesses : []).map((item, idx) => (
                    <ListItem key={`ai-weakness-${idx}`}>
                      <ListItemText primary={item} />
                    </ListItem>
                  ))}
                </List>
              </Grid>

              <Grid item xs={12} md={4}>
                <Typography variant="subtitle2" gutterBottom>Opening</Typography>
                <Typography variant="body2" color="text.secondary">
                  {aiFeedback.opening?.analysis || 'No opening analysis available.'}
                </Typography>
              </Grid>
              <Grid item xs={12} md={4}>
                <Typography variant="subtitle2" gutterBottom>Middlegame</Typography>
                <Typography variant="body2" color="text.secondary">
                  {aiFeedback.middlegame?.analysis || 'No middlegame analysis available.'}
                </Typography>
              </Grid>
              <Grid item xs={12} md={4}>
                <Typography variant="subtitle2" gutterBottom>Endgame</Typography>
                <Typography variant="body2" color="text.secondary">
                  {aiFeedback.endgame?.analysis || 'No endgame analysis available.'}
                </Typography>
              </Grid>

              {aiTrainingBlock && (
                <Grid item xs={12}>
                  <Divider sx={{ my: 1 }} />
                  <Typography variant="h6" gutterBottom>AI Training Block</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {aiTrainingBlock.weekly_target?.goal || 'No AI training target available.'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {aiTrainingBlock.weekly_target?.measure || ''}
                  </Typography>
                </Grid>
              )}

              {aiPhaseMotifs && (
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom>AI Phase Motifs</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {aiPhaseMotifs.correction_rule || 'No correction rule available.'}
                  </Typography>
                </Grid>
              )}

              {aiImpactMetrics && (
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom>AI Impact Metrics</Typography>
                  <List dense sx={listTextSx}>
                    <ListItem>
                      <ListItemText primary="Critical Error Rate" secondary={Number(aiImpactMetrics.critical_error_rate || 0).toFixed(2)} />
                    </ListItem>
                    <ListItem>
                      <ListItemText primary="Phase Risk Index" secondary={Number(aiImpactMetrics.phase_risk_index || 0).toFixed(1)} />
                    </ListItem>
                  </List>
                </Grid>
              )}
            </Grid>
          ) : (
            <Typography variant="body1" sx={{ whiteSpace: 'pre-line' }}>
              {aiFeedback}
            </Typography>
          )}
        </CardContent>
      </Card>
    );
  };

  const handleTabChange = (event, newValue) => {
    setCurrentTab(newValue);
  };

  const prepareConfirm = (actionName, items, using, payload) => {
    setConfirmActionName(actionName);
    setConfirmItems(Array.isArray(items) ? items : []);
    setConfirmUsing(using || 'Game IDs');
    setConfirmPayload(payload || null);
    setOpenConfirmDialog(true);
  };

  const executeConfirmedAction = async () => {
    if (!confirmPayload) {
      toast.error('Nothing to submit');
      setOpenConfirmDialog(false);
      return;
    }

    try {
      setIsRetrying(true);
      const resp = await retryFailedGames(confirmPayload);
      const newTaskId = resp?.task_id || resp?.batch_id || resp?.id;
      toast.success(`${confirmActionName} started`);
      setOpenConfirmDialog(false);
      if (newTaskId) navigate(`/batch-analysis/results/${newTaskId}`);
    } catch (err) {
      console.error(`Error executing ${confirmActionName}:`, err);
      const msg = extractUserMessage(err, `Failed to start ${confirmActionName}.`);
      toast.error(msg);
      setError(msg);
    } finally {
      setIsRetrying(false);
      setConfirmActionName('');
      setConfirmItems([]);
      setConfirmUsing('');
      setConfirmPayload(null);
    }
  };

  const handleRetryFailed = async () => {
    if (!Array.isArray(failedGames) || failedGames.length === 0) {
      toast.error('No failed games to retry');
      return;
    }

    const failedIds = failedGames
      .map((f) => (typeof f === 'string' ? f : f.game_id || f.id || f.gameId || null))
      .filter(Boolean);

    if (failedIds.length < 5) {
      toast.error('Retry requires at least 5 games; please add more games or re-run a full batch.');
      return;
    }

    // Open confirmation dialog for retrying failed games
    prepareConfirm('Retry Failed Games', failedIds, 'Game IDs', { gameIds: failedIds });
  };

  const prepareAndOpenRetryConfirm = () => {
    if (!Array.isArray(failedGames) || failedGames.length === 0) {
      toast.error('No failed games to retry');
      return;
    }

    const failedIds = failedGames
      .map((f) => (typeof f === 'string' ? f : f.game_id || f.id || f.gameId || null))
      .filter(Boolean);
    const completedIds = Array.isArray(results)
      ? results.map((r) => r.game_id || r.id || null).filter(Boolean)
      : [];
    const needed = Math.max(0, 5 - failedIds.length);
    const toAdd = completedIds.slice(0, needed);
    const combined = Array.from(new Set([...failedIds, ...toAdd]));

    if (combined.length < 5) {
      toast.error('Not enough games available to build a retry batch of at least 5 games.');
      return;
    }

    prepareConfirm('Retry with Completed Games', combined, 'Game IDs', { gameIds: combined });
  };

  const handleOpenAdd = () => setOpenAddDialog(true);
  const handleCloseAdd = () => {
    setOpenAddDialog(false);
    setExtraInput('');
  };

  const parseExtraInput = (text) => {
    // Split into blocks separated by blank lines (allowing whitespace on blank lines)
    const blocks = text
      .split(/\r?\n\s*\r?\n/)
      .map((b) => b.trim())
      .filter(Boolean);

    const ids = [];
    const pgns = [];

    const isLikelyPgn = (s) => {
      if (!s) return false;
      const lowered = s.toLowerCase();
      if (lowered.includes('[event') || lowered.includes('[site') || lowered.includes('[date') || lowered.includes('[white')) return true;
      if (/\d+\./.test(s)) return true; // contains move numbers like '1.'
      // PGNs are typically longer than short ids
      if (s.length > 50 && s.split(' ').length > 5) return true;
      return false;
    };

    blocks.forEach((block) => {
      // If block looks like a PGN, attempt to split multiple PGNs in one block
      if (isLikelyPgn(block)) {
        // Split before repeated [Event headers
        const splitRegex = /(?=\[Event\s)/i;
        const parts = block.split(splitRegex).map((p) => p.trim()).filter(Boolean);
        if (parts.length > 1) {
          parts.forEach((p) => {
            if (isLikelyPgn(p)) pgns.push(p);
            else ids.push(p);
          });
          return;
        }

        pgns.push(block);
        return;
      }

      // Otherwise split by common separators and treat as IDs
      const parts = block.split(/\s|,|;|\r|\n/).map((p) => p.trim()).filter(Boolean);
      parts.forEach((part) => {
        // treat anything that looks numeric or uuid-like as id
        if (/^[0-9]+$/.test(part) || /^[0-9a-fA-F-]{8,}$/.test(part)) {
          ids.push(part);
        } else if (isLikelyPgn(part)) {
          pgns.push(part);
        } else {
          // fallback: assume id
          ids.push(part);
        }
      });
    });

    return { ids: Array.from(new Set(ids)), pgns: Array.from(new Set(pgns)) };
  };

  const handleAddAndRetry = async () => {
    const parsed = parseExtraInput(extraInput);
    const extraIds = parsed.ids || [];
    const extraPgns = parsed.pgns || [];
    const failedIds = failedGames
      .map((f) => (typeof f === 'string' ? f : f.game_id || f.id || f.gameId || null))
      .filter(Boolean);

    const combined = Array.from(new Set([...failedIds, ...extraIds]));

    // Prefer submitting by IDs if we have enough IDs (>=5)
    if (combined.length >= 5) {
      // Open confirm dialog for IDs
      handleCloseAdd();
      prepareConfirm('Add & Retry', combined, 'Game IDs', { gameIds: combined });
      return;
    }

    // If not enough IDs, but we have PGNs, submit PGNs if there are >=5
    if (extraPgns.length >= 5) {
      // Open confirm dialog for PGNs
      handleCloseAdd();
      prepareConfirm('Add & Retry', extraPgns, 'PGNs', { pgnList: extraPgns });
      return;
    }

    // Not enough combined IDs and not enough PGNs
    toast.error('Retry requires at least 5 games; please add more game IDs or provide at least 5 PGNs.');
    return;
  };

    if (error) {
      return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="error" variant="h6">{error}</Typography>
      </Box>
    );
  }

  if (isLoadingReport || (status !== 'SUCCESS' && status !== 'COMPLETED' && status !== 'PARTIAL')) {
    return renderProgress();
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" gutterBottom>
          Batch Analysis Results
        </Typography>
        <Typography variant="subtitle1" gutterBottom>
          {results.length} games analyzed • {failedGames.length} failed
        </Typography>

        <FailedGamesList failures={failedGames} />

        {failedGames.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Button variant="contained" color="primary" onClick={handleRetryFailed} disabled={isRetrying}>
              {isRetrying ? 'Retrying...' : 'Retry Failed Games'}
            </Button>
            {failedGames.length < 5 && (
              <>
                <Button variant="outlined" sx={{ ml: 2 }} onClick={handleOpenAdd}>
                  Add Games & Retry
                </Button>
                {((results?.length || 0) + failedGames.length) >= 5 && (
                  <Button variant="text" sx={{ ml: 2 }} onClick={prepareAndOpenRetryConfirm} disabled={isRetrying}>
                    Retry with Completed Games
                  </Button>
                )}
              </>
            )}
          </Box>
        )}
          <Dialog open={openConfirmDialog} onClose={() => setOpenConfirmDialog(false)} fullWidth maxWidth="sm">
            <DialogTitle>{confirmActionName || 'Confirm Batch Action'}</DialogTitle>
            <DialogContent>
              <Typography variant="body1" sx={{ mb: 1 }}>
                {confirmItems.length} {confirmItems.length === 1 ? 'game' : 'games'} will be submitted.
              </Typography>
              <Typography variant="body2" sx={{ mb: 2 }}>
                Using: {confirmUsing || 'Game IDs'}
              </Typography>
              {/* Preview: show first 5 items only */}
              {(() => {
                const previewItems = confirmItems.slice(0, 5);
                const moreCount = Math.max(0, confirmItems.length - previewItems.length);
                const previewPGN = (pgn) => {
                  if (!pgn) return '';
                  const lines = String(pgn).split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
                  const first = lines.length > 0 ? lines[0] : String(pgn).slice(0, 120);
                  return first.length > 120 ? `${first.slice(0, 120)}...` : first;
                };

                return (
                  <>
                    <List dense sx={{ maxHeight: 240, overflow: 'auto' }}>
                      {previewItems.map((it, idx) => (
                        <ListItem key={`${String(it)}-${idx}`}>
                          <ListItemText primary={confirmUsing === 'PGNs' ? previewPGN(it) : String(it)} />
                        </ListItem>
                      ))}
                    </List>
                    {moreCount > 0 && (
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                        +{moreCount} more
                      </Typography>
                    )}
                  </>
                );
              })()}
              <Typography variant="body2" sx={{ mt: 2 }}>
                Proceed to start this batch? Retries do not charge additional credits.
              </Typography>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setOpenConfirmDialog(false)} disabled={isRetrying}>Cancel</Button>
              <Button onClick={executeConfirmedAction} variant="contained" disabled={isRetrying}>{isRetrying ? 'Starting...' : 'Confirm'}</Button>
            </DialogActions>
          </Dialog>

        {/* Banner for PARTIAL batches where coaching generation failed */}
        {status === 'PARTIAL' && !hasRawCoach && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            Your games were analyzed, but coaching report generation didn&apos;t complete. You can still view engine stats below.
          </Alert>
        )}

        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
          <Tabs
            value={currentTab}
            onChange={handleTabChange}
            variant="scrollable"
            allowScrollButtonsMobile
            sx={{
              '& .MuiTab-root': {
                color: isDarkMode ? 'rgba(203,213,225,0.75)' : 'rgba(55,65,81,0.8)',
                fontWeight: 600,
              },
              '& .MuiTab-root.Mui-selected': {
                color: isDarkMode ? '#38bdf8' : '#1d4ed8',
              },
              '& .MuiTabs-indicator': {
                backgroundColor: isDarkMode ? '#38bdf8' : '#1d4ed8',
                height: 3,
              },
            }}
          >
            <Tab label="Coach Report" />
            <Tab label="Overall Performance" />
            <Tab label="Phase Analysis" />
            <Tab label="Time Management" />
            <Tab label="AI Feedback" />
          </Tabs>
        </Box>

        <Box sx={{ mt: 3 }}>
          {currentTab === 0 && renderCoachReport()}
          {currentTab === 1 && renderOverallMetrics()}
          {currentTab === 2 && renderPhaseAnalysis()}
          {currentTab === 3 && renderTimeManagement()}
          {currentTab === 4 && renderAIFeedback()}
        </Box>
        <Dialog open={openAddDialog} onClose={handleCloseAdd} fullWidth maxWidth="sm">
          <DialogTitle>Add additional game IDs or PGNs</DialogTitle>
          <DialogContent>
            <TextField
              multiline
              minRows={4}
              fullWidth
              placeholder="Paste game IDs or PGNs separated by newlines, commas, or spaces"
              value={extraInput}
              onChange={(e) => setExtraInput(e.target.value)}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseAdd} disabled={isRetrying}>Cancel</Button>
            <Button onClick={handleAddAndRetry} variant="contained" disabled={isRetrying}>Start Retry</Button>
          </DialogActions>
        </Dialog>
      </Box>
    </Container>
  );
};

export default BatchAnalysisResults;
