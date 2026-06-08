import {
  alignMovesWithBatchContext,
  alignMomentsWithBatchContext,
  hasClassificationDisagreement,
} from '../singleGameBatchAlign';

describe('singleGameBatchAlign', () => {
  const batchContext = {
    linked_moment: {
      move_number: 18,
      type: 'blunder',
      fen: 'fen-from-batch',
      played_move: 'Qh5',
      best_move: 'O-O',
      played_move_uci: 'd1h5',
      best_move_uci: 'e1g1',
    },
  };

  it('merges linked batch moment into normalized moves', () => {
    const moves = [
      { moveNumber: 17, san: 'Bc4', fen: 'a', classification: 'good' },
      { moveNumber: 18, san: 'Qh4', fen: 'b', classification: 'mistake', bestMoveUci: '' },
    ];

    const aligned = alignMovesWithBatchContext(moves, batchContext);
    expect(aligned[1].fen).toBe('fen-from-batch');
    expect(aligned[1].bestMove).toBe('O-O');
    expect(aligned[1].classification).toBe('blunder');
  });

  it('merges linked batch moment into critical moments', () => {
    const moments = [{ move_number: 18, played_move: 'Qh4', type: 'mistake' }];
    const aligned = alignMomentsWithBatchContext(moments, batchContext);
    expect(aligned[0].played_move).toBe('Qh5');
    expect(aligned[0].type).toBe('blunder');
  });

  it('detects classification disagreement', () => {
    const moves = [{ moveNumber: 18, classification: 'mistake' }];
    expect(hasClassificationDisagreement(batchContext, moves)).toBe(true);
  });
});
