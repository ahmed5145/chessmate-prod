/**
 * Inline reminder for colored left borders in report lists.
 */

import React from 'react';
import { Typography } from '@mui/material';

const SectionStatusHint = ({ sx = {} }) => (
  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.5, ...sx }}>
    Side stripe:{' '}
    <Typography component="span" variant="caption" sx={{ color: 'success.main', fontWeight: 600 }}>
      green
    </Typography>
    {' '}= strong ·{' '}
    <Typography component="span" variant="caption" sx={{ color: 'warning.main', fontWeight: 600 }}>
      amber
    </Typography>
    {' '}= needs work ·{' '}
    <Typography component="span" variant="caption" sx={{ color: 'error.main', fontWeight: 600 }}>
      red
    </Typography>
    {' '}= trouble spot
  </Typography>
);

export default SectionStatusHint;
