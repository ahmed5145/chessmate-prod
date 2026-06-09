/** Chess.com-style move labels, colors, and icons for single-game review. */

const toNumber = (value, fallback = 0) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

export const evalForPlayer = (whitePovEval, playerColor = 'white') => {
  const value = toNumber(whitePovEval, 0);
  return playerColor === 'white' ? value : -value;
};

export const isPlayerMove = (move = {}, playerColor = 'white') => {
  const isWhite = move.isWhite ?? move.is_white;
  return Boolean(isWhite) === (playerColor === 'white');
};

export const playerEvalLoss = (move = {}) => {
  const change = toNumber(move.evalChange, 0);
  return change < 0 ? Math.abs(change) : 0;
};

export const MOVE_CLASSIFICATIONS = {
  book: {
    key: 'book',
    label: 'Book',
    icon: '📖',
    arrowColor: '#7c3aed',
    badgeClass: 'bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-200',
  },
  brilliant: {
    key: 'brilliant',
    label: 'Brilliant',
    icon: '!!',
    arrowColor: '#06b6d4',
    badgeClass: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/40 dark:text-cyan-200',
  },
  best: {
    key: 'best',
    label: 'Best',
    icon: '★',
    arrowColor: '#16a34a',
    badgeClass: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200',
  },
  good: {
    key: 'good',
    label: 'Good',
    icon: '✓',
    arrowColor: '#22c55e',
    badgeClass: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200',
  },
  inaccuracy: {
    key: 'inaccuracy',
    label: 'Inaccuracy',
    icon: '?!',
    arrowColor: '#f59e0b',
    badgeClass: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200',
  },
  mistake: {
    key: 'mistake',
    label: 'Mistake',
    icon: '?',
    arrowColor: '#ea580c',
    badgeClass: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200',
  },
  blunder: {
    key: 'blunder',
    label: 'Blunder',
    icon: '??',
    arrowColor: '#dc2626',
    badgeClass: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200',
  },
  missed_win: {
    key: 'missed_win',
    label: 'Missed win',
    icon: '✗',
    arrowColor: '#e11d48',
    badgeClass: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-200',
  },
  neutral: {
    key: 'neutral',
    label: 'Solid',
    icon: '·',
    arrowColor: '#64748b',
    badgeClass: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200',
  },
};

const ERROR_CLASSES = new Set(['inaccuracy', 'mistake', 'blunder', 'missed_win']);
const POSITIVE_CLASSES = new Set(['book', 'brilliant', 'best', 'good']);

const normalizeToken = (value) =>
  String(value || 'neutral').toLowerCase().replace(/_/g, ' ').trim();

export const resolveMoveClassification = (move = {}, reviewPlayerColor = 'white') => {
  const stored = normalizeToken(move.classification);
  const loss = playerEvalLoss(move);
  const isPlayer = isPlayerMove(move, reviewPlayerColor);
  const moverColor = move.isWhite ? 'white' : 'black';
  const evalBeforePlayer = move.evalBefore == null
    ? null
    : evalForPlayer(move.evalBefore, moverColor);
  const evalAfterPlayer = evalForPlayer(move.evalAfter, moverColor);

  if (stored === 'brilliant' || stored === 'great move' || stored === 'great') {
    return 'brilliant';
  }
  if (stored === 'book') {
    return 'book';
  }

  if (
    isPlayer
    && evalBeforePlayer != null
    && evalBeforePlayer >= 2
    && (loss >= 1 || (evalAfterPlayer != null && evalBeforePlayer - evalAfterPlayer >= 1))
  ) {
    return 'missed_win';
  }

  if (move.isBest || stored === 'best' || stored === 'excellent move' || stored === 'excellent') {
    return 'best';
  }

  if (loss >= 1.5) {
    return 'blunder';
  }
  if (loss >= 0.5) {
    return 'mistake';
  }
  if (loss >= 0.2) {
    return 'inaccuracy';
  }

  if (stored === 'blunder') {
    return 'blunder';
  }
  if (stored === 'mistake') {
    return 'mistake';
  }
  if (stored === 'inaccuracy') {
    return 'inaccuracy';
  }
  if (stored === 'missed win' || stored === 'missed_win') {
    return 'missed_win';
  }

  if (isPlayer && Number(move.moveNumber) <= 12 && loss < 0.08) {
    return 'book';
  }

  if (stored === 'good move' || stored === 'good' || loss === 0) {
    return 'good';
  }

  return 'neutral';
};

export const getClassificationMeta = (classificationKey) =>
  MOVE_CLASSIFICATIONS[classificationKey] || MOVE_CLASSIFICATIONS.neutral;

export const getMoveArrowStyle = (move = {}, reviewPlayerColor = 'white') => {
  const key = move.displayClassification || resolveMoveClassification(move, reviewPlayerColor);
  const meta = getClassificationMeta(key);
  const isPlayer = isPlayerMove(move, reviewPlayerColor);
  const isBest = key === 'best' || key === 'brilliant' || move.isBest;

  let playedArrowColor = meta.arrowColor;
  if (!isPlayer && isBest) {
    playedArrowColor = '#2563eb';
  } else if (!isPlayer && !ERROR_CLASSES.has(key)) {
    playedArrowColor = '#475569';
  }

  return {
    classification: key,
    icon: meta.icon,
    label: meta.label,
    playedArrowColor,
    bestArrowColor: isBest ? null : '#16a34a',
    badgeClass: meta.badgeClass,
  };
};

export const formatReviewPositionEval = (move = {}, reviewPlayerColor = 'white') => {
  const value = evalForPlayer(move.evalAfter, reviewPlayerColor);
  if (Math.abs(value) >= 9.5) {
    return value > 0 ? '+M' : '-M';
  }
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}`;
};

export const formatReviewPositionEvalVerbose = (move = {}, reviewPlayerColor = 'white') => {
  const text = formatReviewPositionEval(move, reviewPlayerColor);
  const value = evalForPlayer(move.evalAfter, reviewPlayerColor);
  if (value > 1.5) {
    return { text, tone: 'winning' };
  }
  if (value < -1.5) {
    return { tone: 'losing', text };
  }
  if (Math.abs(value) <= 0.35) {
    return { tone: 'equal', text };
  }
  return { tone: 'unclear', text };
};

export const computePlayerMoveStats = (moves = [], reviewPlayerColor = 'white') => {
  const playerMoves = moves.filter((move) => isPlayerMove(move, reviewPlayerColor));
  if (!playerMoves.length) {
    return { accuracy: 0, errors: 0, mistakes: 0, blunders: 0, totalMoves: 0 };
  }

  const classes = playerMoves.map((move) => resolveMoveClassification(move, reviewPlayerColor));
  const errors = classes.filter((key) => ERROR_CLASSES.has(key)).length;
  const mistakes = classes.filter((key) => key === 'mistake' || key === 'blunder' || key === 'missed_win').length;
  const blunders = classes.filter((key) => key === 'blunder' || key === 'missed_win').length;
  const positive = classes.filter((key) => POSITIVE_CLASSES.has(key)).length;
  const accuracy = Math.round((positive / playerMoves.length) * 1000) / 10;

  return {
    accuracy,
    errors,
    mistakes,
    blunders,
    totalMoves: playerMoves.length,
  };
};

export const plyToFullMoveNumber = (ply, totalPlies = null) => {
  const n = Number(ply);
  if (!Number.isFinite(n) || n <= 0) {
    return null;
  }
  const full = Math.ceil(n / 2);
  if (totalPlies != null) {
    const totalFull = Math.ceil(Number(totalPlies) / 2);
    return { current: full, total: totalFull };
  }
  return { current: full, total: null };
};
