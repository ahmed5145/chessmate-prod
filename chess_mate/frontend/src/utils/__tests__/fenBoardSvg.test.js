import { iterateFenPieces, pieceStyle } from '../fenBoardSvg';

describe('fenBoardSvg', () => {
  it('iterates all pieces in a compact FEN row', () => {
    const pieces = iterateFenPieces('r3k2r/8/8/8/3P4/8/PPP1PPPP/RNBQKBNR');
    const pawn = pieces.find((p) => p.char === 'P' && p.file === 3 && p.rank === 4);
    expect(pawn).toEqual({ char: 'P', file: 3, rank: 4 });
  });

  it('styles white and black pieces differently', () => {
    expect(pieceStyle('Q').fill).toBe('#ffffff');
    expect(pieceStyle('q').fill).toBe('#1a1a1a');
  });
});
