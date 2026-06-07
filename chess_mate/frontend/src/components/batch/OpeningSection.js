/**
 * Unified openings section: flagged repertoire gaps + per-game matchup rows.
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
import OpeningRecommendationText from './OpeningRecommendationText';
import LichessActionButton from './LichessActionButton';
import GameExampleActions from './GameExampleActions';
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
            re-run batch analysis.
          </Typography>
        </Alert>
      </ReportSectionShell>
    );
  }

  return (
    <ReportSectionShell
      title="Openings"
      subtitle="Flagged lines need study; below that, every game’s opening result in this batch."
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

      <ReportSubsection title="Game-by-game results">
        <List dense disablePadding>
          {openingInsights.map((item) => (
            <ListItem
              key={item.game_id || `${item.opening_name}-${item.eco_code || 'x'}-${item.player_color || 'x'}`}
              sx={{
                flexDirection: 'column',
                alignItems: 'flex-start',
                py: 1.5,
                borderLeft: 3,
                borderColor:
                  item.status === 'struggling' || item.status === 'needs_work'
                    ? 'warning.main'
                    : item.status === 'strong'
                      ? 'success.main'
                      : 'divider',
                pl: 2,
                mb: 1,
              }}
            >
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.25 }}>
                {item.opening_name}
                {item.eco_code ? ` · ECO ${item.eco_code}` : ''}
                {item.record ? ` · ${item.record}` : ''}
              </Typography>
              {item.avg_opening_score != null ? (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                  Opening phase {Math.round(item.avg_opening_score * 100)}% move match
                </Typography>
              ) : null}
              {item.game_label ? (
                <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5 }}>
                  {item.game_label}
                </Typography>
              ) : null}
              {item.recommendation ? <OpeningRecommendationText item={item} /> : null}
              <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
                <LichessActionButton
                  label="Study on Lichess"
                  url={lichessOpeningSearchUrl(item.opening_name, {
                    ecoCode: item.eco_code,
                    playerColor: item.player_color,
                  })}
                  kind="opening"
                />
                {item.game_id ? (
                  <GameExampleActions perGameResults={per_game_results} gameId={item.game_id} />
                ) : null}
              </Box>
            </ListItem>
          ))}
        </List>
      </ReportSubsection>
    </ReportSectionShell>
  );
};

export default OpeningSection;
