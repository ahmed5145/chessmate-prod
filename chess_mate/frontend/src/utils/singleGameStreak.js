export const MIN_STREAK_TO_SHOW = 2;

export const normalizeStreakState = (value) => {
  const count = Number(value?.count);
  return {
    count: Number.isFinite(count) && count > 0 ? Math.floor(count) : 0,
    lastGameId: value?.last_game_id ?? value?.lastGameId ?? null,
    updatedAt: value?.updated_at ?? value?.updatedAt ?? null,
  };
};

export const shouldShowSingleGameStreak = (streakState) => (
  normalizeStreakState(streakState).count >= MIN_STREAK_TO_SHOW
);

export const formatSingleGameStreakCopy = (streakState) => {
  const { count } = normalizeStreakState(streakState);
  if (count < MIN_STREAK_TO_SHOW) {
    return null;
  }
  const gameLabel = count === 1 ? 'game' : 'games';
  return `${count} ${gameLabel} without a 1+ pawn blunder`;
};
