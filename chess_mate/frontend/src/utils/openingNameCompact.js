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
