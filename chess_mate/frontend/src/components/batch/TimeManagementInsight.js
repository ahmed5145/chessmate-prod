/**
 * TimeManagementInsight — batch clock pattern when PGN includes %clk data.
 */

import React from 'react';
import { Alert, Container, Tooltip, Typography } from '@mui/material';

const TimeManagementInsight = ({ batch_summary }) => {
  const summary = batch_summary?.time_management_summary;
  if (!summary?.insight) {
    return null;
  }

  const severity = summary.pattern === 'rushed_critical_moments' ? 'warning' : 'info';

  return (
    <Container maxWidth="lg" sx={{ py: 1 }}>
      <Alert severity={severity}>
        <Tooltip title="Only games with clock timestamps in the PGN are included in time analysis.">
          <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
            Time management
            {summary.games_with_clock_data
              ? ` · Clock data available for ${summary.games_with_clock_data} of ${summary.games_analyzed} games`
              : ''}
          </Typography>
        </Tooltip>
        <Typography variant="body2" sx={{ mt: 0.5 }}>
          {summary.insight}
        </Typography>
      </Alert>
    </Container>
  );
};

export default TimeManagementInsight;
