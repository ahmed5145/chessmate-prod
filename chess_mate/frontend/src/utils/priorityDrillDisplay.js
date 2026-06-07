import { humanizeGameIdInText } from './formatGameLabel';

const THEME_DRILLS = {
  hanging_piece:
    'Practice 10–15 hanging-piece puzzles (Lichess Training or Chess.com puzzles). Before each move, name every undefended piece.',
  fork: 'Practice fork and double-attack puzzles. Look for knight forks and moves that attack two targets at once.',
  pin: 'Practice pin and skewer puzzles. Trace lines from enemy bishops, rooks, and queens to your king or queen.',
  skewer: 'Practice skewer tactics — attack a valuable piece first to win material behind it.',
  missed_tactic:
    'Practice 15–20 mixed tactics at your rating. Pause on forcing moves: checks, captures, and threats.',
  tactical_oversight:
    'Practice 15–20 mixed tactics at your rating. Pause on forcing moves: checks, captures, and threats.',
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

export const buildPriorityDrillDisplay = (priority, perGameResults = []) => {
  const humanized = humanizeGameIdInText(priority?.specific_drill || '', perGameResults);
  const structured = splitStructuredDrill(humanized);

  if (structured) {
    return {
      practice: structured.practice,
      review: structured.review,
    };
  }

  const themeKey = inferThemeKey(priority?.title);
  return {
    practice: THEME_DRILLS[themeKey] || priority?.how_to_fix || null,
    review: humanized || null,
  };
};
