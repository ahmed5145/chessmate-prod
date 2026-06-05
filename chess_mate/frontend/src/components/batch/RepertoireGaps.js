/**
 * Opening repertoire gaps — lines where the player loses or underperforms.
 */

import React from 'react';
import {
  Alert,
  Box,
  Chip,
  Container,
  List,
  ListItem,
  Typography
} from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { lichessOpeningSearchUrl } from '../../utils/lichessStudyLinks';

const RepertoireGaps = ({ batch_summary }) => {
  const gaps = Array.isArray(batch_summary?.repertoire_gaps)
    ? batch_summary.repertoire_gaps
    : (batch_summary?.opening_insights || []).filter(
        (item) => item?.status === 'struggling' || item?.status === 'needs_work'
      );

  if (gaps.length === 0) {
    return null;
  }

  return (
    <Container maxWidth="lg" sx={{ py: 2 }}>
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>
        Repertoire gaps
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Openings in this batch where your results or opening-phase scores lag — review or simplify these lines.
      </Typography>
      <List dense disablePadding>
        {gaps.map((gap) => (
          <ListItem
            key={`${gap.opening_name}-${gap.player_color}`}
            sx={{
              flexDirection: 'column',
              alignItems: 'flex-start',
              py: 1.5,
              borderLeft: 3,
              borderColor: 'error.main',
              pl: 2,
              mb: 1
            }}
          >
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 0.5 }}>
              <Chip size="small" label={gap.opening_name} color="error" variant="outlined" />
              {gap.player_color && (
                <Chip size="small" label={`as ${gap.player_color}`} variant="outlined" />
              )}
              {gap.record && <Chip size="small" label={gap.record} variant="outlined" />}
            </Box>
            <Typography variant="body2" sx={{ mb: 1 }}>
              {gap.summary || gap.recommendation}
            </Typography>
            <Box
              component="a"
              href={lichessOpeningSearchUrl(gap.opening_name)}
              target="_blank"
              rel="noopener noreferrer"
              sx={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 0.5,
                fontSize: '0.875rem',
                color: 'primary.main',
                textDecoration: 'none',
                '&:hover': { textDecoration: 'underline' }
              }}
            >
              Study on Lichess
              <OpenInNewIcon sx={{ fontSize: 16 }} />
            </Box>
          </ListItem>
        ))}
      </List>
      <Alert severity="info" variant="outlined" sx={{ mt: 1 }}>
        <Typography variant="caption">
          Based on PGN headers and engine opening-phase scores — not a full ECO/sub-line tree yet.
        </Typography>
      </Alert>
    </Container>
  );
};

export default RepertoireGaps;
