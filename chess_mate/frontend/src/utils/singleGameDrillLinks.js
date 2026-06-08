import { lichessPuzzleUrlForTheme } from './lichessStudyLinks';
import { buildOpeningStudyQuery } from './openingNameCompact';

export const resolveSingleGameDrillLink = ({ moment = null, gameContext = {} } = {}) => {
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
    label: 'Practice on Lichess',
    url: lichessPuzzleUrlForTheme(theme),
    kind: 'puzzle',
  };
};
