/**
 * Local SVG chess board from FEN — no external image API (avoids rate limits / CORS in PDF).
 */

export const LIGHT_SQUARE = '#f0d9b5';
export const DARK_SQUARE = '#b58863';

const PIECE_GLYPH = {
  K: '♔',
  Q: '♕',
  R: '♖',
  B: '♗',
  N: '♘',
  P: '♙',
  k: '♚',
  q: '♛',
  r: '♜',
  b: '♝',
  n: '♞',
  p: '♟',
};

export const iterateFenPieces = (boardFen) => {
  if (!boardFen || typeof boardFen !== 'string') {
    return [];
  }

  const pieces = [];
  const rows = boardFen.trim().split('/');

  rows.forEach((row, rankIndex) => {
    let fileIndex = 0;
    for (const char of row) {
      if (char >= '1' && char <= '8') {
        fileIndex += Number(char);
        continue;
      }
      if (PIECE_GLYPH[char]) {
        pieces.push({ char, file: fileIndex, rank: rankIndex });
        fileIndex += 1;
      }
    }
  });

  return pieces;
};

export const pieceStyle = (char) => {
  const isWhite = char === char.toUpperCase();
  return {
    fill: isWhite ? '#ffffff' : '#1a1a1a',
    stroke: isWhite ? '#4b5563' : '#f9fafb',
    strokeWidth: 0.04,
  };
};

export const squareFill = (file, rank) => ((file + rank) % 2 === 0 ? LIGHT_SQUARE : DARK_SQUARE);
