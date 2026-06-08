import { toast } from 'react-hot-toast';

/**
 * In-app toast + optional browser notification when a single-game review finishes.
 * Browser notifications only fire when permission is already granted and the tab is hidden.
 */
export const notifySingleGameAnalysisComplete = (gameId, options = {}) => {
  const { opponent = null, onOpen } = options;
  const label = opponent ? `vs ${opponent}` : `game ${gameId}`;

  toast.success(`Depth-20 review ready (${label})`, { duration: 6000 });

  if (
    typeof window !== 'undefined'
    && typeof Notification !== 'undefined'
    && Notification.permission === 'granted'
    && document.hidden
  ) {
    try {
      const notification = new Notification('ChessMate — review ready', {
        body: `Your depth-20 review (${label}) is ready.`,
        tag: `single-game-complete-${gameId}`,
      });
      notification.onclick = () => {
        window.focus();
        if (typeof onOpen === 'function') {
          onOpen();
        }
        notification.close();
      };
    } catch {
      /* ignore unsupported environments */
    }
  }
};
