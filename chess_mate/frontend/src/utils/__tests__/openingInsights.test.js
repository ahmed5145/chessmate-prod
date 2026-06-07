import {
  buildOpeningInsightsFromGames,
  buildPerGameOpeningInsights,
  resolveOpeningInsights,
  resolveRepertoireGaps,
} from '../openingInsights';

describe('openingInsights', () => {
  const games = [
    {
      game_id: 'game_0',
      result: '0-1',
      player_color: 'white',
      opening_name: "Queen's Pawn Game",
      eco_code: 'D00',
      phase_breakdown: { opening: { moves: 8, avg_eval_drop: 0.3 } },
    },
    {
      game_id: 'game_1',
      result: '0-1',
      player_color: 'white',
      opening_name: "Queen's Pawn Game: London System",
      eco_code: 'D00',
      phase_breakdown: { opening: { moves: 10, avg_eval_drop: 0.35 } },
    },
    {
      game_id: 'game_2',
      result: '1-0',
      player_color: 'white',
      opening_name: 'Sicilian Defense',
      eco_code: 'B90',
      phase_breakdown: { opening: { moves: 9, avg_eval_drop: 0.2 } },
    },
  ];

  it('groups ECO variants and includes neutral openings', () => {
    const insights = buildOpeningInsightsFromGames(games);
    const queensPawn = insights.find((item) => item.opening_name.includes('Queen'));
    expect(queensPawn).toBeDefined();
    expect(queensPawn.games).toBe(2);
    expect(queensPawn.status).toBe('struggling');
    expect(insights.some((item) => item.opening_name === 'Sicilian Defense')).toBe(true);
  });

  it('returns one row per game with opening data', () => {
    const insights = buildPerGameOpeningInsights(games);
    expect(insights).toHaveLength(3);
    expect(insights.every((row) => row.games === 1)).toBe(true);
  });

  it('prefers per-game rows when per_game_results are available', () => {
    const insights = resolveOpeningInsights({}, games);
    expect(insights).toHaveLength(3);
  });

  it('resolves repertoire gaps from batch summary', () => {
    const gaps = resolveRepertoireGaps(
      {
        repertoire_gaps: [{ opening_name: "Queen's Pawn Game", status: 'struggling', record: '0W-2L-0D' }],
      },
      games
    );
    expect(gaps.some((gap) => gap.opening_name.includes('Queen'))).toBe(true);
  });
});
