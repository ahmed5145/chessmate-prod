/**
 * TrainingPlan.js — 4-week training plan from the coaching report.
 */

import React from 'react';
import {
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ReportSectionShell from './ReportSectionShell';

const TrainingPlan = ({ coaching_report }) => {
  if (!coaching_report?.training_plan) {
    return null;
  }

  const trainingPlan = coaching_report.training_plan;
  const weeks = [
    { key: 'week_1', label: 'Week 1' },
    { key: 'week_2', label: 'Week 2' },
    { key: 'week_3', label: 'Week 3' },
    { key: 'week_4', label: 'Week 4' }
  ];

  return (
    <ReportSectionShell
      title="4-week training plan"
      subtitle="AI-suggested study outline based on this batch. Pair with the game breakdown below for specific positions."
    >
      {weeks.map((week) => (
        <Accordion
          key={week.key}
          defaultExpanded={week.key === 'week_1'}
          sx={{ mb: 2 }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
              {week.label}
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="body2">
              {trainingPlan[week.key] || 'No training data available'}
            </Typography>
          </AccordionDetails>
        </Accordion>
      ))}
    </ReportSectionShell>
  );
};

export default TrainingPlan;
