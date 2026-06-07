/**
 * Additional Lichess drill links not already shown in the Practice next strip.
 */

import React from 'react';
import {
  Box,
  Chip,
  Grid,
  Paper,
  Typography
} from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import SportsEsportsIcon from '@mui/icons-material/SportsEsports';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import FlagIcon from '@mui/icons-material/Flag';
import ReportSectionShell from './ReportSectionShell';
import { collectStudyLinksFromBatchSummary } from '../../utils/lichessStudyLinks';

const KIND_META = {
  puzzle: { icon: SportsEsportsIcon, color: 'primary', label: 'Tactics' },
  opening: { icon: MenuBookIcon, color: 'secondary', label: 'Opening' },
  endgame: { icon: FlagIcon, color: 'warning', label: 'Endgame' }
};

const StudyDrillLinks = ({ batch_summary, links: linksProp }) => {
  const links = linksProp || collectStudyLinksFromBatchSummary(batch_summary);

  if (links.length === 0) {
    return null;
  }

  return (
    <ReportSectionShell
      title="More suggested drills"
      subtitle="Extra practice matched to patterns from this batch — opens Lichess in a new tab."
    >
      <Grid container spacing={1.5}>
        {links.map((link) => {
          const meta = KIND_META[link.kind] || KIND_META.puzzle;
          const Icon = meta.icon;
          return (
            <Grid item xs={12} sm={6} md={4} key={`${link.kind}-${link.url}`}>
              <Paper
                component="a"
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                variant="outlined"
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1.5,
                  p: 1.5,
                  textDecoration: 'none',
                  color: 'inherit',
                  height: '100%',
                  transition: 'border-color 0.15s, box-shadow 0.15s',
                  '&:hover': {
                    borderColor: `${meta.color}.main`,
                    boxShadow: 1
                  }
                }}
              >
                <Box
                  sx={{
                    p: 1,
                    borderRadius: 1,
                    bgcolor: 'action.hover',
                    color: `${meta.color}.main`,
                    display: 'flex'
                  }}
                >
                  <Icon fontSize="small" />
                </Box>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Chip size="small" label={meta.label} color={meta.color} sx={{ mb: 0.5 }} />
                  <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.3 }}>
                    {link.label}
                  </Typography>
                </Box>
                <OpenInNewIcon fontSize="small" color="action" />
              </Paper>
            </Grid>
          );
        })}
      </Grid>
    </ReportSectionShell>
  );
};

export default StudyDrillLinks;
