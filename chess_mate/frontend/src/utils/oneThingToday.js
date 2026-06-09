/** SRG-12 — dashboard “one thing today” card + 24h snooze. */

const SNOOZE_KEY = 'chessmate_one_thing_snooze_until';
const SNOOZE_MS = 24 * 60 * 60 * 1000;

export const normalizeOneThingToday = (raw) => {
  if (!raw || typeof raw !== 'object') {
    return null;
  }
  const ctaTo = raw.ctaTo || raw.cta_to;
  if (!ctaTo) {
    return null;
  }
  return {
    headline: raw.headline || 'One thing today',
    subline: raw.subline || '',
    ctaLabel: raw.ctaLabel || raw.cta_label || '5 min drill',
    ctaTo,
    source: raw.source || 'unknown',
    drillMinutes: raw.drillMinutes ?? raw.drill_minutes ?? 5,
  };
};

export const isOneThingSnoozed = () => {
  if (typeof window === 'undefined') {
    return false;
  }
  try {
    const until = Number(localStorage.getItem(SNOOZE_KEY) || 0);
    return Number.isFinite(until) && until > Date.now();
  } catch {
    return false;
  }
};

export const snoozeOneThingToday = () => {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    localStorage.setItem(SNOOZE_KEY, String(Date.now() + SNOOZE_MS));
  } catch {
    // ignore quota errors
  }
};

export const resolveOneThingToday = (dashboardData = {}) => {
  if (isOneThingSnoozed()) {
    return null;
  }
  return normalizeOneThingToday(
    dashboardData.oneThingToday || dashboardData.one_thing_today
  );
};
