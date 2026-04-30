/**
 * TrainingPlan.js
 * 
 * Displays a 4-week training plan from the coaching report.
 * If coaching_report is null, shows a graceful fallback.
 * 
 * Props:
 *   - coaching_report: object | null
 *       Contains training_plan object with week_1, week_2, week_3, week_4 strings
 * 
 * Pure display component — no state, no API calls.
 */

import React from 'react';
import {
  Typography,
  Alert,
  Container,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

const TrainingPlan = ({ coaching_report }) => {
  // If coaching_report is null or training_plan missing, show fallback
  if (!coaching_report || !coaching_report.training_plan) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="info" sx={{ mb: 4 }}>
          <Typography variant="body2">
            Coaching narrative unavailable for this batch — analysis data shown below.
          </Typography>
        </Alert>
      </Container>
    );
  }

  const trainingPlan = coaching_report.training_plan;
  const weeks = [
    { key: 'week_1', label: 'Week 1' },
    { key: 'week_2', label: 'Week 2' },
    { key: 'week_3', label: 'Week 3' },
    { key: 'week_4', label: 'Week 4' }
  ];

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 3 }}>
        4-Week Training Plan
      </Typography>

      {weeks.map((week) => (
        <Accordion key={week.key} sx={{ mb: 2 }}>
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
    </Container>
  );
};

export default TrainingPlan;
