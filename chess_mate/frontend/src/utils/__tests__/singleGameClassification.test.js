import {
  computePlayerMoveStats,
  formatReviewPositionEval,
  plyToFullMoveNumber,
  resolveMoveClassification,
} from '../singleGameClassification';
import { normalizeSingleGameMove } from '../singleGameMoves';

describe('singleGameClassification', () => {
  it('classifies large losses as blunders and missed wins separately', () => {
    expect(resolveMoveClassification(normalizeSingleGameMove({
      is_white: false,
      eval_before: -3.2,
      eval_after: 0.4,
      eval_change: -3.6,
      move_number: 18,
      classification: 'inaccuracy',
    }, 0, 'black'), 'black')).toBe('missed_win');

    expect(resolveMoveClassification(normalizeSingleGameMove({
      is_white: false,
      eval_before: -1.47,
      eval_after: 6.94,
      eval_change: -8.41,
      move_number: 10,
      classification: 'inaccuracy',
    }, 0, 'black'), 'black')).toBe('blunder');
  });

  it('formats position eval from the reviewing player perspective', () => {
    expect(formatReviewPositionEval({ evalAfter: 6.94 }, 'black')).toBe('-6.94');
    expect(formatReviewPositionEval({ evalAfter: 0.4 }, 'white')).toBe('+0.40');
  });

  it('computes player-only accuracy and errors', () => {
    const stats = computePlayerMoveStats([
      { isWhite: false, evalChange: -0.5, moveNumber: 6, classification: 'mistake' },
      { isWhite: false, evalChange: 0.1, moveNumber: 7, isBest: true, classification: 'best' },
      { isWhite: true, evalChange: -1, moveNumber: 7, classification: 'blunder' },
    ], 'black');

    expect(stats.totalMoves).toBe(2);
    expect(stats.errors).toBe(1);
    expect(stats.accuracy).toBe(50);
  });

  it('converts engine ply progress to full-move counts', () => {
    expect(plyToFullMoveNumber(21, 21)).toEqual({ current: 11, total: 11 });
    expect(plyToFullMoveNumber(20, 40)).toEqual({ current: 10, total: 20 });
  });
});
