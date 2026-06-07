/**
 * FenBoardImage — inline SVG board from FEN with move arrows.
 * Flips to the player's perspective (Chess.com style) when orientation is black.
 */

import React, { useId, useMemo } from 'react';
import { Box, Typography } from '@mui/material';
import {
  iterateFenPieces,
  LIGHT_SQUARE,
  pieceStyle,
  squareFill,
} from '../../utils/fenBoardSvg';

/** Use board placement only — full FEN breaks many renderers. */
export const boardFenFromFullFen = (fen) => {
  if (!fen || typeof fen !== 'string') {
    return null;
  }
  const board = fen.trim().split(/\s+/)[0];
  return board || null;
};

/** @deprecated External URL kept for tests only — UI renders inline SVG. */
export const buildBoardImageUrl = (fen, size = 280) => {
  const boardFen = boardFenFromFullFen(fen);
  if (!boardFen) {
    return null;
  }
  const params = new URLSearchParams({
    fen: boardFen,
    colors: 'lichess-brown',
    size: String(Math.min(Math.max(size, 120), 512)),
  });
  return `https://backscattering.de/web-boardimage/board.png?${params.toString()}`;
};

const FILE_LABELS = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
const RANK_LABELS = ['1', '2', '3', '4', '5', '6', '7', '8'];

const mapCoords = (file, rank, isBlackView) =>
  isBlackView ? { file: 7 - file, rank: 7 - rank } : { file, rank };

const squareCenterPercent = (square, isBlackView) => {
  let file = square.charCodeAt(0) - 'a'.charCodeAt(0);
  let rank = Number(square[1]) - 1;
  if (isBlackView) {
    file = 7 - file;
    rank = 7 - rank;
  }
  return {
    left: ((file + 0.5) / 8) * 100,
    top: ((7 - rank + 0.5) / 8) * 100,
  };
};

const parseUciSquares = (uci) => {
  if (!uci || typeof uci !== 'string' || uci.length < 4) {
    return null;
  }
  return { from: uci.slice(0, 2), to: uci.slice(2, 4) };
};

const MoveArrow = ({ from, to, color, markerId, isBlackView }) => {
  const start = squareCenterPercent(from, isBlackView);
  const end = squareCenterPercent(to, isBlackView);
  return (
    <svg
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }}
    >
      <defs>
        <marker id={markerId} markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
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
        markerEnd={`url(#${markerId})`}
      />
    </svg>
  );
};

const BoardSvg = ({ boardFen, isBlackView }) => {
  const pieces = useMemo(() => iterateFenPieces(boardFen), [boardFen]);

  return (
    <svg
      width="100%"
      height="100%"
      viewBox="0 0 8 8"
      role="img"
      aria-label="Chess position"
      style={{ display: 'block' }}
    >
      {Array.from({ length: 8 }, (_, rank) =>
        Array.from({ length: 8 }, (_, file) => {
          const display = mapCoords(file, rank, isBlackView);
          return (
            <rect
              key={`sq-${file}-${rank}`}
              x={display.file}
              y={display.rank}
              width={1}
              height={1}
              fill={squareFill(file, rank)}
            />
          );
        })
      )}
      {pieces.map((piece) => {
        const style = pieceStyle(piece.char);
        const display = mapCoords(piece.file, piece.rank, isBlackView);
        const glyph = piece.char === piece.char.toUpperCase()
          ? piece.char.toUpperCase()
          : piece.char.toLowerCase();
        const symbol = {
          K: '♔', Q: '♕', R: '♖', B: '♗', N: '♘', P: '♙',
          k: '♚', q: '♛', r: '♜', b: '♝', n: '♞', p: '♟',
        }[glyph];
        return (
          <text
            key={`${piece.file}-${piece.rank}-${piece.char}`}
            x={display.file + 0.5}
            y={display.rank + 0.78}
            textAnchor="middle"
            fontSize="0.82"
            fontFamily="'Segoe UI Symbol', 'Noto Sans Symbols2', serif"
            fill={style.fill}
            stroke={style.stroke}
            strokeWidth={style.strokeWidth}
            paintOrder="stroke fill"
          >
            {symbol}
          </text>
        );
      })}
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
  const isBlackView = (perspective || orientation) === 'black';
  const boardFen = useMemo(() => boardFenFromFullFen(fen), [fen]);
  const reactId = useId();
  const playedArrow = parseUciSquares(playedMoveUci);
  const bestArrow = parseUciSquares(bestMoveUci);

  if (!boardFen) {
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
          bgcolor: 'action.hover',
        }}
      >
        <Typography variant="caption" color="text.secondary" align="center">
          Board preview unavailable
        </Typography>
      </Box>
    );
  }

  const files = isBlackView ? [...FILE_LABELS].reverse() : FILE_LABELS;
  const ranks = isBlackView ? RANK_LABELS : [...RANK_LABELS].reverse();

  const bestMarkerId = `best-arrow-${reactId.replace(/:/g, '')}`;
  const playedMarkerId = `played-arrow-${reactId.replace(/:/g, '')}`;

  return (
    <Box
      className="fen-board-diagram"
      sx={{ position: 'relative', width: '100%', maxWidth: size }}
      aria-label={alt}
    >
      <Box
        sx={{
          position: 'relative',
          borderRadius: 1,
          border: '1px solid',
          borderColor: 'divider',
          overflow: 'hidden',
          bgcolor: LIGHT_SQUARE,
          aspectRatio: '1 / 1',
          width: '100%',
        }}
      >
        <BoardSvg boardFen={boardFen} isBlackView={isBlackView} />
        {bestArrow ? (
          <MoveArrow {...bestArrow} color="#16a34a" markerId={bestMarkerId} isBlackView={isBlackView} />
        ) : null}
        {playedArrow ? (
          <MoveArrow {...playedArrow} color="#dc2626" markerId={playedMarkerId} isBlackView={isBlackView} />
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
            sx={{
              textAlign: 'center',
              fontSize: '0.65rem',
              color: 'text.secondary',
              fontWeight: 600,
              textShadow: '0 0 2px rgba(255,255,255,0.9)',
            }}
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
            sx={{
              fontSize: '0.65rem',
              color: 'text.secondary',
              fontWeight: 600,
              lineHeight: 1,
              textShadow: '0 0 2px rgba(255,255,255,0.9)',
            }}
          >
            {rank}
          </Typography>
        ))}
      </Box>
    </Box>
  );
};

export default FenBoardImage;
