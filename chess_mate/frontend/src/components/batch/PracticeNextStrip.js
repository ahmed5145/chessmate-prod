/**
 * Consolidated "practice next" strip — priority #1 drill + top batch Lichess links.
 */

import React from 'react';
import { Box, Paper, Typography } from '@mui/material';
import SportsEsportsIcon from '@mui/icons-material/SportsEsports';
import LichessActionButton from './LichessActionButton';

const PracticeNextStrip = ({ links = [] }) => {
  if (!links.length) {
    return null;
  }

  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        bgcolor: 'rgba(99, 102, 241, 0.06)',
        borderColor: 'rgba(99, 102, 241, 0.35)',
      }}
    >
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mb: 1.5 }}>
        <SportsEsportsIcon color="primary" fontSize="small" />
        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
          Practice next
        </Typography>
      </Box>

      <Box sx={{ display: 'grid', gap: 1.5 }}>
        {links.map((link) => (
          <Box
            key={`${link.source}-${link.url}`}
            sx={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 1,
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="body2" sx={{ fontWeight: 700, lineHeight: 1.35 }}>
                {link.headline || link.label}
              </Typography>
              {link.description ? (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.25 }}>
                  {link.description}
                </Typography>
              ) : null}
            </Box>
            <LichessActionButton
              label={link.label}
              url={link.url}
              kind={link.kind}
            />
          </Box>
        ))}
      </Box>
    </Paper>
  );
};

export default PracticeNextStrip;
