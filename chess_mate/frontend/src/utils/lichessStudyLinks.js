/**
 * Map batch weakness themes to Lichess study URLs (puzzles, openings, endgames).
 */

import { toTitleCase } from './formatLabel';
import { compactOpeningName } from './openingNameCompact';

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
  rook_and_pawn: 'https://lichess.org/learn#/1',
  rook_endgame: 'https://lichess.org/learn#/1',
  king_and_pawn: 'https://lichess.org/learn#/6',
  queen_endgame: 'https://lichess.org/learn#/3',
  minor_piece_endgame: 'https://lichess.org/learn',
  pawn_structure_endgame: 'https://lichess.org/learn#/6',
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

export const lichessOpeningSearchUrl = (openingName) => {
  const query = compactOpeningName(openingName) || 'opening';
  const params = new URLSearchParams({ order: 'hot', q: query });
  return `https://lichess.org/study/search?${params.toString()}`;
};

export const lichessEndgamePracticeUrl = (endgameType) => {
  const key = normalizeThemeKey(endgameType);
  return ENDGAME_PRACTICE_URLS[key] || ENDGAME_PRACTICE_URLS.general_endgame;
};

const inferPriorityThemeKey = (priority = {}) => {
  const combined = [priority.title, priority.how_to_fix, priority.specific_drill]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();

  if (combined.includes('hanging')) return 'hanging_piece';
  if (combined.includes('fork')) return 'fork';
  if (combined.includes('pin')) return 'pin';
  if (combined.includes('skewer')) return 'skewer';
  if (combined.includes('tactic')) return 'missed_tactic';
  return 'missed_tactic';
};

const cleanExtractedOpeningName = (name) => {
  const compacted = compactOpeningName(name);
  return compacted || String(name || '').trim() || null;
};

const extractOpeningNameFromPriority = (priority = {}) => {
  const sources = [priority.title, priority.how_to_fix, priority.specific_drill].filter(Boolean);

  for (const raw of sources) {
    const text = String(raw);

    const fromTheory = text.match(/opening theory on\s+(.+?)(?:\s+to\b|[.;]|$)/i);
    if (fromTheory?.[1]) {
      return cleanExtractedOpeningName(fromTheory[1]);
    }

    const fromIdeas = text.match(/ideas from (?:the\s+)?(.+?)(?:\s+to\b|[.;]|$)/i);
    if (fromIdeas?.[1]) {
      return cleanExtractedOpeningName(fromIdeas[1]);
    }

    const fromMasters = text.match(/masters in (?:the\s+)?(.+?)(?:\s*[.;]|$)/i);
    if (fromMasters?.[1]) {
      return cleanExtractedOpeningName(fromMasters[1]);
    }

    const quotedOpening = text.match(/(?:Queen's|King's|London|Sicilian|Caro|French|Slav|Indian)[^.;]*/i);
    if (quotedOpening?.[0]) {
      return cleanExtractedOpeningName(quotedOpening[0]);
    }
  }

  return null;
};

const isEndgamePriority = (priority = {}) => {
  const combined = [priority.title, priority.how_to_fix, priority.specific_drill]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
  return /endgame|king activation|passed pawn|rook ending|pawn ending/.test(combined);
};

const isOpeningPriority = (priority = {}) => {
  const combined = [priority.title, priority.how_to_fix, priority.specific_drill]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
  return /opening|repertoire|london system|queen'?s pawn|theory/.test(combined)
    || Boolean(extractOpeningNameFromPriority(priority));
};

/**
 * Map a single top-3 priority to a Lichess study / puzzle / endgame URL.
 */
export const resolvePriorityLichessLink = (priority) => {
  if (!priority || typeof priority !== 'object') {
    return null;
  }

  if (isEndgamePriority(priority)) {
    return {
      label: 'Practice on Lichess',
      url: lichessEndgamePracticeUrl('general_endgame'),
      kind: 'endgame',
    };
  }

  if (isOpeningPriority(priority)) {
    const openingName = extractOpeningNameFromPriority(priority) || 'opening repertoire';
    return {
      label: 'Study on Lichess',
      url: lichessOpeningSearchUrl(openingName),
      kind: 'opening',
    };
  }

  const themeKey = inferPriorityThemeKey(priority);
  return {
    label: 'Train on Lichess',
    url: lichessPuzzleUrlForTheme(themeKey),
    kind: 'puzzle',
  };
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
      `${toTitleCase(pattern)} Puzzles`,
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

  const endgameInsights = batchSummary.endgame_insights || [];
  const hasSpecificEndgame = endgameInsights.some(
    (item) => item?.endgame_type && item.endgame_type !== 'general_endgame'
  );
  endgameInsights
    .filter((item) => !(hasSpecificEndgame && item?.endgame_type === 'general_endgame'))
    .slice(0, 3)
    .forEach((item) => {
    const type = item.endgame_type || item.label;
    if (!type) {
      return;
    }
    const url = item.study_url || lichessEndgamePracticeUrl(type);
    addLink(
      `${toTitleCase(item.label || type)} Practice`,
      url,
      'endgame'
    );
  });

  return links.slice(0, 8);
};
