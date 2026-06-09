const OPENING_MOVE_CUTOFF = 12;

const isOpeningMistake = (move = {}) => {
  const moveNumber = Number(move.move_number ?? move.moveNumber);
  if (!Number.isFinite(moveNumber) || moveNumber > OPENING_MOVE_CUTOFF) {
    return false;
  }
  const classification = String(move.classification || move.type || '').toLowerCase();
  return ['inaccuracy', 'mistake', 'blunder', 'missed_win'].some((label) => classification.includes(label));
};

export const countOpeningInaccuracies = (moves = []) => {
  if (!Array.isArray(moves)) {
    return 0;
  }
  return moves.filter(isOpeningMistake).length;
};

export const buildBatchPatternCta = (batchContext = null) => {
  if (!batchContext?.batch_id) {
    return {
      variant: 'upsell',
      headline: 'Want patterns across many games?',
      subline: 'Batch Coach finds recurring mistakes across 5–30 games — one coach-style plan, not one-game engine lines.',
      primaryLabel: 'Start Batch Coach',
      primaryPath: '/batch-analysis',
      secondaryLabel: 'All games',
      secondaryPath: '/games',
      reportPath: null,
    };
  }

  const batchId = batchContext.batch_id;
  const priorityRank = batchContext.priority_rank || batchContext.priority?.rank;
  const priorityTitle = batchContext.priority?.title || batchContext.pattern_label;
  const patternCount = batchContext.pattern_count;
  const batchGameCount = batchContext.batch_game_count || batchContext.games_count;
  const reportPath = priorityRank
    ? `/batch-report/${batchId}?priority=${priorityRank}`
    : `/batch-report/${batchId}`;

  let headline = 'Patterns across your games live in your batch report.';
  if (priorityTitle && patternCount != null && batchGameCount) {
    headline = `"${priorityTitle}" showed up in ${patternCount} of ${batchGameCount} games in this batch`;
  } else if (priorityTitle) {
    headline = `Your batch priority: ${priorityTitle}`;
  } else if (batchContext.pattern_frequency) {
    headline = `This pattern appeared in ${batchContext.pattern_frequency}`;
  }

  return {
    variant: 'batch',
    headline,
    subline: 'See priorities, drills, and your training plan in Batch Coach.',
    primaryLabel: 'See batch priorities',
    primaryPath: reportPath,
    secondaryLabel: 'Run new batch',
    secondaryPath: '/batch-analysis',
    reportPath,
  };
};

export const buildOpeningStudyDrillLink = ({
  gameContext = {},
  moves = [],
  worstMoment = null,
} = {}) => {
  const opening = gameContext.opening_name || gameContext.opening;
  if (!opening || String(opening).toLowerCase() === 'unknown opening') {
    return null;
  }

  const eco = gameContext.eco || gameContext.eco_code;
  const mistakeCount = countOpeningInaccuracies(moves);
  const openingMoment = moves.find(isOpeningMistake) || (
    worstMoment?.move_number && Number(worstMoment.move_number) <= OPENING_MOVE_CUTOFF
      ? worstMoment
      : null
  );

  const ecoPrefix = eco ? `${eco} ` : '';
  const countSuffix = mistakeCount > 0
    ? ` — you had ${mistakeCount} inaccurac${mistakeCount === 1 ? 'y' : 'ies'} in the opening`
    : '';

  if (openingMoment?.fen) {
    const encoded = encodeURIComponent(String(openingMoment.fen).trim().replace(/ /g, '_'));
    return {
      label: `Study ${ecoPrefix}${opening}${countSuffix}`,
      url: `https://lichess.org/analysis/${encoded}`,
      kind: 'opening',
    };
  }

  return {
    label: `Study ${ecoPrefix}${opening}${countSuffix}`,
    url: `https://lichess.org/analysis?q=${encodeURIComponent(opening)}`,
    kind: 'opening',
  };
};
