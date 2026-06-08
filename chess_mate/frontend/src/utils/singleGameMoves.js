/** Normalize single-game move payloads for board + chart UI. */

const toNumber = (value, fallback = 0) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

export const normalizeSingleGameMove = (move = {}, index = 0) => {
  const evalAfter = move.eval_after ?? move.evaluation ?? move.score ?? 0;
  const evalBefore = move.eval_before ?? null;
  const evalChange = move.eval_change ?? move.evaluation_change ?? move.delta ?? 0;

  return {
    index,
    moveNumber: move.move_number || index + 1,
    san: move.san || move.move || '-',
    uci: move.move || move.uci || '',
    fen: move.position || move.fen || '',
    isWhite: Boolean(move.is_white ?? move.isWhite),
    classification: move.classification || 'neutral',
    evalAfter: toNumber(evalAfter),
    evalBefore: evalBefore == null ? null : toNumber(evalBefore),
    evalChange: toNumber(evalChange),
    bestMove: move.best_move_san || move.best_move || move.bestMove || '-',
    bestMoveUci: move.best_move_uci || (typeof move.best_move === 'string' && move.best_move.length <= 5 ? move.best_move : '') || '',
    isBest: Boolean(move.is_best || move.isBest),
    isCritical: Boolean(move.is_critical || move.isCritical),
  };
};

export const normalizeSingleGameMoves = (rawMoves = []) => {
  if (!Array.isArray(rawMoves)) {
    return [];
  }
  return rawMoves.map((move, index) => normalizeSingleGameMove(move, index));
};

export const findMoveIndexByNumber = (moves = [], moveNumber) => {
  const target = Number(moveNumber);
  if (!Number.isFinite(target) || target <= 0) {
    return 0;
  }
  const index = moves.findIndex((move) => Number(move.moveNumber) === target);
  return index >= 0 ? index : 0;
};

export const pickEvalSeries = (moves = []) =>
  moves.map((move, index) => ({
    label: move.moveNumber || index + 1,
    value: toNumber(move.evalAfter),
  }));
