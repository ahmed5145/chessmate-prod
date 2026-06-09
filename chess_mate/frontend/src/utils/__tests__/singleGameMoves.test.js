import {
  annotateMovesForPlayer,
  countFullMoves,
  findMoveIndexByNumber,
  findMoveIndexForMoment,
  formatBestMoveDisplay,
  formatMoveLabel,
  formatMoveSideLabel,
  formatMovesSummaryLabel,
  formatPlayerEvalLoss,
  getMoveArrowColors,
  inferDisplayClassification,
  normalizeSingleGameMoves,
  pickEvalSeries,
} from '../singleGameMoves';

describe('singleGameMoves', () => {
  const pairedMoves = normalizeSingleGameMoves([
    { move_number: 10, san: 'Qb3', is_white: true, eval_change: -0.67, best_move: 'f4g5' },
    { move_number: 10, san: 'd5', is_white: false, eval_change: -8.41, best_move: 'b8a6' },
    { move_number: 11, san: 'Bxc7', is_white: true, eval_change: 0.04, best_move: 'f4c7' },
  ]);

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

  it('labels white and black moves distinctly', () => {
    expect(formatMoveLabel(pairedMoves[0])).toBe('10. Qb3');
    expect(formatMoveLabel(pairedMoves[1])).toBe('10... d5');
  });

  it('finds the correct ply when move number is shared', () => {
    expect(findMoveIndexByNumber(pairedMoves, 10, { playerColor: 'black' })).toBe(1);
    expect(findMoveIndexByNumber(pairedMoves, 10, { isWhite: true })).toBe(0);
  });

  it('resolves critical moments to the player ply', () => {
    const index = findMoveIndexForMoment(pairedMoves, {
      move_number: 10,
      played_move: 'd5',
      played_move_uci: 'd6d5',
      player_color: 'black',
    }, 'black');
    expect(index).toBe(1);
  });

  it('formats UCI best moves for display', () => {
    expect(formatBestMoveDisplay(pairedMoves[0])).toBe('f4→g5');
  });

  it('infers blunder classification from large eval loss', () => {
    expect(inferDisplayClassification(pairedMoves[1], 'black')).toBe('blunder');
    expect(formatPlayerEvalLoss(pairedMoves[1])).toBe('8.41');
  });

  it('summarizes full move count only', () => {
    expect(countFullMoves(pairedMoves)).toBe(11);
    expect(formatMovesSummaryLabel(pairedMoves)).toBe('11 moves');
  });

  it('annotates player vs opponent sides', () => {
    const annotated = annotateMovesForPlayer(pairedMoves, 'black');
    expect(annotated[0].sideLabel).toBe('Opponent');
    expect(annotated[1].sideLabel).toBe('You');
    expect(formatMoveSideLabel(pairedMoves[1], 'black')).toBe('You');
  });

  it('colors arrows by classification and side', () => {
    const blunderStyle = getMoveArrowColors(pairedMoves[1], 'black');
    expect(blunderStyle.playedArrowColor).toBe('#dc2626');
    expect(blunderStyle.bestArrowColor).toBe('#16a34a');
    expect(blunderStyle.icon).toBe('??');

    const opponentBest = getMoveArrowColors({
      ...pairedMoves[2],
      isBest: true,
      displayClassification: 'best',
      displayArrowStyle: undefined,
    }, 'black');
    expect(opponentBest.playedArrowColor).toBe('#2563eb');
    expect(opponentBest.bestArrowColor).toBeNull();
  });

  it('builds eval series by ply', () => {
    const moves = normalizeSingleGameMoves([
      { move_number: 1, eval_after: 0.1 },
      { move_number: 1, eval_after: -0.5, is_white: false },
    ]);
    expect(pickEvalSeries(moves, 'white')).toEqual([
      { label: 1, value: 0.1 },
      { label: 1, value: -0.5 },
    ]);
  });
});
