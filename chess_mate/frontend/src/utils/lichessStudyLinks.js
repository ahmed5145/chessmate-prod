/**
 * Map batch weakness themes to Lichess study URLs (puzzles, openings, endgames).
 */

import { findGameResultById } from './formatGameLabel';
import { toTitleCase } from './formatLabel';
import { buildOpeningStudyQuery, compactOpeningName } from './openingNameCompact';

const UNKNOWN_OPENING_LABELS = new Set(['unknown', 'unknown opening', '?']);

const GENERIC_OPENING_LABELS = new Set([
  'opening repertoire',
  'your repertoire',
  'the repertoire',
  'your opening repertoire',
  'the opening repertoire',
  'opening theory',
  'study opening theory',
  'your opening',
  'the opening',
  'repertoire',
]);

const SPECIFIC_OPENING_HINT_RE = /sicilian|london|french|caro|italian|ruy|queen'?s|king'?s|slav|indian|najdorf|dragon|catalan|nimzo|grünfeld|grunfeld|scandinavian|gambit|defense|defence|system|attack|variation|pawn game|gambit declined|opening:/i;

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

export const lichessOpeningSearchUrl = (openingName, options = {}) => {
  const query = buildOpeningStudyQuery(
    openingName,
    options.ecoCode,
    options.playerColor
  ) || 'opening';
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

const normalizeOpeningLabel = (name) => (
  String(name || '')
    .trim()
    .toLowerCase()
    .replace(/^(?:the|your)\s+/, '')
    .trim()
);

const cleanExtractedOpeningName = (name) => {
  const compacted = compactOpeningName(name);
  return compacted || String(name || '').trim() || null;
};

const hasSpecificOpeningFamily = (name) => SPECIFIC_OPENING_HINT_RE.test(String(name || ''));

const extractGameIdsFromPriority = (priority = {}) => {
  const text = [priority.title, priority.why_it_matters, priority.how_to_fix, priority.specific_drill]
    .filter(Boolean)
    .join(' ');
  const matches = text.match(/game_\d+/gi) || [];
  return [...new Set(matches.map((id) => id.toLowerCase()))];
};

const isRecognizedOpeningName = (name) => {
  const compacted = compactOpeningName(name);
  if (!compacted || UNKNOWN_OPENING_LABELS.has(compacted.toLowerCase())) {
    return false;
  }
  const normalized = compacted.toLowerCase();
  if (/^game_\d+$/i.test(normalized) || /\bgame_\d+\b/i.test(normalized)) {
    return false;
  }
  if (GENERIC_OPENING_LABELS.has(normalized) || GENERIC_OPENING_LABELS.has(normalizeOpeningLabel(compacted))) {
    return false;
  }
  if (/\brepertoire\b/i.test(compacted) && !hasSpecificOpeningFamily(compacted)) {
    return false;
  }
  if (/\bopening theory\b/i.test(compacted) && !hasSpecificOpeningFamily(compacted)) {
    return false;
  }
  return true;
};

const openingStudyTargetFromName = (openingName, options = {}) => ({
  openingName: compactOpeningName(openingName),
  ecoCode: options.ecoCode || null,
  playerColor: options.playerColor || null,
});

const extractOpeningNameFromPriority = (priority = {}) => {
  const sources = [priority.title, priority.how_to_fix, priority.specific_drill, priority.why_it_matters]
    .filter(Boolean);

  for (const raw of sources) {
    const text = String(raw);

    const fromTheory = text.match(
      /opening theory(?:\s+(?:on|for|about|in))?\s+(.+?)(?:\s+to\b|[.;]|$)/i
    );
    if (fromTheory?.[1]) {
      const name = cleanExtractedOpeningName(fromTheory[1]);
      if (isRecognizedOpeningName(name)) {
        return name;
      }
    }

    const fromStudyTheory = text.match(
      /study\s+opening\s+theory(?:\s*(?:on|for|about|in|:)\s*)?(.+?)(?:\s+to\b|[.;]|$)/i
    );
    if (fromStudyTheory?.[1]) {
      const name = cleanExtractedOpeningName(fromStudyTheory[1]);
      if (isRecognizedOpeningName(name)) {
        return name;
      }
    }

    const fromColon = text.match(/opening\s+theory\s*:\s*(.+?)(?:\s+to\b|[.;]|$)/i);
    if (fromColon?.[1]) {
      const name = cleanExtractedOpeningName(fromColon[1]);
      if (isRecognizedOpeningName(name)) {
        return name;
      }
    }

    const fromIdeas = text.match(/ideas from (?:the\s+)?(.+?)(?:\s+to\b|[.;]|$)/i);
    if (fromIdeas?.[1]) {
      const name = cleanExtractedOpeningName(fromIdeas[1]);
      if (isRecognizedOpeningName(name)) {
        return name;
      }
    }

    const fromMasters = text.match(/masters in (?:the\s+)?(.+?)(?:\s*[.;]|$)/i);
    if (fromMasters?.[1]) {
      const name = cleanExtractedOpeningName(fromMasters[1]);
      if (isRecognizedOpeningName(name)) {
        return name;
      }
    }

    const fromLine = text.match(/\b(?:line|lines)\s+in\s+(?:the\s+)?(.+?)(?:\s+to\b|[.;]|$)/i);
    if (fromLine?.[1]) {
      const name = cleanExtractedOpeningName(fromLine[1]);
      if (isRecognizedOpeningName(name)) {
        return name;
      }
    }

    const quotedOpening = text.match(
      /(?:Queen's|King's|London|Sicilian|Caro|French|Slav|Indian|Italian|Ruy|Scandinavian|Nimzo|Grünfeld|Catalan)[^.;]*/i
    );
    if (quotedOpening?.[0]) {
      const name = cleanExtractedOpeningName(quotedOpening[0]);
      if (isRecognizedOpeningName(name)) {
        return name;
      }
    }
  }

  return null;
};

const resolveOpeningStudyTargetFromLinkedGames = (priority, perGameResults = []) => {
  const gameIds = extractGameIdsFromPriority(priority);
  for (const gameId of gameIds) {
    const game = findGameResultById(perGameResults, gameId);
    if (isRecognizedOpeningName(game?.opening_name)) {
      return openingStudyTargetFromName(game.opening_name, {
        ecoCode: game.eco_code,
        playerColor: game.player_color,
      });
    }
  }
  return null;
};

const resolveOpeningStudyTargetFromBatchSummary = (batchSummary = {}) => {
  const gaps = Array.isArray(batchSummary.repertoire_gaps) ? batchSummary.repertoire_gaps : [];
  if (gaps[0]?.opening_name && isRecognizedOpeningName(gaps[0].opening_name)) {
    return openingStudyTargetFromName(gaps[0].opening_name, {
      ecoCode: gaps[0].eco_code,
      playerColor: gaps[0].player_color,
    });
  }

  const struggling = (batchSummary.opening_insights || []).filter(
    (item) => item?.status === 'struggling' || item?.status === 'needs_work'
  );
  if (struggling[0]?.opening_name && isRecognizedOpeningName(struggling[0].opening_name)) {
    return openingStudyTargetFromName(struggling[0].opening_name, {
      ecoCode: struggling[0].eco_code,
      playerColor: struggling[0].player_color,
    });
  }

  const primaryOpenings = batchSummary.phase_performance?.opening?.primary_openings || [];
  const primary = primaryOpenings.find((name) => isRecognizedOpeningName(name));
  if (primary) {
    return openingStudyTargetFromName(primary);
  }

  return null;
};

const resolveOpeningStudyTargetFromPerGameResults = (perGameResults = []) => {
  const counts = new Map();
  perGameResults.forEach((game) => {
    const name = compactOpeningName(game?.opening_name);
    if (!isRecognizedOpeningName(name)) {
      return;
    }
    counts.set(name, (counts.get(name) || 0) + 1);
  });

  const [topOpening] = [...counts.entries()].sort((a, b) => b[1] - a[1]);
  if (topOpening?.[0]) {
    const sample = perGameResults.find(
      (game) => compactOpeningName(game?.opening_name) === topOpening[0]
    );
    return openingStudyTargetFromName(topOpening[0], {
      ecoCode: sample?.eco_code,
      playerColor: sample?.player_color,
    });
  }

  return null;
};

export const resolveOpeningStudyTarget = (priority, context = {}) => {
  const { batch_summary: batchSummary = {}, per_game_results: perGameResults = [] } = context;

  const linkedGameTarget = resolveOpeningStudyTargetFromLinkedGames(priority, perGameResults);
  if (linkedGameTarget) {
    return linkedGameTarget;
  }

  const batchTarget = resolveOpeningStudyTargetFromBatchSummary(batchSummary);
  if (batchTarget) {
    return batchTarget;
  }

  const extractedName = extractOpeningNameFromPriority(priority);
  if (extractedName) {
    return openingStudyTargetFromName(extractedName);
  }

  return resolveOpeningStudyTargetFromPerGameResults(perGameResults);
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
export const resolvePriorityLichessLink = (priority, context = {}) => {
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
    const openingTarget = resolveOpeningStudyTarget(priority, context);
    if (!openingTarget?.openingName) {
      return null;
    }

    const labelName = openingTarget.openingName.includes(':')
      ? openingTarget.openingName.split(':').slice(1).join(':').trim() || openingTarget.openingName
      : openingTarget.openingName;

    return {
      label: 'Study on Lichess',
      url: lichessOpeningSearchUrl(openingTarget.openingName, {
        ecoCode: openingTarget.ecoCode,
        playerColor: openingTarget.playerColor,
      }),
      kind: 'opening',
      openingName: labelName,
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

  const addLink = (label, url, kind, dedupeKey = null) => {
    const dedupe = dedupeKey || `${kind}:${url}`;
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
      const url = lichessOpeningSearchUrl(name, {
        ecoCode: item.eco_code,
        playerColor: item.player_color,
      });
      addLink(
        `Study ${name}${color}`,
        url,
        'opening',
        `opening:${item.eco_code || ''}:${buildOpeningStudyQuery(name, item.eco_code, item.player_color)}`
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
