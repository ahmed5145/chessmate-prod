/**
 * ExecutiveSummary.js — structured coaching summary cards.
 */

import React from 'react';
import {
  Paper,
  List,
  ListItem,
  ListItemText,
  Typography,
} from '@mui/material';
import ReportSectionShell from './ReportSectionShell';
import { splitSummaryBullets } from '../../utils/batchReportText';
import { humanizeGameIdInText } from '../../utils/formatGameLabel';

const summaryTextSx = {
  lineHeight: 1.65,
  wordBreak: 'break-word',
};

const ExecutiveSummary = ({ coaching_report, per_game_results = [] }) => {
  if (!coaching_report?.executive_summary) {
    return null;
  }

  const executiveSummary = coaching_report.executive_summary || '';
  const bullets = splitSummaryBullets(executiveSummary).map((bullet) =>
    humanizeGameIdInText(bullet, per_game_results)
  );
  const humanizedSummary = humanizeGameIdInText(executiveSummary, per_game_results);

  return (
    <ReportSectionShell title="Executive summary">
      <Paper variant="outlined" sx={{ p: { xs: 2, sm: 2.5 } }}>
        {bullets.length > 1 ? (
          <List dense disablePadding>
            {bullets.map((bullet, index) => (
              <ListItem key={`summary-bullet-${index}`} disableGutters sx={{ py: 0.5, alignItems: 'flex-start' }}>
                <Typography component="span" variant="body2" sx={{ mr: 1, mt: 0.15, color: 'primary.main' }}>
                  •
                </Typography>
                <ListItemText
                  primary={bullet}
                  primaryTypographyProps={{ variant: 'body2', sx: summaryTextSx }}
                />
              </ListItem>
            ))}
          </List>
        ) : (
          <Typography variant="body1" sx={summaryTextSx}>
            {humanizedSummary}
          </Typography>
        )}
      </Paper>
    </ReportSectionShell>
  );
};

export default ExecutiveSummary;
