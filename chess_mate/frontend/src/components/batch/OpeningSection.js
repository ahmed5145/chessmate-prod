/**
 * Unified openings section: flagged repertoire gaps + per-game table.
 */

import React from 'react';
import {
  Alert,
  Box,
  Button,
  List,
  ListItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
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

const formatResultLabel = (record) => {
  const match = String(record || '').match(/(\d+)W-(\d+)L/);
  if (!match) {
    return '—';
  }
  const wins = Number(match[1]);
  const losses = Number(match[2]);
  if (wins === 1 && losses === 0) {
    return 'W';
  }
  if (wins === 0 && losses === 1) {
    return 'L';
  }
  return 'D';
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
      subtitle="Flagged lines need study; the table below lists every game’s opening in this batch."
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
        <TableContainer sx={{ overflowX: 'auto', border: 1, borderColor: 'divider', borderRadius: 1 }}>
          <Table size="small" aria-label="Opening results by game">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>Game</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Opening</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>ECO</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Color</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Result</TableCell>
                <TableCell sx={{ fontWeight: 700 }} align="right">
                  Practice
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {openingInsights.map((item) => (
                <TableRow
                  key={item.game_id || `${item.opening_name}-${item.eco_code || 'x'}-${item.player_color || 'x'}`}
                  sx={{
                    '&:last-child td': { borderBottom: 0 },
                    bgcolor:
                      item.status === 'struggling' || item.status === 'needs_work'
                        ? 'rgba(255, 152, 0, 0.06)'
                        : item.status === 'strong'
                          ? 'rgba(76, 175, 80, 0.05)'
                          : 'inherit',
                  }}
                >
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    {item.game_label || '—'}
                  </TableCell>
                  <TableCell sx={{ minWidth: 160, maxWidth: 280, wordBreak: 'break-word' }}>
                    {item.recommendation ? (
                      <OpeningRecommendationText item={item} />
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        {item.opening_name}
                        {item.eco_code ? ` (${item.eco_code})` : ''}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>{item.eco_code || '—'}</TableCell>
                  <TableCell sx={{ textTransform: 'capitalize' }}>{item.player_color || '—'}</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>{formatResultLabel(item.record)}</TableCell>
                  <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                    <Box sx={{ display: 'inline-flex', flexWrap: 'wrap', gap: 0.75, justifyContent: 'flex-end' }}>
                      <LichessActionButton
                        label="Study"
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
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </ReportSubsection>
    </ReportSectionShell>
  );
};

export default OpeningSection;
