import React from 'react';
import { Box, Typography } from '@mui/material';

export const Sparkline = ({ values = [] }) => {
  if (!Array.isArray(values) || values.length < 2) {
    return null;
  }

  const width = 72;
  const height = 20;
  const max = Math.max(...values, 0.01);
  const points = values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * width;
      const y = height - (Number(value) / max) * height;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <svg width={width} height={height} aria-hidden="true">
      <polyline
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        points={points}
      />
    </svg>
  );
};

const MomentTimelineStrip = ({ timeline, variant = 'default', sx = {} }) => {
  if (!timeline?.show) {
    return null;
  }

  const monthsSuffix = timeline.months_label ? ` (${timeline.months_label})` : '';
  const trendSuffix = timeline.trend_copy ? ` · ${timeline.trend_copy}` : '';

  if (variant === 'tailwind') {
    return (
      <p className="mt-2 text-xs text-indigo-600 dark:text-indigo-300/90">
        {timeline.headline}
        {monthsSuffix}
        {trendSuffix}
      </p>
    );
  }

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        mt: 1,
        color: 'text.secondary',
        ...sx,
      }}
    >
      <Typography variant="caption" sx={{ fontStyle: 'italic' }}>
        {timeline.headline}
        {monthsSuffix}
        {trendSuffix}
      </Typography>
      <Sparkline values={timeline.sparkline} />
    </Box>
  );
};

export default MomentTimelineStrip;
