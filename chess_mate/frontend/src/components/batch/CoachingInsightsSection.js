/**
 * Structured coaching insights: level guidance, strengths, and phase narrative.
 */

import React from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
} from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import SchoolIcon from '@mui/icons-material/School';
import AutoStoriesIcon from '@mui/icons-material/AutoStories';
import ReportSectionShell, { ReportSubsection } from './ReportSectionShell';
import { toTitleCase } from '../../utils/formatLabel';

const InsightCard = ({ icon: Icon, title, children, accent = 'primary' }) => (
  <Paper
    variant="outlined"
    sx={(theme) => ({
      p: 2,
      height: '100%',
      borderLeft: 4,
      borderLeftColor: theme.palette[accent]?.main || theme.palette.primary.main,
      bgcolor: 'background.paper',
    })}
  >
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
      {Icon ? <Icon fontSize="small" color={accent} /> : null}
      <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
        {title}
      </Typography>
    </Box>
    {children}
  </Paper>
);

const CoachingInsightsSection = ({ batch_summary, coaching_report }) => {
  const band = batch_summary?.rating_band_coaching;
  const strengths = Array.isArray(batch_summary?.strength_patterns)
    ? batch_summary.strength_patterns
    : [];
  const narrative = coaching_report?.coaching_narrative;
  const phases = narrative && typeof narrative === 'object'
    ? [
        { key: 'opening', label: 'Opening' },
        { key: 'middlegame', label: 'Middlegame' },
        { key: 'endgame', label: 'Endgame' },
      ].filter((phase) => narrative[phase.key])
    : [];

  if (!band?.focus && strengths.length === 0 && phases.length === 0) {
    return null;
  }

  return (
    <ReportSectionShell
      title="Coaching insights"
      subtitle="Strengths and phase notes from this batch — separate from the numeric phase scores above."
    >
      <Grid container spacing={2}>
        {band?.focus ? (
          <Grid item xs={12} md={phases.length > 0 ? 6 : 12}>
            <InsightCard icon={SchoolIcon} title={`For your level${band.label ? ` (${band.label})` : ''}`} accent="secondary">
              <Typography variant="body1" sx={{ fontWeight: 600, mb: band.daily_drill ? 1 : 0 }}>
                {band.focus}
              </Typography>
              {band.daily_drill ? (
                <Typography variant="body2" color="text.secondary">
                  Daily drill: {band.daily_drill}
                </Typography>
              ) : null}
            </InsightCard>
          </Grid>
        ) : null}

        {phases.length > 0 ? (
          <Grid item xs={12} md={band?.focus ? 6 : 12}>
            <InsightCard icon={AutoStoriesIcon} title="Phase coaching notes" accent="info">
              <Box sx={{ display: 'grid', gap: 1.5 }}>
                {phases.map((phase) => (
                  <Box key={phase.key}>
                    <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary' }}>
                      {phase.label}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {narrative[phase.key]}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </InsightCard>
          </Grid>
        ) : null}
      </Grid>

      {strengths.length > 0 ? (
        <ReportSubsection title="What you did well" sx={{ mt: 3, mb: 0 }}>
          <Grid container spacing={1.5}>
            {strengths.map((item, index) => (
              <Grid item xs={12} sm={6} key={`strength-${item.pattern || index}`}>
                <InsightCard
                  icon={TrendingUpIcon}
                  title={item.pattern ? toTitleCase(item.pattern) : 'Strength'}
                  accent="success"
                >
                  <Typography variant="body2" color="text.secondary">
                    {item.detail || item.pattern}
                  </Typography>
                  {item.frequency ? (
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 0.75, display: 'block' }}>
                      Seen in {item.frequency}
                    </Typography>
                  ) : null}
                </InsightCard>
              </Grid>
            ))}
          </Grid>
        </ReportSubsection>
      ) : null}
    </ReportSectionShell>
  );
};

export default CoachingInsightsSection;
