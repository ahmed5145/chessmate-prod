import { formatGameLabel, formatGameLabelById } from '../formatGameLabel';

describe('formatGameLabel', () => {
  it('formats opponent and date', () => {
    expect(
      formatGameLabel({
        opponent: 'rival42',
        date_played: '2024-06-15T12:00:00Z',
      })
    ).toMatch(/vs rival42 —/);
  });

  it('falls back to game index label', () => {
    expect(formatGameLabel({ game_id: 'game_0' })).toBe('Game 1');
  });
});

describe('formatGameLabelById', () => {
  it('looks up game metadata from per_game_results', () => {
    const label = formatGameLabelById(
      [{ game_id: 'game_0', opponent: 'alice', date_played: '2024-01-02' }],
      'game_0'
    );
    expect(label).toContain('vs alice');
  });
});
