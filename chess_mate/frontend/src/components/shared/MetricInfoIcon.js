import React from 'react';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { IconButton, Tooltip } from '@mui/material';
import { formatMetricTooltip } from '../../utils/metricGlossary';

/**
 * Compact (i) icon — metric definitions on hover/focus only.
 */
const MetricInfoIcon = ({
  metricKey = null,
  metricKeys = null,
  isDarkMode = false,
  size = 'small',
  sx = {},
}) => {
  const keys = metricKeys || (metricKey ? [metricKey] : []);
  const title = formatMetricTooltip(keys);
  if (!title) {
    return null;
  }

  return (
    <Tooltip
      title={title}
      arrow
      placement="top"
      enterTouchDelay={0}
      slotProps={{
        tooltip: {
          sx: {
            maxWidth: 320,
            whiteSpace: 'pre-line',
            fontSize: '0.75rem',
            lineHeight: 1.45,
          },
        },
      }}
    >
      <IconButton
        type="button"
        size={size}
        aria-label="Metric definition"
        sx={{
          p: 0.25,
          ml: 0.25,
          color: isDarkMode ? 'grey.500' : 'text.secondary',
          verticalAlign: 'middle',
          '&:hover': {
            color: isDarkMode ? 'grey.300' : 'text.primary',
            bgcolor: 'transparent',
          },
          ...sx,
        }}
        onClick={(event) => event.stopPropagation()}
      >
        <InfoOutlinedIcon sx={{ fontSize: size === 'small' ? '0.95rem' : '1.1rem' }} />
      </IconButton>
    </Tooltip>
  );
};

export default MetricInfoIcon;
