import { isUnknownOpening } from './batchGameLinks';
import { getEcoOpeningName } from './ecoOpeningNames';
import { compactOpeningName } from './openingNameCompact';

/**
 * Opening label for game lists (Games page, batch picker). Never shows "Unknown Opening".
 */
export const formatListOpeningLabel = (game) => {
  const rawName = game?.opening_name;
  const compacted = compactOpeningName(rawName);

  if (compacted && !isUnknownOpening(compacted)) {
    return compacted;
  }

  const fromEco = getEcoOpeningName(game?.eco_code);
  if (fromEco) {
    return fromEco;
  }

  const eco = String(game?.eco_code || '').trim();
  if (eco) {
    return `ECO ${eco}`;
  }

  return '—';
};
