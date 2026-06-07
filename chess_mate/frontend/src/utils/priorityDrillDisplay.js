import { humanizeGameIdInText } from './formatGameLabel';

const THEME_DRILLS = {
  hanging_piece: 'Do 10–15 hanging-piece puzzles. Before each move, name every undefended piece.',
  fork: 'Do fork and double-attack puzzles. Look for knight forks and moves that hit two targets.',
  pin: 'Do pin and skewer puzzles. Trace lines from enemy bishops, rooks, and queens.',
  skewer: 'Do skewer tactics — attack a valuable piece first to win material behind it.',
  missed_tactic: 'Do 15–20 mixed tactics at your rating. Pause on checks, captures, and threats.',
  tactical_oversight: 'Do 15–20 mixed tactics at your rating. Pause on checks, captures, and threats.',
};

const inferThemeKey = (title = '') => {
  const normalized = String(title).toLowerCase();
  if (normalized.includes('hanging')) return 'hanging_piece';
  if (normalized.includes('fork')) return 'fork';
  if (normalized.includes('pin')) return 'pin';
  if (normalized.includes('skewer')) return 'skewer';
  if (normalized.includes('tactic')) return 'missed_tactic';
  return 'missed_tactic';
};

const splitStructuredDrill = (text) => {
  const practiceMatch = text.match(/Practice:\s*([\s\S]+?)(?=\s*Review:|$)/i);
  const reviewMatch = text.match(/Review:\s*([\s\S]+)$/i);
  if (practiceMatch || reviewMatch) {
    return {
      practice: practiceMatch?.[1]?.trim() || null,
      review: reviewMatch?.[1]?.trim() || null,
    };
  }
  return null;
};

const cleanPracticeLine = (text) => {
  if (!text) {
    return '';
  }
  return text
    .replace(/^practice[:\s]*/i, '')
    .replace(/^do\s+/i, 'Do ')
    .trim()
    .replace(/\s+/g, ' ');
};

const cleanReviewLine = (text) => {
  if (!text) {
    return '';
  }
  return text
    .replace(/^review[:\s]*/i, '')
    .trim()
    .replace(/\s+/g, ' ');
};

const ensureSentence = (text) => {
  const trimmed = (text || '').trim();
  if (!trimmed) {
    return '';
  }
  return /[.!?]$/.test(trimmed) ? trimmed : `${trimmed}.`;
};

const combineDrillParts = (practice, review) => {
  const practiceLine = cleanPracticeLine(practice);
  const reviewLine = cleanReviewLine(review);

  if (practiceLine && reviewLine) {
    const reviewLower = reviewLine.charAt(0).toLowerCase() + reviewLine.slice(1);
    if (/^(vs\s|in\s)/i.test(reviewLine)) {
      return `${ensureSentence(practiceLine)} Then replay ${reviewLower}`;
    }
    if (/^move\s\d/i.test(reviewLine)) {
      return `${ensureSentence(practiceLine)} Then ${reviewLower}`;
    }
    return `${ensureSentence(practiceLine)} Then ${reviewLower}`;
  }

  if (practiceLine) {
    return ensureSentence(practiceLine);
  }
  if (reviewLine) {
    return ensureSentence(reviewLine);
  }
  return '';
};

const isGameSpecificLine = (text) => /vs\s|move\s\d|replay/i.test(text || '');

const practiceOverlaps = (practice, review) => {
  const p = cleanPracticeLine(practice).toLowerCase();
  const r = (review || '').toLowerCase();
  if (!p || !r) {
    return false;
  }
  return (
    (p.includes('puzzle') && r.includes('puzzle'))
    || (p.includes('tactic') && r.includes('tactic') && p.length > 20 && r.length > 20)
  );
};

/**
 * Single consolidated drill paragraph for priority cards (no nested Practice / Review labels).
 */
export const buildPriorityDrillDisplay = (priority, perGameResults = []) => {
  const humanized = humanizeGameIdInText(priority?.specific_drill || '', perGameResults);
  const structured = splitStructuredDrill(humanized);

  if (structured) {
    if (structured.practice && structured.review && practiceOverlaps(structured.practice, structured.review)) {
      return ensureSentence(cleanReviewLine(structured.review) || cleanPracticeLine(structured.practice));
    }
    const combined = combineDrillParts(structured.practice, structured.review);
    if (combined) {
      return combined;
    }
  }

  const themeKey = inferThemeKey(priority?.title);
  const themeDrill = THEME_DRILLS[themeKey] || null;

  if (isGameSpecificLine(humanized)) {
    if (/puzzle|tactic|drill/i.test(humanized) && !themeDrill) {
      return ensureSentence(humanized);
    }
    return combineDrillParts(themeDrill, humanized) || ensureSentence(humanized);
  }

  if (humanized) {
    return ensureSentence(humanized);
  }

  return themeDrill ? ensureSentence(themeDrill) : '';
};
