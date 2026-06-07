/**
 * Partial-batch notice: how many games succeeded + link to failure details.
 */

import React from 'react';
import { Alert, Button, Box, Typography } from '@mui/material';
import { normalizeFailedGames } from './FailedGamesList';
import { scrollToBatchSection } from '../../utils/batchReportScroll';

const PartialBatchBanner = ({ batchReport, status }) => {
  if (status !== 'partial') {
    return null;
  }

  const failures = normalizeFailedGames(
    batchReport?.errors || batchReport?.failed_games || []
  );
  if (failures.length === 0) {
    return null;
  }

  const analyzed =
    batchReport?.batch_summary?.games_analyzed
    ?? batchReport?.per_game_results?.length
    ?? 0;
  const total = batchReport?.games_count ?? analyzed + failures.length;
  const coachingNote = batchReport?.coaching_report
    ? 'Coaching below is based on the games that completed successfully.'
    : 'Engine stats below cover the games that completed successfully.';

  return (
    <Box sx={{ py: 0 }}>
      <Alert
        severity="warning"
        variant="outlined"
        action={(
          <Button
            color="inherit"
            size="small"
            onClick={() => scrollToBatchSection('batch-section-failed-games')}
            sx={{ whiteSpace: 'nowrap', fontWeight: 600 }}
          >
            View failed games
          </Button>
        )}
      >
        <Typography variant="body2">
          <strong>
            {analyzed} of {total} games
          </strong>{' '}
          analyzed successfully ({failures.length} failed). {coachingNote}
        </Typography>
      </Alert>
    </Box>
  );
};

export default PartialBatchBanner;
