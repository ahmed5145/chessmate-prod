import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Box, Button, Typography } from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';

const OpeningGapsGames = ({ gap, batchId = null }) => {
  const lostGames = Array.isArray(gap?.lost_games) ? gap.lost_games : [];

  if (lostGames.length === 0) {
    return null;
  }

  return (
    <Box sx={{ mt: 1, width: '100%' }}>
      {gap.loss_copy ? (
        <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.75 }}>
          {gap.loss_copy}
        </Typography>
      ) : null}
      {lostGames.map((game) => (
        <Box
          key={`${gap.opening_name}-${game.saved_game_id || game.game_id}`}
          sx={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            gap: 1,
            mb: 0.75,
          }}
        >
          <Typography variant="caption" color="text.secondary">
            {game.game_label || game.opponent || `Game ${game.game_id}`}
          </Typography>
          {game.href ? (
            <Button
              size="small"
              variant="text"
              component={RouterLink}
              to={game.href}
              sx={{ textTransform: 'none', fontWeight: 600, minWidth: 0, p: 0 }}
            >
              Review in ChessMate
            </Button>
          ) : null}
          {game.platform_game_url ? (
            <Button
              size="small"
              variant="text"
              href={game.platform_game_url}
              target="_blank"
              rel="noopener noreferrer"
              endIcon={<OpenInNewIcon sx={{ fontSize: 14 }} />}
              sx={{ textTransform: 'none', fontWeight: 600, minWidth: 0, p: 0 }}
            >
              {game.platform ? `Open on ${game.platform}` : 'Open game'}
            </Button>
          ) : null}
        </Box>
      ))}
    </Box>
  );
};

export default OpeningGapsGames;
