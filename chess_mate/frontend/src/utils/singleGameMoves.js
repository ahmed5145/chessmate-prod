/** Normalize single-game move payloads for board + chart UI. */

import {
  buildMoveEvalSummary,
  computePlayerMoveStats,
  evalForPlayer,
  formatAfterMoveEval,
  formatBestLineEval,
  formatLivePositionEval,
  formatReviewPositionEval,
  getMoveArrowStyle,
  isPlayerMove as classificationIsPlayerMove,
  resolveMoveClassification,
} from './singleGameClassification';

export {
  buildMoveEvalSummary,
  computePlayerMoveStats,
  evalForPlayer,
  formatAfterMoveEval,
  formatBestLineEval,
  formatLivePositionEval,
  formatReviewPositionEval,
  resolveMoveClassification,
} from './singleGameClassification';

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

export const inferDisplayClassification = (move = {}, reviewPlayerColor = 'white') =>
  resolveMoveClassification(move, reviewPlayerColor);

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

export const normalizeSingleGameMove = (move = {}, index = 0, reviewPlayerColor = 'white') => {
  const evalAfter = move.eval_after ?? move.evaluation ?? move.score ?? 0;
  const evalBefore = move.eval_before ?? null;
  const evalAfterBestRaw = move.eval_after_best ?? move.evalAfterBest;
  const evalAfterBest = evalAfterBestRaw == null ? null : toNumber(evalAfterBestRaw);
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
    evalAfterBest: evalAfterBest == null ? toNumber(evalAfter) : evalAfterBest,
    evalChange: toNumber(evalChange),
    bestMove: move.best_move_san || move.best_move || move.bestMove || '-',
    bestMoveUci,
    isBest: Boolean(move.is_best || move.isBest),
    isCritical: Boolean(move.is_critical || move.isCritical),
  };

  normalized.displayClassification = resolveMoveClassification(normalized, reviewPlayerColor);
  normalized.displayBestMove = formatBestMoveDisplay(normalized);
  normalized.displayLabel = formatMoveLabel(normalized);
  normalized.displayLiveEval = formatLivePositionEval(normalized, reviewPlayerColor);
  normalized.displayBestLineEval = formatBestLineEval(normalized, reviewPlayerColor);
  normalized.displayAfterEval = formatAfterMoveEval(normalized, reviewPlayerColor);
  normalized.displayEval = normalized.displayAfterEval;
  normalized.evalSummary = buildMoveEvalSummary(normalized, reviewPlayerColor);
  const arrowStyle = getMoveArrowStyle(normalized, reviewPlayerColor);
  normalized.displayArrowStyle = arrowStyle;

  return normalized;
};

export const normalizeSingleGameMoves = (rawMoves = [], reviewPlayerColor = 'white') => {
  if (!Array.isArray(rawMoves)) {
    return [];
  }
  return rawMoves.map((move, index) => normalizeSingleGameMove(move, index, reviewPlayerColor));
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

export const pickEvalSeries = (moves = [], reviewPlayerColor = 'white') =>
  moves.map((move, index) => ({
    label: move.moveNumber || index + 1,
    value: evalForPlayer(move.evalAfter, reviewPlayerColor),
  }));

export const isPlayerMove = classificationIsPlayerMove;

export const formatMoveSideLabel = (move = {}, playerColor = 'white') =>
  (isPlayerMove(move, playerColor) ? 'You' : 'Opponent');

export const annotateMovesForPlayer = (moves = [], playerColor = 'white') =>
  moves.map((move) => {
    const playerMove = isPlayerMove(move, playerColor);
    const displayClassification = resolveMoveClassification(move, playerColor);
    const enriched = {
      ...move,
      isPlayerMove: playerMove,
      sideLabel: playerMove ? 'You' : 'Opponent',
      displayClassification,
      displayLiveEval: formatLivePositionEval(move, playerColor),
      displayBestLineEval: formatBestLineEval(move, playerColor),
      displayAfterEval: formatAfterMoveEval(move, playerColor),
      displayEval: formatAfterMoveEval(move, playerColor),
      evalSummary: buildMoveEvalSummary(move, playerColor),
    };
    enriched.displayArrowStyle = getMoveArrowStyle(enriched, playerColor);
    return enriched;
  });

export const getMoveArrowColors = (move = {}, playerColor = 'white') => {
  const style = move.displayArrowStyle || getMoveArrowStyle(move, playerColor);
  return {
    playedArrowColor: style.playedArrowColor,
    bestArrowColor: style.bestArrowColor,
    icon: style.icon,
    classification: style.classification,
  };
};

export const formatMovesSummaryLabel = (moves = []) => {
  const fullMoves = countFullMoves(moves);
  if (!fullMoves) {
    return '0 moves';
  }
  return `${fullMoves} move${fullMoves === 1 ? '' : 's'}`;
};
