/** Merge batch-linked moment data into single-game move/moment payloads. */

const normalizeClassification = (value) =>
  String(value || '').toLowerCase().replace(/_/g, ' ').trim();

export const alignMomentsWithBatchContext = (moments = [], batchContext = null) => {
  const linked = batchContext?.linked_moment;
  if (!linked?.move_number || !Array.isArray(moments)) {
    return moments;
  }

  return moments.map((moment) => {
    if (Number(moment.move_number) !== Number(linked.move_number)) {
      return moment;
    }
    return {
      ...moment,
      fen: linked.fen || moment.fen,
      played_move: linked.played_move || moment.played_move,
      best_move: linked.best_move || moment.best_move,
      played_move_uci: linked.played_move_uci || moment.played_move_uci,
      best_move_uci: linked.best_move_uci || moment.best_move_uci,
      type: linked.type || moment.type,
      batch_type: linked.type,
      explanation: moment.explanation || linked.explanation,
    };
  });
};

export const alignMovesWithBatchContext = (moves = [], batchContext = null) => {
  const linked = batchContext?.linked_moment;
  if (!linked?.move_number || !Array.isArray(moves)) {
    return moves;
  }

  return moves.map((move) => {
    if (Number(move.moveNumber) !== Number(linked.move_number)) {
      return move;
    }
    return {
      ...move,
      fen: linked.fen || move.fen,
      san: linked.played_move || move.san,
      uci: linked.played_move_uci || move.uci,
      bestMove: linked.best_move || move.bestMove,
      bestMoveUci: linked.best_move_uci || move.bestMoveUci,
      classification: linked.type || move.classification,
      batchClassification: linked.type,
      singleClassification: move.classification,
    };
  });
};

export const hasClassificationDisagreement = (batchContext, moves = []) => {
  const linked = batchContext?.linked_moment;
  if (!linked?.move_number || !linked?.type) {
    return false;
  }
  const target = moves.find((move) => Number(move.moveNumber) === Number(linked.move_number));
  if (!target?.classification) {
    return false;
  }
  return normalizeClassification(linked.type) !== normalizeClassification(target.classification);
};
