import { buildPriorityDrillDisplay } from '../priorityDrillDisplay';

describe('buildPriorityDrillDisplay', () => {
  const games = [
    { game_id: 'game_1', opponent: 'rival', date_played: '2025-04-04' },
    { game_id: 'game_2', opponent: 'Sembiringkembaren', date_played: '2025-05-16' },
  ];

  it('returns one consolidated paragraph for structured drills', () => {
    const text = buildPriorityDrillDisplay(
      {
        title: 'Address Tactical Oversights',
        how_to_fix: 'Analyze missed tactics.',
        specific_drill:
          'Practice: 15 tactical puzzles focusing on hanging pieces. Review: game_2 move 16 — replay the Nxb4 tactic and alternatives.',
      },
      games
    );
    expect(text).toMatch(/15 tactical puzzles/i);
    expect(text).toMatch(/Then replay/i);
    expect(text).toMatch(/Sembiringkembaren/i);
    expect(text).not.toMatch(/Practice:/i);
    expect(text).not.toMatch(/Review:/i);
  });

  it('returns a single line for legacy game-specific drills with theme fallback', () => {
    const text = buildPriorityDrillDisplay(
      {
        title: 'Address Hanging Pieces',
        how_to_fix: 'Study piece safety.',
        specific_drill: 'In game_1 move 11... Qxg4 (hanging piece oversight)',
      },
      games
    );
    expect(text).toMatch(/hanging-piece puzzles/i);
    expect(text).toMatch(/vs rival/i);
    expect(typeof text).toBe('string');
    expect(text.split('\n')).toHaveLength(1);
  });
});
