/** User-facing labels for imported game platforms. */

export const formatGamePlatformLabel = (platform) => {
  const normalized = String(platform || '').trim().toLowerCase();
  if (!normalized || normalized === 'unknown') {
    return null;
  }
  if (normalized === 'chess.com' || normalized === 'chesscom') {
    return 'Chess.com';
  }
  if (normalized === 'lichess') {
    return 'Lichess';
  }
  return String(platform).trim();
};
