/**
 * Batch coach duration estimates for user-facing copy.
 * Based on prod: SEQUENTIAL_BATCH_ANALYSIS=true, BATCH_ANALYSIS_DEPTH=14 (~3–5 min/game).
 */

const DEFAULT_MINUTES_PER_GAME_LOW = 3;
const DEFAULT_MINUTES_PER_GAME_HIGH = 5;
const DEFAULT_TYPICAL_MINUTES_PER_GAME = 4;
const DEFAULT_COACHING_BUFFER_MINUTES = 2;

export function estimateBatchDurationMinutes(gameCount, options = {}) {
  const low = options.minutesPerGameLow ?? DEFAULT_MINUTES_PER_GAME_LOW;
  const high = options.minutesPerGameHigh ?? DEFAULT_MINUTES_PER_GAME_HIGH;
  const typical = options.typicalMinutesPerGame ?? DEFAULT_TYPICAL_MINUTES_PER_GAME;
  const buffer = options.coachingBufferMinutes ?? DEFAULT_COACHING_BUFFER_MINUTES;
  const count = Math.max(0, Number(gameCount) || 0);

  if (count === 0) {
    return { minMinutes: 0, maxMinutes: 0, typicalMinutes: 0 };
  }

  return {
    minMinutes: Math.max(1, Math.ceil(count * low + buffer)),
    maxMinutes: Math.max(1, Math.ceil(count * high + buffer)),
    typicalMinutes: Math.max(1, Math.ceil(count * typical + buffer)),
  };
}

export function formatBatchDurationRange(gameCount, options = {}) {
  const { minMinutes, maxMinutes, typicalMinutes } = estimateBatchDurationMinutes(gameCount, options);
  if (!typicalMinutes) {
    return '';
  }
  if (minMinutes >= maxMinutes) {
    return `about ${typicalMinutes} minute${typicalMinutes === 1 ? '' : 's'}`;
  }
  return `about ${minMinutes}–${maxMinutes} minutes`;
}

/** Seconds for countdown UI (typical case). */
export function estimateBatchDurationSeconds(gameCount, options = {}) {
  const { typicalMinutes } = estimateBatchDurationMinutes(gameCount, options);
  return typicalMinutes * 60;
}
