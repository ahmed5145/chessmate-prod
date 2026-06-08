/**
 * Anonymized Batch Coach report for marketing (landing preview + /example/batch-report).
 * Shape matches getBatchReport / getPublicBatchReport API payloads.
 */

const OPPONENTS = ['Opponent A', 'Opponent B', 'Opponent C'];

const buildPerGameResults = () => {
  const specs = [
    { opening_name: 'Sicilian Defense: Najdorf', eco_code: 'B90', result: '0-1', platform: 'lichess' },
    { opening_name: 'Italian Game', eco_code: 'C50', result: '1-0', platform: 'chess.com' },
    { opening_name: 'Queen\'s Gambit Declined', eco_code: 'D30', result: '0-1', platform: 'lichess' },
    { opening_name: 'Caro-Kann Defense', eco_code: 'B12', result: '1-0', platform: 'chess.com' },
    { opening_name: 'Sicilian Defense: Najdorf', eco_code: 'B90', result: '0-1', platform: 'lichess' },
    { opening_name: 'Ruy Lopez', eco_code: 'C78', result: '1/2-1/2', platform: 'chess.com' },
    { opening_name: 'Italian Game', eco_code: 'C53', result: '0-1', platform: 'lichess' },
    { opening_name: 'French Defense', eco_code: 'C00', result: '1-0', platform: 'chess.com' },
  ];

  return specs.map((spec, index) => {
    const playerColor = index % 2 === 0 ? 'white' : 'black';
    const opponent = OPPONENTS[index % OPPONENTS.length];
    const white = playerColor === 'white' ? 'You' : opponent;
    const black = playerColor === 'black' ? 'You' : opponent;
    const gameId = `game_${index}`;

    return {
      game_id: gameId,
      white,
      black,
      player_color: playerColor,
      opponent,
      platform: spec.platform,
      platform_game_url: null,
      opening_name: spec.opening_name,
      eco_code: spec.eco_code,
      result: spec.result,
      total_moves: 38 + index,
      phase_breakdown: {
        opening: { moves: 8 + (index % 3), avg_eval_drop: index % 2 === 0 ? 0.35 : 0.18 },
        middlegame: { moves: 22, avg_eval_drop: 0.22 },
        endgame: { moves: 10, avg_eval_drop: 0.15 },
      },
      critical_moments: index === 0
        ? [{
          move_number: 18,
          type: 'blunder',
          fen: 'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 5',
          played_move: 'Qh5',
          best_move: 'O-O',
          eval_swing: 2.8,
          explanation: 'A premature queen sortie allowed a counterattack on the kingside.',
          played_move_uci: 'd1h5',
          best_move_uci: 'e1g1',
        }]
        : [],
    };
  });
};

export const DEMO_BATCH_REPORT = {
  status: 'completed',
  games_count: 8,
  batch_summary: {
    games_analyzed: 8,
    date_range: 'Apr 2025',
    overall_accuracy_pct: 71.4,
    worst_phase: 'opening',
    phase_performance: {
      opening: { score: 0.58, trend: 'weak' },
      middlegame: { score: 0.74, trend: 'inconsistent' },
      endgame: { score: 0.81, trend: 'strong' },
    },
    recurring_weaknesses: [
      {
        pattern: 'hanging_piece',
        frequency: '3x',
        impact: 'high',
        detail: 'Undefended pieces were punished in the opening and middlegame.',
        example_game_ids: ['game_0', 'game_4'],
      },
      {
        pattern: 'opening_inaccuracy',
        frequency: '4x',
        impact: 'medium',
        detail: 'Slow development in familiar Sicilian lines cost tempo.',
        example_game_ids: ['game_0', 'game_4'],
      },
    ],
    repertoire_gaps: [
      {
        opening_name: 'Sicilian Defense: Najdorf',
        eco_code: 'B90',
        player_color: 'white',
        record: '0W-2L-0D',
        summary: 'Both losses started from the same move-order — review White\'s anti-Najdorf setup.',
      },
    ],
    opening_insights: [
      {
        opening_name: 'Italian Game',
        eco_code: 'C50',
        games: 2,
        record: '1W-1L-0D',
        status: 'mixed',
      },
    ],
    rating_band_coaching: {
      label: '1200–1400',
      focus: 'Prioritize king safety and one-move tactics before captures.',
      daily_drill: '10 easy–medium puzzles (forks & pins)',
    },
    strength_patterns: [
      {
        pattern: 'endgame_technique',
        detail: 'You converted rook endings without major inaccuracies.',
        frequency: '3/8 games',
      },
    ],
    time_management_summary: {
      insight: 'Clock use was steady — no major time-scramble blunders in this batch.',
      games_with_clock_data: 6,
      games_analyzed: 8,
      pattern: 'stable',
    },
  },
  coaching_report: {
    executive_summary:
      'Opening preparation is your biggest leak: Najdorf lines cost material twice. '
      + 'Middlegame tactics are serviceable, and endgames are a relative strength. '
      + 'Focus this week on anti-Sicilian development and hanging-piece scans.',
    one_thing_to_do_today: 'Play 15 fork/pin puzzles, then review one Najdorf loss move-by-move.',
    top_3_priorities: [
      {
        rank: 1,
        title: 'Fix Najdorf prep as White (game_0, game_4)',
        why_it_matters: 'You lost both Najdorf games before move 15 from slow development and hanging pieces.',
        how_to_fix: 'Learn a single anti-Najdorf line: 3. Bb5+ or 6. Be3 with castling before chasing pawns.',
        specific_drill: 'Practice: 10 puzzles on undefended pieces, then replay game_0 moves 1–15.',
      },
      {
        rank: 2,
        title: 'Scan for hanging pieces every move',
        why_it_matters: 'Three games in this batch included a one-move tactic you missed.',
        how_to_fix: 'Before each capture or check, ask: "What is undefended?"',
        specific_drill: 'Practice: 10 hanging-piece puzzles daily for one week.',
      },
      {
        rank: 3,
        title: 'Convert Italian Game advantages',
        why_it_matters: 'You reached good middlegames but did not always press the initiative.',
        how_to_fix: 'When up material, trade into simpler endgames rather than opening the position.',
        specific_drill: 'Review game_1 and note where you could trade queens earlier.',
      },
    ],
    coaching_narrative: {
      opening: 'Najdorf and early development need structured prep — not improvisation.',
      middlegame: 'Tactics are adequate when you have time; blunders cluster in fast openings.',
      endgame: 'Rook endings are a bright spot — keep building on conversion habits.',
    },
    training_plan: {
      week_1: 'Daily hanging-piece puzzles + one anti-Najdorf study chapter.',
      week_2: 'Replay both Najdorf losses; annotate moves 1–20.',
      week_3: 'Italian Game model games — focus on simplifying when ahead.',
      week_4: 'Blitz session with pre-game checklist: develop, castle, scan.',
    },
  },
  per_game_results: buildPerGameResults(),
  errors: [],
};

export const getDemoBatchReport = () => DEMO_BATCH_REPORT;

export default DEMO_BATCH_REPORT;
