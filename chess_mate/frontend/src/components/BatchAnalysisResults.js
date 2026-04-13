import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { useTheme } from '../context/ThemeContext';
import { checkBatchAnalysisStatus, fetchBatchReportById } from '../services/apiRequests';
import {
  Box,
  Typography,
  CircularProgress,
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
  const { isDarkMode } = useTheme();

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
    if (reportId) {
      const loadSavedReport = async () => {
        setIsLoadingReport(true);
        setMessage('Loading saved batch report...');
        setError(null);
        try {
          let report = null;
          let lastError = null;

          // Persisted report writes can be slightly delayed; retry briefly before failing UX.
          for (let attempt = 1; attempt <= 5; attempt += 1) {
            try {
              report = await fetchBatchReportById(reportId);
              break;
            } catch (fetchErr) {
              lastError = fetchErr;
              if (attempt < 5) {
                await new Promise((resolve) => setTimeout(resolve, 600));
              }
            }
          }

          if (!report) {
            throw lastError || new Error('Failed to load saved batch report');
          }

          const completedGames = Array.isArray(report.completed_games) ? report.completed_games : [];
          const failed = Array.isArray(report.failed_games) ? report.failed_games : [];
          setResults(completedGames);
          setFailedGames(failed);
          setAggregateMetrics(report.aggregate_metrics || null);
          setMeta({
            total: report.games_count || completedGames.length + failed.length,
            current: completedGames.length,
            progress: 100,
          });
          setProgress(100);
          setMessage('Loaded saved batch report');
          setStatus('SUCCESS');
        } catch (err) {
          console.error('Error loading saved report:', err);
          setError(err.message || 'Failed to load saved batch report');
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
        const response = await checkBatchAnalysisStatus(taskId);

        if (!response) {
          setError('Failed to fetch analysis status');
          return true;
        }

        const {
          state = 'PENDING',
          meta = {},
          completed_games = [],
          failed_games = [],
          aggregate_metrics = null
        } = response;

        setStatus(state);
          setMeta(prevMeta => ({
            ...prevMeta,
            ...meta,
            total: meta.total || prevMeta.total,
            current: meta.current || prevMeta.current,
            progress: meta.progress || prevMeta.progress
          }));
          setProgress(meta.progress || 0);
          setMessage(meta.message || '');

        if (state === 'FAILURE') {
          setError(meta.error || 'Analysis failed');
          toast.error(meta.error || 'Analysis failed');
          return true;
        }

        if (completed_games.length > 0) {
          setResults(completed_games);
        }

        if (failed_games.length > 0) {
          setFailedGames(failed_games);
        }

        if (aggregate_metrics) {
          setAggregateMetrics(aggregate_metrics);
        }

        if (state === 'SUCCESS') {
          toast.success('Analysis completed successfully!');
          return true;
        }

        return false;
      } catch (err) {
        console.error('Error polling status:', err);
        setError(err.message || 'Error checking analysis progress');
        toast.error(err.message || 'Error checking analysis progress');
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
    if (!coachReport) {
      return (
        <Card sx={cardSx}>
          <CardContent>
            <Typography variant="h6">Combined coaching report is not ready yet.</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              We are still collecting enough analyzed games in this batch to generate coaching guidance.
            </Typography>
          </CardContent>
        </Card>
      );
    }

    const strengths = Array.isArray(coachReport.top_strengths) ? coachReport.top_strengths : [];
    const weaknesses = Array.isArray(coachReport.top_weaknesses) ? coachReport.top_weaknesses : [];
    const improvements = Array.isArray(coachReport.improvement_areas) ? coachReport.improvement_areas : [];
    const actionPlan = Array.isArray(coachReport.action_plan) ? coachReport.action_plan : [];
    const openingsSeen = Array.isArray(coachReport.openings_seen) ? coachReport.openings_seen : [];
    const criticalMoments = Array.isArray(coachReport.critical_moments) ? coachReport.critical_moments : [];
    const trainingBlock = coachReport.training_block || aggregateMetrics?.training_block || null;
    const phaseMotifs = trainingBlock?.phase_motifs || coachReport.phase_motifs || aggregateMetrics?.phase_motifs || null;
    const impactMetrics = trainingBlock?.impact_metrics || coachReport.impact_metrics || aggregateMetrics?.impact_metrics || null;
    const performanceTier = coachReport.performance_tier || 'unknown';
    const confidence = coachReport.confidence || 'medium';
    const sampleSizeNote = coachReport.sample_size_note || '';

    return (
      <Card sx={cardSx}>
        <CardContent>
          <Typography variant="h5" gutterBottom>Coach Summary</Typography>
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={12} md={4}>
              <Card sx={{ bgcolor: isDarkMode ? 'rgba(15, 23, 42, 0.6)' : 'grey.50' }}>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">Performance Tier</Typography>
                  <Typography variant="h6" sx={{ textTransform: 'capitalize' }}>{performanceTier}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card sx={{ bgcolor: isDarkMode ? 'rgba(15, 23, 42, 0.6)' : 'grey.50' }}>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">Confidence</Typography>
                  <Typography variant="h6" sx={{ textTransform: 'capitalize' }}>{confidence}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card sx={{ bgcolor: isDarkMode ? 'rgba(15, 23, 42, 0.6)' : 'grey.50' }}>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">Key Takeaway</Typography>
                  <Typography variant="body2">{coachReport.key_takeaway || coachReport.summary || 'No key takeaway available'}</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
          {sampleSizeNote && (
            <Typography variant="body2" sx={{ mb: 2 }} color="text.secondary">
              {sampleSizeNote}
            </Typography>
          )}
          <Typography variant="body1" sx={{ mb: 3 }}>
            {coachReport.summary || 'No summary available yet.'}
          </Typography>

          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>Top Strengths</Typography>
              <List dense sx={listTextSx}>
                {strengths.length > 0 ? strengths.map((item, idx) => (
                  <ListItem key={`strength-${idx}`}>
                    <ListItemText primary={item} />
                  </ListItem>
                )) : <ListItem><ListItemText primary="No strengths detected yet" /></ListItem>}
              </List>
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>Recurring Weaknesses</Typography>
              <List dense sx={listTextSx}>
                {weaknesses.length > 0 ? weaknesses.map((item, idx) => (
                  <ListItem key={`weakness-${idx}`}>
                    <ListItemText primary={item} />
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
                      primary={`Game ${item.game_id} • Move ${item.move_number || '?'} • ${item.san || '-'}`}
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

    if (error) {
      return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="error" variant="h6">{error}</Typography>
      </Box>
    );
  }

  if (isLoadingReport || status !== 'SUCCESS') {
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
      </Box>
    </Container>
  );
};

export default BatchAnalysisResults;
