/**
 * Title-case labels for UI (e.g. "hanging piece" → "Hanging Piece").
 */
export const toTitleCase = (value) => {
  if (!value) {
    return '';
  }
  return String(value)
    .replace(/_/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};
