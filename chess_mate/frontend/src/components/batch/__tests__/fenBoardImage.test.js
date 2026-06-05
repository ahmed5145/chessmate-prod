import { boardFenFromFullFen, buildBoardImageUrl } from '../FenBoardImage';

describe('FenBoardImage helpers', () => {
  it('extracts board-only FEN', () => {
    const full = 'r4rk1/p4p2/5pp1/4pb1P/2q3p1/Q4P2/PPP5/2KR3R w - - 1 22';
    expect(boardFenFromFullFen(full)).toBe('r4rk1/p4p2/5pp1/4pb1P/2q3p1/Q4P2/PPP5/2KR3R');
  });

  it('builds backscattering board URL', () => {
    const url = buildBoardImageUrl('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1', 200);
    expect(url).toContain('backscattering.de/web-boardimage/board.png');
    expect(url).toContain('fen=');
    expect(url).not.toContain('lichess.org/export/fen');
  });
});
