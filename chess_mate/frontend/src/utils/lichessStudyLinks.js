/**
 * Map batch weakness themes to Lichess study URLs (puzzles, openings, endgames).
 */

const PUZZLE_THEME_SLUGS = {
  fork: 'fork',
  pin: 'pin',
  skewer: 'skewer',
  hanging_piece: 'hangingPiece',
  hangingpiece: 'hangingPiece',
  discovered_attack: 'discoveredAttack',
  double_check: 'doubleCheck',
  back_rank: 'backRankMate',
  back_rank_mate: 'backRankMate',
  trapped_piece: 'trappedPiece',
  mate_in_1: 'mateIn1',
  mate_in_2: 'mateIn2',
  mate_in_3: 'mateIn3',
  sacrifice: 'sacrifice',
  defensive_move: 'defensiveMove',
  attacking_f2_f7: 'attackingF2F7',
  advanced_pawn: 'advancedPawn',
  promotion: 'promotion',
  zugzwang: 'zugzwang',
  xray_attack: 'xRayAttack',
  interference: 'interference',
  quiet_move: 'quietMove',
  very_long: 'veryLong',
  equality: 'equality',
  advantage: 'advantage',
  crushing: 'crushing',
  tactical_oversight: null
};

const ENDGAME_PRACTICE_URLS = {
  rook_and_pawn: 'https://lichess.org/practice/endgames/rook',
  rook_endgame: 'https://lichess.org/practice/endgames/rook',
  king_and_pawn: 'https://lichess.org/learn#king',
  queen_endgame: 'https://lichess.org/learn#queen',
  general_endgame: 'https://lichess.org/learn'
};

const normalizeThemeKey = (theme) =>
  String(theme || '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '_');

export const lichessPuzzleUrlForTheme = (theme) => {
  const key = normalizeThemeKey(theme);
  const slug = PUZZLE_THEME_SLUGS[key];
  if (slug) {
    return `https://lichess.org/training/${slug}`;
  }
  return 'https://lichess.org/training';
};

export const lichessOpeningSearchUrl = (openingName) =>
  `https://lichess.org/analysis?q=${encodeURIComponent(openingName || 'opening')}`;

export const lichessEndgamePracticeUrl = (endgameType) => {
  const key = normalizeThemeKey(endgameType);
  return ENDGAME_PRACTICE_URLS[key] || ENDGAME_PRACTICE_URLS.general_endgame;
};

export const collectStudyLinksFromBatchSummary = (batchSummary) => {
  if (!batchSummary || typeof batchSummary !== 'object') {
    return [];
  }

  const links = [];
  const seen = new Set();

  const addLink = (label, url, kind) => {
    const dedupe = `${kind}:${url}`;
    if (!url || seen.has(dedupe)) {
      return;
    }
    seen.add(dedupe);
    links.push({ label, url, kind });
  };

  (batchSummary.recurring_weaknesses || []).forEach((item) => {
    const pattern = item?.pattern;
    if (!pattern) {
      return;
    }
    addLink(
      `${String(pattern).replace(/_/g, ' ')} puzzles`,
      lichessPuzzleUrlForTheme(pattern),
      'puzzle'
    );
  });

  (batchSummary.repertoire_gaps || batchSummary.opening_insights || [])
    .filter((item) => item?.status === 'struggling' || item?.status === 'needs_work')
    .slice(0, 3)
    .forEach((item) => {
      const name = item.opening_name;
      if (!name) {
        return;
      }
      const color = item.player_color ? ` (${item.player_color})` : '';
      addLink(
        `Study ${name}${color}`,
        lichessOpeningSearchUrl(name),
        'opening'
      );
    });

  (batchSummary.endgame_insights || []).slice(0, 3).forEach((item) => {
    const type = item.endgame_type || item.label;
    if (!type) {
      return;
    }
    const url = item.study_url || lichessEndgamePracticeUrl(type);
    addLink(
      `${String(item.label || type).replace(/_/g, ' ')} practice`,
      url,
      'endgame'
    );
  });

  return links.slice(0, 8);
};
