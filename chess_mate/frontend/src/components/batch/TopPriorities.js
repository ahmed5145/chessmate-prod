/**
 * TopPriorities.js — top 3 priorities from the coaching report.
 */

import React from 'react';
import { Box } from '@mui/material';
import ReportSectionShell from './ReportSectionShell';
import PriorityCard from './PriorityCard';

const TopPriorities = ({ coaching_report, per_game_results = [] }) => {
  if (
    !coaching_report?.top_3_priorities ||
    !Array.isArray(coaching_report.top_3_priorities) ||
    coaching_report.top_3_priorities.length === 0
  ) {
    return null;
  }

  const priorities = coaching_report.top_3_priorities;

  return (
    <ReportSectionShell title="Top 3 priorities">
      <Box>
        {priorities.map((priority, index) => (
          <PriorityCard
            key={priority.rank || index}
            priority={priority}
            per_game_results={per_game_results}
            showLichessLink={Number(priority.rank) !== 1}
          />
        ))}
      </Box>
    </ReportSectionShell>
  );
};

export default TopPriorities;
