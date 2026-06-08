import React, { useState } from 'react';
import { useTheme } from '../../context/ThemeContext';
import { buildSingleGameAnalysisLink } from '../../utils/singleGameAnalysisLinks';
import { trackSingleGameEvent } from '../../utils/marketingAnalytics';
import { createGameMomentShare } from '../../services/gameAnalysisService';

const SingleGameReportActions = ({
  gameId,
  batchId = null,
  move = null,
  priority = null,
  onReanalyze,
}) => {
  const { isDarkMode } = useTheme();
  const [copyLabel, setCopyLabel] = useState('Copy link');
  const [shareLabel, setShareLabel] = useState('Share moment');
  const [sharing, setSharing] = useState(false);

  const handlePrint = () => {
    trackSingleGameEvent('single_game_print', { game_id: gameId, batch_id: batchId });
    window.print();
  };

  const handleCopyLink = async () => {
    const url = `${window.location.origin}${buildSingleGameAnalysisLink({
      gameId,
      batchId,
      move,
      priority,
    })}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopyLabel('Copied!');
      trackSingleGameEvent('single_game_share_copy', { game_id: gameId, batch_id: batchId });
      setTimeout(() => setCopyLabel('Copy link'), 2000);
    } catch {
      setCopyLabel('Copy failed');
      setTimeout(() => setCopyLabel('Copy link'), 2000);
    }
  };

  const handleShareMoment = async () => {
    if (!gameId || sharing) {
      return;
    }
    setSharing(true);
    try {
      const data = await createGameMomentShare(gameId, { move });
      const url = data.share_url || `${window.location.origin}/share/game-moment/${data.share_token}`;
      await navigator.clipboard.writeText(url);
      setShareLabel('Moment link copied!');
      trackSingleGameEvent('single_game_moment_share_copy', {
        game_id: gameId,
        batch_id: batchId,
        move,
      });
      setTimeout(() => setShareLabel('Share moment'), 2000);
    } catch {
      setShareLabel('Share failed');
      setTimeout(() => setShareLabel('Share moment'), 2000);
    } finally {
      setSharing(false);
    }
  };

  const buttonClass = isDarkMode
    ? 'px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-600 text-gray-200 hover:bg-gray-700'
    : 'px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-300 text-gray-700 hover:bg-gray-50';

  return (
    <div className="single-game-no-print mb-6 flex flex-wrap gap-2">
      {onReanalyze ? (
        <button type="button" className={buttonClass} onClick={onReanalyze}>
          Re-run deep review (1 credit)
        </button>
      ) : null}
      <button type="button" className={buttonClass} onClick={handlePrint}>
        Print summary
      </button>
      <button type="button" className={buttonClass} onClick={handleCopyLink}>
        {copyLabel}
      </button>
      <button
        type="button"
        className={buttonClass}
        onClick={handleShareMoment}
        disabled={sharing}
      >
        {sharing ? 'Sharing…' : shareLabel}
      </button>
    </div>
  );
};

export default SingleGameReportActions;
