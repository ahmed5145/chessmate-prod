import React from 'react';
import { useTheme } from '../../context/ThemeContext';
import { getClassificationMeta } from '../../utils/singleGameClassification';

const LIGHT_BADGE = {
  book: 'bg-violet-100 text-violet-800',
  brilliant: 'bg-cyan-100 text-cyan-800',
  best: 'bg-emerald-100 text-emerald-800',
  good: 'bg-green-100 text-green-800',
  inaccuracy: 'bg-amber-100 text-amber-800',
  mistake: 'bg-orange-100 text-orange-800',
  blunder: 'bg-red-100 text-red-800',
  missed_win: 'bg-rose-100 text-rose-800',
  neutral: 'bg-gray-100 text-gray-700',
};

const DARK_BADGE = {
  book: 'bg-violet-900/40 text-violet-200',
  brilliant: 'bg-cyan-900/40 text-cyan-200',
  best: 'bg-emerald-900/40 text-emerald-200',
  good: 'bg-green-900/40 text-green-200',
  inaccuracy: 'bg-amber-900/40 text-amber-200',
  mistake: 'bg-orange-900/40 text-orange-200',
  blunder: 'bg-red-900/40 text-red-200',
  missed_win: 'bg-rose-900/40 text-rose-200',
  neutral: 'bg-gray-700 text-gray-200',
};

const MoveClassificationBadge = ({ classification = 'neutral', showIcon = true }) => {
  const { isDarkMode } = useTheme();
  const meta = getClassificationMeta(classification);
  const palette = isDarkMode ? DARK_BADGE : LIGHT_BADGE;

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${
        palette[classification] || palette.neutral
      }`}
    >
      {showIcon ? <span aria-hidden="true">{meta.icon}</span> : null}
      {meta.label}
    </span>
  );
};

export default MoveClassificationBadge;
