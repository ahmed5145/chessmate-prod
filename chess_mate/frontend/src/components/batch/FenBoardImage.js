/**
 * FenBoardImage — static board diagram from FEN (third-party renderer; Lichess /export/fen is unreliable).
 */

import React, { useMemo, useState } from 'react';
import { Box, Typography } from '@mui/material';

/** Use board placement only — full FEN breaks many renderers. */
export const boardFenFromFullFen = (fen) => {
  if (!fen || typeof fen !== 'string') {
    return null;
  }
  const board = fen.trim().split(/\s+/)[0];
  return board || null;
};

export const buildBoardImageUrl = (fen, size = 280) => {
  const boardFen = boardFenFromFullFen(fen);
  if (!boardFen) {
    return null;
  }
  const params = new URLSearchParams({
    fen: boardFen,
    colors: 'lichess-brown',
    size: String(Math.min(Math.max(size, 120), 512))
  });
  return `https://backscattering.de/web-boardimage/board.png?${params.toString()}`;
};

const FenBoardImage = ({ fen, alt = 'Position diagram', size = 280 }) => {
  const src = useMemo(() => buildBoardImageUrl(fen, size), [fen, size]);
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    const board = boardFenFromFullFen(fen);
    return (
      <Box
        sx={{
          width: '100%',
          maxWidth: size,
          minHeight: size * 0.9,
          borderRadius: 1,
          border: '1px dashed',
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          p: 1,
          bgcolor: 'action.hover'
        }}
      >
        <Typography variant="caption" color="text.secondary" align="center">
          {board ? `Position: ${board.slice(0, 32)}…` : 'Board preview unavailable'}
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      component="img"
      src={src}
      alt={alt}
      loading="lazy"
      onError={() => setFailed(true)}
      sx={{
        width: '100%',
        maxWidth: size,
        height: 'auto',
        borderRadius: 1,
        border: '1px solid',
        borderColor: 'divider',
        bgcolor: 'background.paper'
      }}
    />
  );
};

export default FenBoardImage;
