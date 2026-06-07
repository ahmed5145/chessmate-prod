/**
 * Human-readable game label: opponent + date (platform link is secondary).
 */

export const formatGameDate = (datePlayed) => {
  if (!datePlayed) {
    return null;
  }
  const parsed = new Date(datePlayed);
  if (Number.isNaN(parsed.getTime())) {
    return String(datePlayed);
  }
  return parsed.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
};

export const formatGameLabel = (gameResult = {}) => {
  const opponent = gameResult.opponent;
  const dateLabel = formatGameDate(gameResult.date_played);

  if (opponent && dateLabel) {
    return `vs ${opponent} — ${dateLabel}`;
  }
  if (opponent) {
    return `vs ${opponent}`;
  }
  if (dateLabel) {
    return dateLabel;
  }

  const gameId = gameResult.game_id;
  if (gameId) {
    const indexMatch = String(gameId).match(/^game_(\d+)$/);
    if (indexMatch) {
      return `Game ${Number(indexMatch[1]) + 1}`;
    }
    return String(gameId);
  }

  return 'Unknown game';
};

export const findGameResultById = (perGameResults, gameId) => {
  if (!gameId || !Array.isArray(perGameResults)) {
    return null;
  }
  return perGameResults.find((game) => game.game_id === gameId) || null;
};

export const formatGameLabelById = (perGameResults, gameId) => {
  const game = findGameResultById(perGameResults, gameId);
  if (game) {
    return formatGameLabel(game);
  }
  if (gameId) {
    const indexMatch = String(gameId).match(/^game_(\d+)$/);
    if (indexMatch) {
      return `Game ${Number(indexMatch[1]) + 1}`;
    }
    return String(gameId);
  }
  return 'Unknown game';
};

const GAME_ID_PATTERN = /\bgame_\d+\b/gi;

/**
 * Replace internal game_N ids with human labels (or "this game" when shown in-context).
 */
export const humanizeGameIdInText = (text, perGameResults, options = {}) => {
  if (!text || typeof text !== 'string') {
    return text;
  }

  const { inThisGameId = null } = options;

  let result = text.replace(GAME_ID_PATTERN, (match) => {
    const normalized = match.toLowerCase();
    if (inThisGameId && normalized === String(inThisGameId).toLowerCase()) {
      return 'this game';
    }
    return formatGameLabelById(perGameResults, normalized);
  });

  result = result.replace(/\bIn this game\b/g, 'In this game');
  result = result.replace(
    /(In (?:this game|vs [^,]+ — [^,]+|Game \d+))\s+move\b/gi,
    '$1, move'
  );

  return result;
};
