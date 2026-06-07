/**
 * ExecutiveSummary.js — structured coaching summary cards.
 */

import React from 'react';
import {
  Box,
  Typography,
  Alert,
  Container,
  Paper,
  List,
  ListItem,
  ListItemText
} from '@mui/material';

const splitSummaryBullets = (text) => {
  if (!text || typeof text !== 'string') {
    return [];
  }
  return text
    .split(/\n+|(?<=[.!?])\s+/)
    .map((line) => line.trim())
    .filter((line) => line.length > 12)
    .slice(0, 6);
};

const ExecutiveSummary = ({ coaching_report }) => {
  if (!coaching_report) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="info" sx={{ mb: 4 }}>
          <Typography variant="body2">
            Coaching narrative unavailable for this batch — analysis data shown below.
          </Typography>
        </Alert>
      </Container>
    );
  }

  const executiveSummary = coaching_report.executive_summary || '';
  const bullets = splitSummaryBullets(executiveSummary);

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
        Executive summary
      </Typography>
      <Paper variant="outlined" sx={{ p: 2.5 }}>
        {bullets.length > 1 ? (
          <List dense disablePadding>
            {bullets.map((bullet, index) => (
              <ListItem key={`summary-bullet-${index}`} disableGutters sx={{ py: 0.5 }}>
                <ListItemText
                  primary={bullet}
                  primaryTypographyProps={{ variant: 'body2' }}
                />
              </ListItem>
            ))}
          </List>
        ) : (
          <Typography variant="body1" sx={{ lineHeight: 1.7 }}>
            {executiveSummary}
          </Typography>
        )}
        {coaching_report.one_thing_to_do_today && (
          <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
              Do today
            </Typography>
            <Typography variant="body2">{coaching_report.one_thing_to_do_today}</Typography>
          </Box>
        )}
      </Paper>
    </Container>
  );
};

export default ExecutiveSummary;
