/**
 * One-time legend for batch report status colors (W/L/D and insight severity).
 */

import React from 'react';
import { Box, Chip, Container, Typography } from '@mui/material';

const BatchReportLegend = () => (
  <Container maxWidth="lg" sx={{ py: 1 }}>
    <Box
      sx={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 1,
        alignItems: 'center',
        p: 1.5,
        borderRadius: 1,
        border: '1px solid',
        borderColor: 'divider',
        bgcolor: 'background.paper',
      }}
    >
      <Typography variant="caption" color="text.secondary" sx={{ mr: 0.5 }}>
        Legend:
      </Typography>
      <Chip size="small" label="Win" color="success" />
      <Chip size="small" label="Loss" color="error" />
      <Chip size="small" label="Draw" variant="outlined" />
      <Chip size="small" label="Needs work" color="warning" variant="outlined" />
      <Chip size="small" label="Strength" color="success" variant="outlined" />
      <Chip size="small" label="Critical issue" color="error" variant="outlined" />
    </Box>
  </Container>
);

export default BatchReportLegend;
