import {
  normalizeSingleGameMoves,
  findMoveIndexByNumber,
  pickEvalSeries,
} from '../singleGameMoves';

describe('singleGameMoves', () => {
  it('normalizes move payload for board UI', () => {
    const moves = normalizeSingleGameMoves([
      {
        move_number: 3,
        san: 'Nf3',
        move: 'g1f3',
        position: 'fen-here',
        eval_after: 0.4,
        classification: 'good',
        is_white: true,
      },
    ]);
    expect(moves[0].san).toBe('Nf3');
    expect(moves[0].fen).toBe('fen-here');
    expect(moves[0].evalAfter).toBe(0.4);
  });

  it('finds move index by move number', () => {
    const moves = normalizeSingleGameMoves([
      { move_number: 1, san: 'e4' },
      { move_number: 2, san: 'e5' },
    ]);
    expect(findMoveIndexByNumber(moves, 2)).toBe(1);
  });

  it('builds eval series', () => {
    const moves = normalizeSingleGameMoves([
      { move_number: 1, eval_after: 0.1 },
      { move_number: 2, eval_after: -0.5 },
    ]);
    expect(pickEvalSeries(moves)).toEqual([
      { label: 1, value: 0.1 },
      { label: 2, value: -0.5 },
    ]);
  });
});
