import { findGameResultById } from './formatGameLabel';

export const isUnknownOpening = (name) => {
  const normalized = String(name || '').trim().toLowerCase();
  return !normalized || normalized === 'unknown' || normalized === 'unknown opening';
};

export const scrollToBatchGame = (gameId) => {
  if (!gameId) {
    return;
  }
  const element = document.getElementById(`batch-game-${gameId}`);
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
};

export const getGamePlatformUrl = (perGameResults, gameId) => {
  const game = findGameResultById(perGameResults, gameId);
  return game?.platform_game_url || null;
};

export const getGamePlatformLabel = (perGameResults, gameId) => {
  const game = findGameResultById(perGameResults, gameId);
  if (!game?.platform) {
    return 'platform';
  }
  return game.platform === 'chess.com' ? 'Chess.com' : game.platform;
};
