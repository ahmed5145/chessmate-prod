import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { useTheme } from '../context/ThemeContext';
import { checkBatchAnalysisStatus } from '../services/apiRequests';
import {
  Box,
  Paper,
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
import { Line, Radar } from 'react-chartjs-2';
import {
  Target,
  BookOpen,
  Clock
} from 'lucide-react';

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

const ProgressBar = ({ current, total, startTime }) => {
  const progress = total > 0 ? Math.round((current / total) * 100) : 0;
  const elapsedTime = Math.floor((Date.now() - startTime) / 1000);
  
  return (
    <Box sx={{ width: '100%', mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
        <Typography variant="body2">Progress: {progress}%</Typography>
        <Typography variant="body2">Time Elapsed: {formatTime(elapsedTime)}</Typography>
      </Box>
      <Box sx={{ 
        width: '100%', 
        height: 8, 
        bgcolor: 'background.paper',
        borderRadius: 1,
        position: 'relative' 
      }}>
        <Box sx={{
          width: `${progress}%`,
          height: '100%',
          bgcolor: 'primary.main',
          borderRadius: 1,
          transition: 'width 0.5s ease-in-out'
        }} />
      </Box>
      <Typography variant="body2" sx={{ mt: 1 }}>
        Analyzing game {current} of {total}
      </Typography>
    </Box>
  );
};

const formatTime = (seconds) => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

const TabPanel = ({ children, value, index, ...other }) => (
  <div
    role="tabpanel"
    hidden={value !== index}
    id={`tabpanel-${index}`}
    aria-labelledby={`tab-${index}`}
    {...other}
  >
    {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
  </div>
);

const BatchAnalysisResults = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('PROGRESS');
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('Initializing analysis...');
  const [results, setResults] = useState([]);
  const [failedGames, setFailedGames] = useState([]);
  const [error, setError] = useState(null);
  const [startTime] = useState(Date.now());
  const [meta, setMeta] = useState({ total: 0, current: 0, progress: 0 });
  const [currentTab, setCurrentTab] = useState(0);
  const [aggregateMetrics, setAggregateMetrics] = useState(null);
  const { isDarkMode } = useTheme();

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

  useEffect(() => {
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
  }, [taskId, navigate]);

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
    const chartData = [
      { name: 'Blunders', value: overall.blunders || 0 },
      { name: 'Mistakes', value: overall.mistakes || 0 },
      { name: 'Inaccuracies', value: overall.inaccuracies || 0 }
    ];

    return (
      <Card sx={{ mb: 4 }}>
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
                      secondary={`${((overall.blunders || 0) / results.length).toFixed(1)} per game`}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Mistakes"
                      secondary={`${((overall.mistakes || 0) / results.length).toFixed(1)} per game`}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Inaccuracies"
                      secondary={`${((overall.inaccuracies || 0) / results.length).toFixed(1)} per game`}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Average Moves"
                      secondary={`${((overall.total_moves || 0) / results.length).toFixed(1)} moves`}
                    />
                  </ListItem>
                </List>
      </Box>
            </Grid>
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

    return (
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h5" gutterBottom>Phase Analysis</Typography>
          <Box sx={{ height: 300, mt: 2 }}>
            <BarChart data={phaseData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <Bar dataKey="accuracy" fill="#8884d8" name="Accuracy %" />
            </BarChart>
          </Box>
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
    return (
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h5" gutterBottom>Time Management</Typography>
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
                secondary={`${((timeMetrics.time_pressure_mistakes || 0) / results.length).toFixed(1)} per game`}
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
        </CardContent>
      </Card>
    );
  };

  const renderAIFeedback = () => {
    if (!aggregateMetrics?.ai_feedback) return null;

    return (
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h5" gutterBottom>AI Analysis & Recommendations</Typography>
          <Typography variant="body1" sx={{ whiteSpace: 'pre-line' }}>
            {aggregateMetrics.ai_feedback}
          </Typography>
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

  if (status !== 'SUCCESS') {
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
          <Tabs value={currentTab} onChange={handleTabChange}>
            <Tab label="Overall Performance" />
            <Tab label="Phase Analysis" />
            <Tab label="Time Management" />
            <Tab label="AI Feedback" />
          </Tabs>
        </Box>

        <Box sx={{ mt: 3 }}>
          {currentTab === 0 && renderOverallMetrics()}
          {currentTab === 1 && renderPhaseAnalysis()}
          {currentTab === 2 && renderTimeManagement()}
          {currentTab === 3 && renderAIFeedback()}
        </Box>
      </Box>
    </Container>
  );
};

export default BatchAnalysisResults; 