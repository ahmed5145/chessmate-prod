/**
 * User-facing copy for single-game analysis polling states.
 */

const QUEUED_PATTERNS = [
  'task queued',
  'waiting for worker',
  'worker availability',
  'task pending',
  'not found or not started',
  'not started',
];

export const humanizeAnalysisStatusMessage = (message, progress = 0) => {
  const raw = String(message || '').trim();
  const normalized = raw.toLowerCase();

  if (normalized.includes('rate limit')) {
    return {
      status: 'Taking a short pause',
      detail:
        'We are spacing out status checks so the server stays responsive. Your depth-20 review is still running — no action needed.',
      queued: false,
    };
  }

  if (QUEUED_PATTERNS.some((pattern) => normalized.includes(pattern))) {
    return {
      status: 'Queued — starting soon',
      detail:
        'Your depth-20 review is in line for the background worker. If this lasts more than 2–3 minutes, the analysis worker may be busy or offline — try again shortly or check Games for progress.',
      queued: true,
    };
  }

  if (normalized.includes('starting analysis') || progress <= 5) {
    return {
      status: 'Starting your review',
      detail: 'Stockfish depth 20 is preparing your game. Feel free to browse elsewhere.',
      queued: false,
    };
  }

  if (raw) {
    return {
      status: raw,
      detail: 'Analysis is running in the background. You do not need to keep this tab open.',
      queued: false,
    };
  }

  return {
    status: 'Analysis in progress',
    detail: 'We will load your coaching report automatically when ready.',
    queued: false,
  };
};
