import { lichessOpeningSearchUrl, lichessPuzzleUrlForTheme } from './lichessStudyLinks';
import { buildOpeningStudyDrillLink, countOpeningInaccuracies } from './singleGameBatchCta';
import { buildOpeningStudyQuery } from './openingNameCompact';

/** Lichess analysis URLs use underscores for spaces; slashes stay unencoded. */
export const lichessAnalysisFromFen = (fen) => {
  if (!fen || typeof fen !== 'string') {
    return null;
  }
  const normalized = fen.trim().replace(/ /g, '_');
  return `https://lichess.org/analysis/${normalized}`;
};

/** Half-move (ply) for the critical moment — used by Lichess game links. */
export const lichessPlyFromMoment = (moment = {}) => {
  const moveNumber = Number(moment.move_number);
  if (!Number.isFinite(moveNumber) || moveNumber < 1) {
    return null;
  }

  const mover = String(moment.mover || '').toLowerCase();
  if (mover === 'white') {
    return (moveNumber - 1) * 2 + 1;
  }
  if (mover === 'black') {
    return (moveNumber - 1) * 2 + 2;
  }

  if (moment.is_white === true) {
    return (moveNumber - 1) * 2 + 1;
  }
  if (moment.is_white === false) {
    return (moveNumber - 1) * 2 + 2;
  }

  const playerColor = String(moment.player_color || '').toLowerCase();
  if (playerColor === 'white' || playerColor === 'black') {
    return (moveNumber - 1) * 2 + (playerColor === 'white' ? 1 : 2);
  }

  return moveNumber * 2 - 1;
};

export const buildLichessGameMoveUrl = (gameUrl, moment = {}) => {
  if (!gameUrl || !String(gameUrl).includes('lichess.org')) {
    return null;
  }
  const ply = lichessPlyFromMoment(moment);
  if (!ply) {
    return gameUrl;
  }
  try {
    const url = new URL(gameUrl);
    url.searchParams.set('move', String(ply));
    return url.toString();
  } catch {
    return gameUrl;
  }
};

export const buildMomentReplayLink = (moment = {}, gameContext = {}) => {
  if (!moment) {
    return null;
  }

  const platformUrl = gameContext.platform_game_url;
  const lichessReplay = buildLichessGameMoveUrl(platformUrl, moment);
  if (lichessReplay) {
    const moveNo = moment.move_number ? `move ${moment.move_number}` : 'this moment';
    return {
      label: `Replay ${moveNo} on Lichess`,
      url: lichessReplay,
      kind: 'moment',
    };
  }

  if (moment.fen) {
    const analysisUrl = lichessAnalysisFromFen(moment.fen);
    if (analysisUrl) {
      const moveNo = moment.move_number ? `move ${moment.move_number}` : 'this position';
      return {
        label: `Replay ${moveNo} on Lichess`,
        url: analysisUrl,
        kind: 'moment',
      };
    }
  }

  if (platformUrl) {
    const moveNo = moment.move_number ? `move ${moment.move_number}` : 'this game';
    return {
      label: `Open ${moveNo} on ${gameContext.platform === 'chess.com' ? 'Chess.com' : 'Lichess'}`,
      url: platformUrl,
      kind: 'moment',
    };
  }

  return null;
};

export const resolveSingleGameDrillLink = ({
  moment = null,
  gameContext = {},
  moves = [],
} = {}) => {
  const openingMistakes = countOpeningInaccuracies(moves);
  if (openingMistakes > 0) {
    const openingDrill = buildOpeningStudyDrillLink({
      gameContext,
      moves,
      worstMoment: moment,
    });
    if (openingDrill) {
      return openingDrill;
    }
  }

  const momentReplay = buildMomentReplayLink(moment, gameContext);
  if (momentReplay) {
    return momentReplay;
  }

  const opening = gameContext.opening_name || gameContext.opening;
  if (opening && opening.toLowerCase() !== 'unknown opening') {
    const query = buildOpeningStudyQuery(opening);
    if (query) {
      return {
        label: `Study ${opening} on Lichess`,
        url: lichessOpeningSearchUrl(opening, {
          ecoCode: gameContext.eco || gameContext.eco_code,
          playerColor: gameContext.player_color,
        }),
        kind: 'opening',
      };
    }
  }

  const theme = moment?.type === 'blunder' || moment?.type === 'mistake'
    ? 'tactical_oversight'
    : 'advantage';
  return {
    label: 'Practice tactics on Lichess',
    url: lichessPuzzleUrlForTheme(theme),
    kind: 'puzzle',
  };
};
