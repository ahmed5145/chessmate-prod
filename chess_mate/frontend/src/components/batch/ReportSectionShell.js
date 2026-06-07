/**
 * Shared heading block for batch report sections.
 */

import React from 'react';
import { Box, Typography } from '@mui/material';
import SectionStatusHint from './SectionStatusHint';

const ReportSectionShell = ({
  title,
  subtitle,
  showStatusHint = false,
  children,
  sx = {},
}) => (
  <Box sx={{ py: 2, ...sx }}>
    <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>
      {title}
    </Typography>
    {subtitle ? (
      <Typography variant="body2" color="text.secondary" sx={{ mb: showStatusHint ? 1 : 2 }}>
        {subtitle}
      </Typography>
    ) : null}
    {showStatusHint ? <SectionStatusHint sx={{ mb: 2 }} /> : null}
    {children}
  </Box>
);

export const ReportSubsection = ({ title, children, sx = {} }) => (
  <Box sx={{ mb: 3, ...sx }}>
    {title ? (
      <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5, color: 'text.primary' }}>
        {title}
      </Typography>
    ) : null}
    {children}
  </Box>
);

export default ReportSectionShell;
