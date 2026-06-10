/**
 * Shared metric definitions for batch + single-game reports.
 * Keep coaching copy and UI tooltips aligned on what each number means.
 */

export const METRIC_GLOSSARY = {
  move_match: {
    shortLabel: 'Move match %',
    description:
      'Chess.com-style score: how often your moves matched Stockfish’s top line. Higher means closer engine play — not win rate.',
  },
  eval_stability: {
    shortLabel: 'Eval stability',
    description:
      'How steadily your evaluation held across positions (1 − average eval drop). Different from move match % — you can play engine moves and still lose stability after a blunder.',
  },
  phase_move_match: {
    shortLabel: 'Phase move match',
    description:
      'Move match % split by opening, middlegame, or endgame — same formula as the header, scoped to that phase.',
  },
  single_game_accuracy: {
    shortLabel: 'Move match %',
    description:
      'Your move match for this game (depth 20). Chess.com-style from centipawn loss on each of your moves.',
  },
  single_game_phase_accuracy: {
    shortLabel: 'Phase move match',
    description:
      'Move match % for opening, middlegame, or endgame in this game only.',
  },
  eval_swing: {
    shortLabel: 'Eval swing',
    description:
      'How much the position evaluation shifted against you on a move (in pawns). Larger swings = bigger turning points.',
  },
  acpl: {
    shortLabel: 'ACPL',
    description:
      'Average centipawn loss per move — lower is better. Complements move match % with magnitude of mistakes.',
  },
};

export const BATCH_METRIC_KEYS = ['move_match', 'eval_stability', 'phase_move_match'];

export const formatMetricTooltip = (keys) => {
  const list = Array.isArray(keys) ? keys : [keys];
  return list
    .map((key) => METRIC_GLOSSARY[key])
    .filter(Boolean)
    .map((entry) => `${entry.shortLabel}: ${entry.description}`)
    .join('\n\n');
};
