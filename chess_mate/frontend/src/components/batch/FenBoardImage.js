/**
 * FenBoardImage — static board diagram from a FEN (Lichess export, no extra deps).
 */

import React from 'react';
import { Box } from '@mui/material';

const buildLichessFenUrl = (fen, size = 280) => {
  if (!fen || typeof fen !== 'string') {
    return null;
  }
  const encoded = encodeURIComponent(fen.trim());
  return `https://lichess1.org/export/fen/${encoded}?theme=brown&piece=cburnett&size=${size}`;
};

const FenBoardImage = ({ fen, alt = 'Position diagram', size = 280 }) => {
  const src = buildLichessFenUrl(fen, size);
  if (!src) {
    return null;
  }

  return (
    <Box
      component="img"
      src={src}
      alt={alt}
      loading="lazy"
      sx={{
        width: '100%',
        maxWidth: size,
        borderRadius: 1,
        border: '1px solid',
        borderColor: 'divider',
        bgcolor: 'background.paper'
      }}
    />
  );
};

export default FenBoardImage;
