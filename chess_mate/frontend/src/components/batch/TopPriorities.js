/**
 * TopPriorities.js
 *
 * Displays the top 3 priorities from the coaching report.
 * If coaching_report is null, shows a graceful fallback.
 *
 * Props:
 *   - coaching_report: object | null
 *       Contains top_3_priorities array of 3 priority objects
 *
 * Pure display component — no state, no API calls.
 */

import React from 'react';
import {
  Box,
  Typography,
  Alert,
  Container
} from '@mui/material';
import PriorityCard from './PriorityCard';

const TopPriorities = ({ coaching_report }) => {
  // If coaching_report is null or top_3_priorities missing/empty, show fallback
  if (
    !coaching_report ||
    !coaching_report.top_3_priorities ||
    !Array.isArray(coaching_report.top_3_priorities) ||
    coaching_report.top_3_priorities.length === 0
  ) {
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

  const priorities = coaching_report.top_3_priorities;

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 3 }}>
        Top 3 Priorities
      </Typography>

      <Box>
        {priorities.map((priority, index) => (
          <PriorityCard key={priority.rank || index} priority={priority} />
        ))}
      </Box>
    </Container>
  );
};

export default TopPriorities;
