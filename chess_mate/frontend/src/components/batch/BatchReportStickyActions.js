/**
 * Owner actions — sticky below navbar on mobile so Share/PDF stay reachable while scrolling.
 */

import React from 'react';
import { Box } from '@mui/material';
import BatchReportActions from './BatchReportActions';

const BatchReportStickyActions = (props) => (
  <Box
    className="batch-report-no-print batch-report-sticky-actions"
    sx={{
      position: { xs: 'sticky', md: 'static' },
      top: { xs: 56, sm: 64 },
      zIndex: { xs: 35, md: 'auto' },
      bgcolor: 'background.default',
      borderBottom: { xs: 1, md: 0 },
      borderColor: 'divider',
      py: { xs: 1, md: 0 },
      mb: { xs: 0.5, md: 2 },
    }}
  >
    <BatchReportActions {...props} />
  </Box>
);

export default BatchReportStickyActions;
