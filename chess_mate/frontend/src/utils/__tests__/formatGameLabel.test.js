import { formatGameLabel, formatGameLabelById, humanizeGameIdInText } from '../formatGameLabel';

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

describe('humanizeGameIdInText', () => {
  const games = [
    { game_id: 'game_0', opponent: 'alice', date_played: '2024-01-02' },
    { game_id: 'game_1', opponent: 'bob', date_played: '2024-02-03' },
  ];

  it('replaces the current game id with "this game"', () => {
    const text = 'In game_0, at move 19, you played Rac8.';
    expect(humanizeGameIdInText(text, games, { inThisGameId: 'game_0' })).toBe(
      'In this game, at move 19, you played Rac8.'
    );
  });

  it('replaces other game ids with opponent labels', () => {
    const text = 'In game_1 move 11, review hanging pieces.';
    expect(humanizeGameIdInText(text, games)).toMatch(/vs bob/);
    expect(humanizeGameIdInText(text, games)).toMatch(/move 11/);
  });
});
