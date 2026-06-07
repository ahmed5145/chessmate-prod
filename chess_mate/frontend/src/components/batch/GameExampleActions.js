import React from 'react';
import { Box, Button } from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import {
  getGamePlatformLabel,
  getGamePlatformUrl,
  scrollToBatchGame,
} from '../../utils/batchGameLinks';

const GameExampleActions = ({ perGameResults, gameId, moveNumber }) => {
  const platformUrl = getGamePlatformUrl(perGameResults, gameId);
  const platformLabel = getGamePlatformLabel(perGameResults, gameId);

  return (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
      {platformUrl ? (
        <Button
          size="small"
          variant="outlined"
          href={platformUrl}
          target="_blank"
          rel="noopener noreferrer"
          endIcon={<OpenInNewIcon fontSize="small" />}
          sx={{ textTransform: 'none', fontWeight: 600 }}
        >
          View on {platformLabel}
        </Button>
      ) : null}
      {gameId ? (
        <Button
          size="small"
          variant="text"
          onClick={() => scrollToBatchGame(gameId)}
          sx={{ textTransform: 'none', fontWeight: 600 }}
        >
          {moveNumber ? `See move ${moveNumber} in report` : 'See in game breakdown'}
        </Button>
      ) : null}
    </Box>
  );
};

export default GameExampleActions;
