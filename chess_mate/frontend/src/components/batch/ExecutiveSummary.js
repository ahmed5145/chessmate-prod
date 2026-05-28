/**
 * ExecutiveSummary.js
 *
 * Displays the executive summary from the coaching report.
 * If coaching_report is null (partial status), shows a graceful fallback.
 *
 * Props:
 *   - coaching_report: object | null
 *       Contains executive_summary string
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

const ExecutiveSummary = ({ coaching_report }) => {
  // If coaching_report is null (partial status), show alert
  if (!coaching_report) {
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

  // coaching_report is present; render executive_summary
  const executiveSummary = coaching_report.executive_summary || '';

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography
          variant="h5"
          sx={{
            textAlign: 'center',
            fontWeight: 600,
            lineHeight: 1.6,
            color: 'text.primary'
          }}
        >
          {executiveSummary}
        </Typography>
      </Box>
    </Container>
  );
};

export default ExecutiveSummary;
