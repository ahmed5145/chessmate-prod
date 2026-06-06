/**
 * Resolve game time control category (bullet / blitz / rapid / classical).
 * Matches backend Game.get_time_control_category() semantics.
 */

const NAMED = new Set(['bullet', 'blitz', 'rapid', 'classical']);

export const getTimeControlCategory = (game) => {
  if (!game) {
    return null;
  }

  const candidates = [
    game.time_control_category,
    game.time_control_type,
    game.time_control
  ];

  for (const raw of candidates) {
    if (!raw) {
      continue;
    }
    const normalized = String(raw).trim().toLowerCase();
    if (NAMED.has(normalized)) {
      return normalized;
    }
  }

  const timeControl = game.time_control;
  if (!timeControl) {
    return null;
  }

  const lower = String(timeControl).trim().toLowerCase();
  if (NAMED.has(lower)) {
    return lower;
  }

  if (lower.includes('bullet')) return 'bullet';
  if (lower.includes('blitz')) return 'blitz';
  if (lower.includes('rapid')) return 'rapid';
  if (lower.includes('classical') || lower.includes('daily')) return 'classical';

  try {
    const parts = String(timeControl).split('+');
    const baseTime = parseInt(parts[0], 10);
    if (Number.isNaN(baseTime)) {
      return null;
    }
    const increment = parts.length > 1 ? parseInt(parts[1], 10) || 0 : 0;
    const totalTime = baseTime + increment * 40;
    if (totalTime < 180) return 'bullet';
    if (totalTime < 600) return 'blitz';
    if (totalTime < 1800) return 'rapid';
    return 'classical';
  } catch (_) {
    return null;
  }
};
