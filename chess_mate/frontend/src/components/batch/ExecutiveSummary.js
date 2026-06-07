/**
 * ExecutiveSummary.js — structured coaching summary cards.
 */

import React from 'react';
import {
  Box,
  Paper,
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
          <Box
            component="ul"
            sx={{
              m: 0,
              pl: 2.5,
              listStyleType: 'disc',
              '& > li::marker': { color: 'text.secondary' },
            }}
          >
            {bullets.map((bullet, index) => (
              <Box component="li" key={`summary-bullet-${index}`} sx={{ py: 0.4 }}>
                <Typography variant="body2" sx={summaryTextSx}>
                  {bullet}
                </Typography>
              </Box>
            ))}
          </Box>
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
