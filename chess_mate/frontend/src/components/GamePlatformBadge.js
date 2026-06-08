import React from 'react';
import { formatGamePlatformLabel } from '../utils/gamePlatform';

const GamePlatformBadge = ({ platform, isDarkMode = false, className = '' }) => {
  const label = formatGamePlatformLabel(platform);
  if (!label) {
    return null;
  }

  const isLichess = label === 'Lichess';

  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
        isDarkMode
          ? (isLichess ? 'bg-neutral-700 text-neutral-200' : 'bg-amber-900/40 text-amber-200')
          : (isLichess ? 'bg-neutral-100 text-neutral-700' : 'bg-amber-50 text-amber-800')
      } ${className}`.trim()}
    >
      {label}
    </span>
  );
};

export default GamePlatformBadge;
