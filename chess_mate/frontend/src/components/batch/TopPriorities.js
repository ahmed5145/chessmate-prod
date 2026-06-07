/**
 * TopPriorities.js — top 3 priorities from the coaching report.
 */

import React from 'react';
import { Box, Typography, Container } from '@mui/material';
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
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 3 }}>
        Top 3 Priorities
      </Typography>

      <Box>
        {priorities.map((priority, index) => (
          <PriorityCard
            key={priority.rank || index}
            priority={priority}
            per_game_results={per_game_results}
          />
        ))}
      </Box>
    </Container>
  );
};

export default TopPriorities;
