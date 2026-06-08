/** Map internal analysis states to user-facing Games tab labels. */

export const isGameAnalyzed = (game = {}) => {
  const status = String(game.analysis_status || game.status || '').toLowerCase();
  return (
    status === 'analyzed'
    || status === 'completed'
    || !!game.analysis
  );
};

export const getGameAnalysisStatusLabel = (game = {}) => (
  isGameAnalyzed(game) ? 'Analyzed' : 'Unanalyzed'
);
