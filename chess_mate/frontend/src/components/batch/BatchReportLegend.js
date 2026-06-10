/**
 * Compact color key for batch report chips (replaces noisy chip row).
 */

import React from 'react';
import { Box, Typography } from '@mui/material';

const BatchReportLegend = () => (
  <Box sx={{ py: 0, pb: 1.5 }}>
    <Typography
      variant="caption"
      color="text.secondary"
      component="p"
      sx={{ lineHeight: 1.5, m: 0 }}
    >
      Color key:{' '}
      <Typography component="span" variant="caption" sx={{ color: 'success.main', fontWeight: 600 }}>
        green
      </Typography>
      {' '}= win or strength ·{' '}
      <Typography component="span" variant="caption" sx={{ color: 'error.main', fontWeight: 600 }}>
        red
      </Typography>
      {' '}= loss or critical mistake ·{' '}
      <Typography component="span" variant="caption" sx={{ color: 'warning.main', fontWeight: 600 }}>
        amber
      </Typography>
      {' '}= needs work · Hover{' '}
      <Typography component="span" variant="caption" sx={{ fontWeight: 600 }}>
        ⓘ
      </Typography>
      {' '}icons on metrics for definitions
    </Typography>
  </Box>
);

export default BatchReportLegend;
