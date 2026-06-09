import React, { useEffect, useState } from 'react';
import { Link as RouterLink, useParams } from 'react-router-dom';
import { Alert, Box, Button, Container, Paper, Typography } from '@mui/material';
import FenBoardImage from '../batch/FenBoardImage';
import EngineMetaNote from './EngineMetaNote';
import { getPublicGameMoment } from '../../services/gameAnalysisService';
import { buildRegisterHref, MARKETING_SOURCES } from '../../utils/marketingLinks';
import { usePageMeta } from '../../utils/pageMeta';

const SharedGameMomentPage = () => {
  const { shareToken } = useParams();
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const data = await getPublicGameMoment(shareToken);
        if (active) {
          setPayload(data);
          setError(null);
        }
      } catch (loadError) {
        if (active) {
          setError(loadError?.detail || loadError?.message || 'Shared moment not found.');
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    if (shareToken) {
      load();
    } else {
      setError('Invalid share link.');
      setLoading(false);
    }

    return () => {
      active = false;
    };
  }, [shareToken]);

  const moment = payload?.moment || {};
  const context = payload?.game_context || {};
  const coaching = payload?.coaching || {};
  const shareTitle = coaching.takeaway || 'Critical moment from a ChessMate deep review';
  const shareDescriptionParts = [
    moment.move_number ? `Move ${moment.move_number}` : null,
    moment.eval_swing != null ? `Eval swing ${moment.eval_swing}` : null,
    context.opening_name ? context.opening_name : null,
    context.result ? `Result ${context.result}` : null,
    coaching.do_today ? `Practice: ${coaching.do_today}` : null,
  ].filter(Boolean);
  const shareDescription = shareDescriptionParts.length
    ? shareDescriptionParts.join(' · ')
    : 'See a turning point from a ChessMate depth-20 review — get your own batch coach report.';

  usePageMeta({
    title: payload ? shareTitle : 'Shared chess moment',
    description: payload ? shareDescription : 'See a turning point from a ChessMate depth-20 review.',
    path: shareToken ? `/share/game-moment/${shareToken}` : '/share/game-moment',
    type: 'article',
    twitterCard: 'summary',
  });

  if (loading) {
    return (
      <Container maxWidth="md" sx={{ py: 6 }}>
        <Typography>Loading shared moment…</Typography>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="md" sx={{ py: 6 }}>
        <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
        <Button component={RouterLink} to="/" variant="outlined">
          Back to home
        </Button>
      </Container>
    );
  }

  const registerHref = buildRegisterHref(MARKETING_SOURCES.EXAMPLE_PAGE);

  const metaParts = [
    context.opening_name ? `${context.opening_name}${context.eco ? ` (${context.eco})` : ''}` : null,
    moment.move_number ? `Move ${moment.move_number}` : null,
    context.result ? `Result ${context.result}` : null,
  ].filter(Boolean);

  return (
    <Box sx={{ minHeight: '100vh', py: 4, bgcolor: 'background.default' }}>
      <Container maxWidth="md">
        <Paper sx={{ p: { xs: 2, sm: 3 }, mb: 3 }}>
          <Typography variant="overline" color="primary">
            Shared turning point
          </Typography>
          <Typography variant="h5" sx={{ fontWeight: 800, mt: 0.5, mb: 1 }}>
            {coaching.takeaway || 'Critical moment from a ChessMate deep review'}
          </Typography>
          {metaParts.length ? (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {metaParts.join(' · ')}
            </Typography>
          ) : null}
          <EngineMetaNote engineMeta={payload?.engine_meta} />
          {moment.fen ? (
            <Box sx={{ maxWidth: 360, mx: 'auto', mb: 2 }}>
              <FenBoardImage
                fen={moment.fen}
                orientation={context.player_color === 'black' ? 'black' : 'white'}
                bestMoveUci={moment.best_move_uci}
              />
            </Box>
          ) : null}
          {moment.played_move || moment.best_move ? (
            <Typography variant="body2" sx={{ mb: 2 }}>
              Played {moment.played_move || '—'}
              {moment.best_move ? ` · Engine best ${moment.best_move}` : ''}
            </Typography>
          ) : null}
          {coaching.do_today ? (
            <Alert severity="info" sx={{ mb: 2 }}>
              <strong>Do today:</strong> {coaching.do_today}
            </Alert>
          ) : null}
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            <Button
              component={RouterLink}
              to={registerHref}
              variant="contained"
              sx={{ textTransform: 'none', fontWeight: 600 }}
            >
              Get your own deep reviews
            </Button>
            <Button component={RouterLink} to="/" variant="outlined" sx={{ textTransform: 'none' }}>
              Back to home
            </Button>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
};

export default SharedGameMomentPage;
