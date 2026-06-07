/**
 * Client-side opening rollup for batch reports (mirrors batch_aggregator logic).
 * Used when batch_summary.opening_insights is empty (older reports or sparse batches).
 */

import { isUnknownOpening } from './batchGameLinks';
import { getEcoOpeningName } from './ecoOpeningNames';
import { formatGameLabel } from './formatGameLabel';
import { compactOpeningName } from './openingNameCompact';

export const resolveGameOpeningName = (game) => {
  let name = null;
  if (!isUnknownOpening(game?.opening_name)) {
    name = game.opening_name;
  } else {
    name = getEcoOpeningName(game?.eco_code);
  }
  const compacted = compactOpeningName(name);
  if (compacted) {
    return compacted;
  }
  return game?.opening_name || 'Unknown';
};

const hasOpeningData = (game) =>
  Boolean(game?.eco_code) || !isUnknownOpening(game?.opening_name);

const phaseScore = (phaseData = {}) => {
  const avgEvalDrop = Number(phaseData.avg_eval_drop);
  if (Number.isNaN(avgEvalDrop)) {
    return 0;
  }
  return Math.max(0, Math.min(1, 1 - avgEvalDrop));
};

const playerOutcome = (game) => {
  const raw = String(game.result || '').trim();
  const color = game.player_color || 'white';
  if (raw === '1/2-1/2' || raw === '*') {
    return 'draw';
  }
  if (raw === '1-0') {
    return color === 'white' ? 'win' : 'loss';
  }
  if (raw === '0-1') {
    return color === 'black' ? 'win' : 'loss';
  }
  return 'unknown';
};

const openingGroupKey = (game) => {
  const eco = String(game.eco_code || '').trim();
  if (eco) {
    return `eco:${eco}`;
  }
  const name = String(game.opening_name || '').trim();
  if (name.includes(':')) {
    return name.split(':', 1)[0].trim();
  }
  return name;
};

const openingDisplayName = (games) => {
  const names = games.map((game) => resolveGameOpeningName(game)).filter(Boolean);
  if (names.length === 0) {
    return 'Unknown';
  }
  const withVariation = names.filter((name) => String(name).includes(':'));
  if (withVariation.length > 0) {
    return withVariation.reduce((best, name) => (String(name).length > String(best).length ? name : best));
  }
  return names.reduce((best, name) => (String(name).length > String(best).length ? name : best));
};

const buildRecommendation = (openingName, games, wins, losses, draws, avgOpeningScore) => {
  if (losses >= 2 || (games.length >= 2 && losses > wins)) {
    return {
      status: 'struggling',
      recommendation: `You lost ${losses} of ${games.length} games as ${openingName}. Review mainline theory and typical plans for this opening.`,
    };
  }
  if (wins >= 2 && losses === 0) {
    return {
      status: 'strong',
      recommendation: `${openingName} is working well (${wins}W-${losses}L in this batch). Deepen theory on the lines you already play.`,
    };
  }
  if (avgOpeningScore != null && avgOpeningScore < 0.65) {
    return {
      status: 'needs_work',
      recommendation: `Opening phase accuracy in ${openingName} averaged ${Math.round(avgOpeningScore * 100)}%. Study model games and common middlegame plans.`,
    };
  }

  const ecoCodes = [...new Set(games.map((game) => game.eco_code).filter(Boolean))];
  const ecoLabel = ecoCodes.length === 1 ? ` (${ecoCodes[0]})` : '';
  const colors = games.map((game) => game.player_color || 'white');
  const playerColor = colors.filter((color) => color === 'black').length > colors.length / 2
    ? 'black'
    : 'white';
  const scoreText =
    avgOpeningScore != null
      ? ` Opening phase: ${Math.round(avgOpeningScore * 100)}%.`
      : '';
  return {
    status: 'neutral',
    recommendation: `As ${playerColor} in ${openingName}${ecoLabel}: ${wins}W-${losses}L-${draws}D across ${games.length} game(s).${scoreText}`,
  };
};

export const buildPerGameOpeningInsights = (perGameResults = []) => {
  if (!Array.isArray(perGameResults)) {
    return [];
  }

  return perGameResults.filter(hasOpeningData).map((game) => {
    const outcome = playerOutcome(game);
    const wins = outcome === 'win' ? 1 : 0;
    const losses = outcome === 'loss' ? 1 : 0;
    const draws = outcome === 'draw' ? 1 : 0;
    const openingPhase = game.phase_breakdown?.opening;
    const avgOpeningScore =
      openingPhase && Number(openingPhase.moves) > 0 ? phaseScore(openingPhase) : null;

    const openingName = resolveGameOpeningName(game);
    const { status, recommendation } = buildRecommendation(
      openingName,
      [game],
      wins,
      losses,
      draws,
      avgOpeningScore
    );

    return {
      opening_name: openingName,
      eco_code: game.eco_code || null,
      games: 1,
      record: `${wins}W-${losses}L-${draws}D`,
      avg_opening_score: avgOpeningScore != null ? Math.round(avgOpeningScore * 100) / 100 : null,
      status,
      player_color: game.player_color || 'white',
      recommendation,
      game_id: game.game_id,
      game_label: formatGameLabel(game),
      example_game_ids: game.game_id ? [game.game_id] : [],
    };
  });
};

export const buildOpeningInsightsFromGames = (perGameResults = []) => {
  if (!Array.isArray(perGameResults) || perGameResults.length === 0) {
    return [];
  }

  const byOpening = {};
  perGameResults.forEach((game) => {
    if (!hasOpeningData(game)) {
      return;
    }
    const key = openingGroupKey(game);
    if (!key) {
      return;
    }
    if (!byOpening[key]) {
      byOpening[key] = [];
    }
    byOpening[key].push(game);
  });

  const insights = Object.values(byOpening).map((games) => {
    const openingName = openingDisplayName(games);
    const outcomes = games.map(playerOutcome);
    const wins = outcomes.filter((outcome) => outcome === 'win').length;
    const losses = outcomes.filter((outcome) => outcome === 'loss').length;
    const draws = outcomes.filter((outcome) => outcome === 'draw').length;

    const openingScores = games
      .map((game) => game.phase_breakdown?.opening)
      .filter((phase) => Number(phase?.moves) > 0)
      .map(phaseScore);
    const avgOpeningScore =
      openingScores.length > 0
        ? openingScores.reduce((sum, score) => sum + score, 0) / openingScores.length
        : null;

    const { status, recommendation } = buildRecommendation(
      openingName,
      games,
      wins,
      losses,
      draws,
      avgOpeningScore
    );

    const colors = games.map((game) => game.player_color || 'white');
    const playerColor = colors.filter((color) => color === 'black').length > colors.length / 2
      ? 'black'
      : 'white';
    const ecoCodes = [...new Set(games.map((game) => game.eco_code).filter(Boolean))];

    return {
      opening_name: openingName,
      eco_code: ecoCodes.length === 1 ? ecoCodes[0] : null,
      eco_codes: ecoCodes.slice(0, 3),
      games: games.length,
      record: `${wins}W-${losses}L-${draws}D`,
      avg_opening_score: avgOpeningScore != null ? Math.round(avgOpeningScore * 100) / 100 : null,
      status,
      player_color: playerColor,
      recommendation,
      example_game_ids: games.map((game) => game.game_id).filter(Boolean).slice(0, 3),
    };
  });

  insights.sort((left, right) => {
    const leftRank = left.status === 'struggling' ? 0 : 1;
    const rightRank = right.status === 'struggling' ? 0 : 1;
    if (leftRank !== rightRank) {
      return leftRank - rightRank;
    }
    return right.games - left.games;
  });

  return insights;
};

export const resolveOpeningInsights = (batchSummary, perGameResults = []) => {
  const perGame = buildPerGameOpeningInsights(perGameResults);
  if (perGame.length > 0) {
    return perGame;
  }

  const fromSummary = Array.isArray(batchSummary?.opening_insights)
    ? batchSummary.opening_insights.filter((item) => hasOpeningData({ opening_name: item?.opening_name, eco_code: item?.eco_code }))
    : [];
  if (fromSummary.length > 0) {
    return fromSummary;
  }
  return buildOpeningInsightsFromGames(perGameResults);
};

export const resolveRepertoireGaps = (batchSummary, perGameResults = []) => {
  const rawGaps = Array.isArray(batchSummary?.repertoire_gaps)
    ? batchSummary.repertoire_gaps
    : resolveOpeningInsights(batchSummary, perGameResults).filter(
        (item) => item?.status === 'struggling' || item?.status === 'needs_work'
      );

  return rawGaps.filter((gap) => !isUnknownOpening(gap?.opening_name));
};
