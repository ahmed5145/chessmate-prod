/**
 * Deep links into single-game analysis from batch citations and games library.
 */

export const buildSingleGameAnalysisLink = ({
  gameId,
  batchId = null,
  move = null,
  priority = null,
  mode = null,
  force = null,
} = {}) => {
  if (gameId == null || gameId === '') {
    return '/games';
  }

  const base = `/game/${gameId}/analysis`;
  const params = new URLSearchParams();

  if (batchId != null && batchId !== '') {
    params.set('batch', String(batchId));
  }
  if (move != null && move !== '') {
    params.set('move', String(move));
  }
  if (priority != null && priority !== '') {
    params.set('priority', String(priority));
  }
  if (mode === 'review' || mode === 'run') {
    params.set('mode', mode);
  }
  if (force === 'reanalyze') {
    params.set('force', 'reanalyze');
  }

  const query = params.toString();
  return query ? `${base}?${query}` : base;
};

export const parseSingleGameAnalysisSearch = (search = '') => {
  const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search);
  const batchId = params.get('batch');
  const move = params.get('move');
  const priority = params.get('priority');
  const mode = params.get('mode');
  const force = params.get('force');

  return {
    batchId: batchId ? String(batchId) : null,
    move: move ? Number(move) : null,
    priority: priority ? Number(priority) : null,
    mode: mode === 'review' || mode === 'run' ? mode : null,
    force: force === 'reanalyze' ? 'reanalyze' : null,
  };
};
