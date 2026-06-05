/**
 * Lichess drill links derived from batch weaknesses / openings / endgames.
 */

import React from 'react';
import { Box, Button, Chip, Container, Typography } from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { collectStudyLinksFromBatchSummary } from '../../utils/lichessStudyLinks';

const StudyDrillLinks = ({ batch_summary }) => {
  const links = collectStudyLinksFromBatchSummary(batch_summary);

  if (links.length === 0) {
    return null;
  }

  return (
    <Container maxWidth="lg" sx={{ py: 2 }}>
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>
        Suggested drills
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        One-click Lichess practice matched to patterns from this batch (opens in a new tab).
      </Typography>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
        {links.map((link) => (
          <Button
            key={`${link.kind}-${link.url}`}
            component="a"
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
            variant="outlined"
            size="small"
            endIcon={<OpenInNewIcon fontSize="small" />}
          >
            {link.label}
          </Button>
        ))}
      </Box>
      <Box sx={{ mt: 1.5, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        <Chip size="small" label="Puzzles" variant="outlined" />
        <Chip size="small" label="Openings" variant="outlined" />
        <Chip size="small" label="Endgames" variant="outlined" />
      </Box>
    </Container>
  );
};

export default StudyDrillLinks;
