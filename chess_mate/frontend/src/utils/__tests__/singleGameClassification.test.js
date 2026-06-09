import {
  buildMoveEvalSummary,
  computePlayerMoveStats,
  formatAfterMoveEval,
  formatBestLineEval,
  formatLivePositionEval,
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

  it('formats live, best-line, and after-move evals from player perspective', () => {
    const move = {
      evalBefore: -1.47,
      evalAfter: 6.94,
      evalAfterBest: -0.8,
      isBest: false,
    };
    expect(formatLivePositionEval(move, 'black')).toBe('+1.47');
    expect(formatBestLineEval(move, 'black')).toBe('+0.80');
    expect(formatAfterMoveEval(move, 'black')).toBe('-6.94');
    expect(buildMoveEvalSummary(move, 'black').showBestLine).toBe(true);
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
