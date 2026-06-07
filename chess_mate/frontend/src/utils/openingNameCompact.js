/**
 * Strip move-tree suffixes from verbose PGN/Chess.com opening headers.
 */

const MOVE_SEGMENT_RE = /^\d+\./;
const MOVE_TAIL_RE = /\s+\d+\.\s*.*$/;
const INLINE_MOVE_TAIL_RE = /\d+\.[NBRQKO].*$/i;

export const compactOpeningName = (openingName) => {
  let text = String(openingName || '').trim();
  if (!text) {
    return '';
  }

  const ellipsisIndex = text.indexOf('...');
  if (ellipsisIndex !== -1) {
    text = text.slice(0, ellipsisIndex).trim();
  }

  const segments = text.split(',').map((part) => part.trim());
  const kept = [];
  for (const segment of segments) {
    if (MOVE_SEGMENT_RE.test(segment) || INLINE_MOVE_TAIL_RE.test(segment)) {
      break;
    }
    kept.push(segment);
  }
  text = kept.length > 0 ? kept.join(', ') : text;

  text = text.replace(MOVE_TAIL_RE, '').trim();
  text = text.replace(INLINE_MOVE_TAIL_RE, '').trim();
  text = text.replace(/\s+/g, ' ').trim();
  return text;
};

/**
 * Build a focused Lichess study search query — variation name + ECO when available.
 */
export const buildOpeningStudyQuery = (openingName, ecoCode = null, playerColor = null) => {
  const compacted = compactOpeningName(openingName);
  if (!compacted) {
    return 'chess opening';
  }

  let query = compacted;
  if (compacted.includes(':')) {
    const variation = compacted.split(':').slice(1).join(':').trim();
    if (variation) {
      query = variation;
    }
  }

  const eco = String(ecoCode || '').trim().toUpperCase();
  if (eco && !query.toUpperCase().includes(eco)) {
    query = `${query} ${eco}`;
  }

  const color = String(playerColor || '').trim().toLowerCase();
  if (color === 'white' || color === 'black') {
    query = `${query} ${color}`;
  }

  return query.trim();
};
