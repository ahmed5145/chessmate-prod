/** Normalize single-game move payloads for board + chart UI. */

const toNumber = (value, fallback = 0) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const isUciMove = (value) =>
  typeof value === 'string' && /^[a-h][1-8][a-h][1-8][qrbn]?$/i.test(value.trim());

export const formatUciMove = (uci) => {
  if (!uci || typeof uci !== 'string' || uci.length < 4) {
    return uci || '-';
  }
  const promotion = uci.length > 4 ? uci.slice(4) : '';
  return `${uci.slice(0, 2)}→${uci.slice(2, 4)}${promotion}`;
};

export const formatBestMoveDisplay = (move = {}) => {
  const san = move.bestMove;
  if (san && san !== '-' && !isUciMove(san)) {
    return san;
  }
  if (move.bestMoveUci) {
    return formatUciMove(move.bestMoveUci);
  }
  if (san && isUciMove(san)) {
    return formatUciMove(san);
  }
  return '-';
};

export const playerEvalLoss = (move = {}) => {
  const change = toNumber(move.evalChange, 0);
  if (change < 0) {
    return Math.abs(change);
  }
  return 0;
};

export const formatPlayerEvalLoss = (move = {}) => {
  const change = toNumber(move.evalChange, 0);
  if (change > 0) {
    return `+${change.toFixed(2)}`;
  }
  if (change < 0) {
    return Math.abs(change).toFixed(2);
  }
  return '0.00';
};

export const inferDisplayClassification = (move = {}) => {
  const stored = String(move.classification || 'neutral').toLowerCase();
  const loss = playerEvalLoss(move);
  if (loss >= 1.5) {
    return 'blunder';
  }
  if (loss >= 0.5) {
    return 'mistake';
  }
  if (loss >= 0.2) {
    return 'inaccuracy';
  }
  return stored;
};

export const formatMoveLabel = (move = {}) => {
  const num = move.moveNumber;
  const san = move.san || '-';
  if (!Number.isFinite(Number(num))) {
    return san;
  }
  return move.isWhite ? `${num}. ${san}` : `${num}... ${san}`;
};

export const countFullMoves = (moves = []) => {
  if (!Array.isArray(moves) || moves.length === 0) {
    return 0;
  }
  return moves.reduce((max, move) => Math.max(max, Number(move.moveNumber) || 0), 0);
};

export const normalizeSingleGameMove = (move = {}, index = 0) => {
  const evalAfter = move.eval_after ?? move.evaluation ?? move.score ?? 0;
  const evalBefore = move.eval_before ?? null;
  const evalChange = move.eval_change ?? move.evaluation_change ?? move.delta ?? 0;
  const bestMoveUci = move.best_move_uci
    || (typeof move.best_move === 'string' && isUciMove(move.best_move) ? move.best_move : '')
    || '';

  const normalized = {
    index,
    ply: index + 1,
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
    bestMoveUci,
    isBest: Boolean(move.is_best || move.isBest),
    isCritical: Boolean(move.is_critical || move.isCritical),
  };

  normalized.displayClassification = inferDisplayClassification(normalized);
  normalized.displayBestMove = formatBestMoveDisplay(normalized);
  normalized.displayLabel = formatMoveLabel(normalized);
  normalized.displayEvalLoss = formatPlayerEvalLoss(normalized);

  return normalized;
};

export const normalizeSingleGameMoves = (rawMoves = []) => {
  if (!Array.isArray(rawMoves)) {
    return [];
  }
  return rawMoves.map((move, index) => normalizeSingleGameMove(move, index));
};

export const findMoveIndexByNumber = (moves = [], moveNumber, options = {}) => {
  const target = Number(moveNumber);
  if (!Number.isFinite(target) || target <= 0) {
    return 0;
  }

  const { isWhite, playerColor } = options;

  if (isWhite === true || isWhite === false) {
    const index = moves.findIndex(
      (move) => Number(move.moveNumber) === target && Boolean(move.isWhite) === isWhite
    );
    if (index >= 0) {
      return index;
    }
  }

  if (playerColor === 'black') {
    const index = moves.findIndex(
      (move) => Number(move.moveNumber) === target && !move.isWhite
    );
    if (index >= 0) {
      return index;
    }
  }

  if (playerColor === 'white') {
    const index = moves.findIndex(
      (move) => Number(move.moveNumber) === target && move.isWhite
    );
    if (index >= 0) {
      return index;
    }
  }

  const fallback = moves.findIndex((move) => Number(move.moveNumber) === target);
  return fallback >= 0 ? fallback : 0;
};

export const findMoveIndexForMoment = (moves = [], moment = {}, defaultPlayerColor = 'white') => {
  if (!moment || typeof moment !== 'object') {
    return 0;
  }
  const playerColor = moment.player_color || defaultPlayerColor;
  const isWhite = playerColor === 'white';
  const byNumber = findMoveIndexByNumber(moves, moment.move_number, { isWhite, playerColor });
  if (moment.played_move_uci) {
    const byUci = moves.findIndex((move) => move.uci === moment.played_move_uci);
    if (byUci >= 0) {
      return byUci;
    }
  }
  if (moment.played_move) {
    const bySan = moves.findIndex(
      (move) => move.san === moment.played_move && Number(move.moveNumber) === Number(moment.move_number)
    );
    if (bySan >= 0) {
      return bySan;
    }
  }
  return byNumber;
};

export const pickEvalSeries = (moves = []) =>
  moves.map((move, index) => ({
    label: move.ply || index + 1,
    value: toNumber(move.evalAfter),
  }));

export const formatMovesSummaryLabel = (moves = []) => {
  const plies = moves.length;
  const fullMoves = countFullMoves(moves);
  if (!plies) {
    return '0 moves';
  }
  if (fullMoves && fullMoves !== plies) {
    return `${fullMoves} moves (${plies} half-moves)`;
  }
  return `${plies} moves`;
};
