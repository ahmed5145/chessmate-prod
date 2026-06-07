/**
 * Shared text helpers for batch report hero + executive summary.
 */

export const splitSummaryBullets = (text) => {
  if (!text || typeof text !== 'string') {
    return [];
  }
  return text
    .split(/\n+|(?<=[.!?])\s+/)
    .map((line) => line.trim())
    .filter((line) => line.length > 12)
    .slice(0, 6);
};

export const extractExecutiveTakeaway = (coachingReport) => {
  const text = coachingReport?.executive_summary?.trim();
  if (!text) {
    return null;
  }
  const bullets = splitSummaryBullets(text);
  if (bullets.length > 0) {
    return bullets[0];
  }
  const firstSentence = text.split(/(?<=[.!?])\s+/)[0]?.trim();
  if (firstSentence && firstSentence.length >= 20) {
    return firstSentence;
  }
  return text.length > 220 ? `${text.slice(0, 217)}…` : text;
};

export const hasCoachingPriorities = (coachingReport) => (
  Boolean(
    coachingReport?.top_3_priorities?.length > 0
  )
);
