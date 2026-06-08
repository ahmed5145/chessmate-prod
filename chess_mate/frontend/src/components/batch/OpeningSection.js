/**
 * Openings section: flagged repertoire gaps from batch opening data.
 */

import React from 'react';
import {
  Alert,
  Box,
  Button,
  List,
  ListItem,
  Typography,
} from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import ReportSectionShell, { ReportSubsection } from './ReportSectionShell';
import LichessActionButton from './LichessActionButton';
import { lichessOpeningSearchUrl } from '../../utils/lichessStudyLinks';
import {
  resolveOpeningInsights,
  resolveRepertoireGaps,
} from '../../utils/openingInsights';

const findExampleGame = (gap, perGameResults) => {
  if (!Array.isArray(perGameResults)) {
    return null;
  }
  return perGameResults.find(
    (game) =>
      (game.opening_name === gap.opening_name
        || String(game.opening_name || '').startsWith(`${gap.opening_name}:`))
      && game.player_color === gap.player_color
      && game.platform_game_url
  );
};

const OpeningSection = ({ batch_summary, per_game_results = [] }) => {
  const openingInsights = resolveOpeningInsights(batch_summary, per_game_results);
  const gaps = resolveRepertoireGaps(batch_summary, per_game_results);

  if (openingInsights.length === 0) {
    return (
      <ReportSectionShell title="Openings" subtitle="Opening data from games in this batch.">
        <Alert severity="info" variant="outlined">
          <Typography variant="body2">
            No recognizable opening data in this batch. Import games with ECO or opening tags, then
            re-run Batch Coach to refresh opening insights.
          </Typography>
        </Alert>
      </ReportSectionShell>
    );
  }

  return (
    <ReportSectionShell
      title="Openings"
      subtitle="Flagged lines need study in your recent games."
      showStatusHint
    >
      {gaps.length > 0 ? (
        <ReportSubsection title="Lines to review">
          <List dense disablePadding>
            {gaps.map((gap) => {
              const linkedGame = findExampleGame(gap, per_game_results);
              return (
                <ListItem
                  key={`gap-${gap.opening_name}-${gap.player_color}`}
                  sx={{
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    py: 1.5,
                    borderLeft: 3,
                    borderColor: 'error.main',
                    pl: 2,
                    mb: 1,
                    bgcolor: 'background.paper',
                  }}
                >
                  <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
                    {gap.opening_name}
                    {gap.eco_code ? ` · ECO ${gap.eco_code}` : ''}
                    {gap.player_color ? ` · as ${gap.player_color}` : ''}
                    {gap.record ? ` · ${gap.record}` : ''}
                  </Typography>
                  <Typography variant="body2" sx={{ mb: 1 }}>
                    {gap.summary || (
                      <>
                        Review <strong>{gap.opening_name}</strong> as {gap.player_color || 'your color'}.
                      </>
                    )}
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
                    <LichessActionButton
                      label="Study on Lichess"
                      url={lichessOpeningSearchUrl(gap.opening_name, {
                        ecoCode: gap.eco_code,
                        playerColor: gap.player_color,
                      })}
                      kind="opening"
                    />
                    {linkedGame?.platform_game_url ? (
                      <Button
                        size="small"
                        variant="outlined"
                        href={linkedGame.platform_game_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        endIcon={<OpenInNewIcon fontSize="small" />}
                        sx={{ textTransform: 'none', fontWeight: 600 }}
                      >
                        View game on {linkedGame.platform || 'platform'}
                      </Button>
                    ) : null}
                  </Box>
                </ListItem>
              );
            })}
          </List>
        </ReportSubsection>
      ) : (
        <Alert severity="success" variant="outlined" sx={{ mb: 3 }}>
          <Typography variant="body2">
            No major repertoire gaps this batch — opening scores look manageable overall.
          </Typography>
        </Alert>
      )}
    </ReportSectionShell>
  );
};

export default OpeningSection;
