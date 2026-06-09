import { lichessPuzzleUrlForTheme } from './lichessStudyLinks';
import { buildOpeningStudyQuery } from './openingNameCompact';

const lichessAnalysisFromFen = (fen) => {
  if (!fen || typeof fen !== 'string') {
    return null;
  }
  const encoded = encodeURIComponent(fen.trim().replace(/ /g, '_'));
  return `https://lichess.org/analysis/${encoded}`;
};

export const resolveSingleGameDrillLink = ({ moment = null, gameContext = {} } = {}) => {
  if (moment?.fen) {
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

  const opening = gameContext.opening_name || gameContext.opening;
  if (opening && opening.toLowerCase() !== 'unknown opening') {
    const query = buildOpeningStudyQuery(opening);
    if (query) {
      return {
        label: `Study ${opening} on Lichess`,
        url: `https://lichess.org/analysis?q=${encodeURIComponent(query)}`,
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
