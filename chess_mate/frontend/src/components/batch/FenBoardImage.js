/**
 * FenBoardImage — static board diagram from FEN with move arrows.
 * Board stays upright (white at bottom); `orientation` / `perspective` only flips a–h / 1–8 labels.
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

const FILE_LABELS = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
const RANK_LABELS = ['1', '2', '3', '4', '5', '6', '7', '8'];

const squareCenterPercent = (square, orientation) => {
  const file = square.charCodeAt(0) - 'a'.charCodeAt(0);
  const rank = Number(square[1]) - 1;
  const orientedFile = orientation === 'black' ? 7 - file : file;
  const orientedRank = orientation === 'black' ? rank : 7 - rank;
  return {
    left: ((orientedFile + 0.5) / 8) * 100,
    top: ((orientedRank + 0.5) / 8) * 100,
  };
};

const parseUciSquares = (uci) => {
  if (!uci || typeof uci !== 'string' || uci.length < 4) {
    return null;
  }
  return { from: uci.slice(0, 2), to: uci.slice(2, 4) };
};

const MoveArrow = ({ from, to, orientation, color }) => {
  const start = squareCenterPercent(from, orientation);
  const end = squareCenterPercent(to, orientation);
  return (
    <svg
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }}
    >
      <defs>
        <marker id="arrowhead" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
          <polygon points="0 0, 6 3, 0 6" fill={color} />
        </marker>
      </defs>
      <line
        x1={start.left}
        y1={start.top}
        x2={end.left}
        y2={end.top}
        stroke={color}
        strokeWidth="1.8"
        strokeOpacity="0.75"
        markerEnd="url(#arrowhead)"
      />
    </svg>
  );
};

const FenBoardImage = ({
  fen,
  alt = 'Position diagram',
  size = 280,
  orientation = 'white',
  perspective,
  playedMoveUci = null,
  bestMoveUci = null,
}) => {
  // Board stays standard (white at bottom); perspective only affects a–h / 1–8 labels.
  const labelPerspective = (perspective || orientation) === 'black' ? 'black' : 'white';
  const src = useMemo(() => buildBoardImageUrl(fen, size), [fen, size]);
  const [failed, setFailed] = useState(false);
  const playedArrow = parseUciSquares(playedMoveUci);
  const bestArrow = parseUciSquares(bestMoveUci);

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

  const files = labelPerspective === 'black' ? [...FILE_LABELS].reverse() : FILE_LABELS;
  const ranks = labelPerspective === 'black' ? RANK_LABELS : [...RANK_LABELS].reverse();

  return (
    <Box sx={{ position: 'relative', width: '100%', maxWidth: size }}>
      <Box
        sx={{
          position: 'relative',
          borderRadius: 1,
          border: '1px solid',
          borderColor: 'divider',
          overflow: 'hidden',
          bgcolor: 'background.paper',
        }}
      >
        <Box
          component="img"
          src={src}
          alt={alt}
          loading="lazy"
          onError={() => setFailed(true)}
          sx={{
            width: '100%',
            height: 'auto',
            display: 'block',
          }}
        />
        {bestArrow ? (
          <MoveArrow {...bestArrow} orientation="white" color="#22c55e" />
        ) : null}
        {playedArrow ? (
          <MoveArrow {...playedArrow} orientation="white" color="#ef4444" />
        ) : null}
      </Box>
      <Box
        sx={{
          position: 'absolute',
          bottom: 2,
          left: 0,
          right: 0,
          display: 'grid',
          gridTemplateColumns: 'repeat(8, 1fr)',
          px: 0.5,
          pointerEvents: 'none',
        }}
      >
        {files.map((file) => (
          <Typography
            key={file}
            variant="caption"
            sx={{ textAlign: 'center', fontSize: '0.65rem', color: 'text.secondary', fontWeight: 600 }}
          >
            {file}
          </Typography>
        ))}
      </Box>
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          bottom: 0,
          left: 2,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          py: 0.5,
          pointerEvents: 'none',
        }}
      >
        {ranks.map((rank) => (
          <Typography
            key={rank}
            variant="caption"
            sx={{ fontSize: '0.65rem', color: 'text.secondary', fontWeight: 600, lineHeight: 1 }}
          >
            {rank}
          </Typography>
        ))}
      </Box>
    </Box>
  );
};

export default FenBoardImage;
