import { boardFenFromFullFen } from '../FenBoardImage';
import { iterateFenPieces, squareFill } from '../../../utils/fenBoardSvg';

describe('FenBoardImage helpers', () => {
  it('extracts board-only FEN', () => {
    const full = 'r4rk1/p4p2/5pp1/4pb1P/2q3p1/Q4P2/PPP5/2KR3R w - - 1 22';
    expect(boardFenFromFullFen(full)).toBe('r4rk1/p4p2/5pp1/4pb1P/2q3p1/Q4P2/PPP5/2KR3R');
  });

  it('parses pieces from starting position', () => {
    const pieces = iterateFenPieces('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR');
    expect(pieces).toHaveLength(32);
    expect(pieces.find((p) => p.char === 'K' && p.file === 4 && p.rank === 7)).toBeTruthy();
  });

  it('uses lichess-brown square colors', () => {
    expect(squareFill(0, 0)).toBe('#f0d9b5');
    expect(squareFill(1, 0)).toBe('#b58863');
  });
});
