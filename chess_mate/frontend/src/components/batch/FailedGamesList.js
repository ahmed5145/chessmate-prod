import React from 'react';
import PropTypes from 'prop-types';
import { Alert, List, ListItem, ListItemText, Typography } from '@mui/material';

/**
 * Normalize API failed_games / errors into { game_id, message } rows.
 */
export const normalizeFailedGames = (raw) => {
  if (!Array.isArray(raw) || raw.length === 0) {
    return [];
  }

  return raw.map((item, index) => {
    if (typeof item === 'string') {
      return { game_id: item, message: 'Analysis failed' };
    }
    if (!item || typeof item !== 'object') {
      return { game_id: `game_${index}`, message: 'Analysis failed' };
    }
    return {
      game_id: item.game_id || item.id || item.gameId || `game_${index}`,
      message: item.message || item.error || 'Analysis failed',
    };
  });
};

const formatGameLabel = (gameId) => {
  const id = String(gameId || '');
  const indexMatch = id.match(/^game_(\d+)$/);
  if (indexMatch) {
    const n = Number(indexMatch[1]) + 1;
    return `Game ${n} (${id})`;
  }
  return id || 'Unknown game';
};

const FailedGamesList = ({ failures = [] }) => {
  const rows = normalizeFailedGames(failures);
  if (rows.length === 0) {
    return null;
  }

  return (
    <Alert severity="error" sx={{ mt: 2, mb: 2 }}>
      <Typography variant="subtitle2" gutterBottom>
        Failed games ({rows.length})
      </Typography>
      <List dense disablePadding>
        {rows.map((row) => (
          <ListItem key={row.game_id} disableGutters sx={{ py: 0.25 }}>
            <ListItemText
              primary={formatGameLabel(row.game_id)}
              secondary={row.message}
              primaryTypographyProps={{ variant: 'body2', fontWeight: 600 }}
              secondaryTypographyProps={{ variant: 'body2' }}
            />
          </ListItem>
        ))}
      </List>
    </Alert>
  );
};

FailedGamesList.propTypes = {
  failures: PropTypes.arrayOf(
    PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.shape({
        game_id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
        message: PropTypes.string,
        error: PropTypes.string,
      }),
    ])
  ),
};

export default FailedGamesList;
