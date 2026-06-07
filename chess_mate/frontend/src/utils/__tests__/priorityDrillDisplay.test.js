import { buildPriorityDrillDisplay } from '../priorityDrillDisplay';

describe('buildPriorityDrillDisplay', () => {
  const games = [
    { game_id: 'game_1', opponent: 'rival', date_played: '2025-04-04' },
  ];

  it('splits structured practice and review drills', () => {
    const display = buildPriorityDrillDisplay(
      {
        title: 'Address Hanging Pieces',
        how_to_fix: 'Study piece safety.',
        specific_drill:
          'Practice: 15 hanging-piece puzzles on Lichess. Review: game_1 move 11 — replay the tactic.',
      },
      games
    );
    expect(display.practice).toMatch(/hanging-piece puzzles/i);
    expect(display.review).toMatch(/move 11/i);
  });

  it('adds a general practice drill for legacy single-game text', () => {
    const display = buildPriorityDrillDisplay(
      {
        title: 'Address Hanging Pieces',
        how_to_fix: 'Study piece safety.',
        specific_drill: 'In game_1 move 11... Qxg4 (hanging piece oversight)',
      },
      games
    );
    expect(display.practice).toMatch(/hanging-piece puzzles/i);
    expect(display.review).toMatch(/vs rival/i);
  });
});
