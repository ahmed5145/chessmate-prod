import React from 'react';
import { useTheme } from '../../context/ThemeContext';

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

const PositionEvalBar = ({ evalText = '0.00', tone = 'equal', playerColor = 'white' }) => {
  const { isDarkMode } = useTheme();
  const numeric = Number(String(evalText).replace(/[^0-9.+-]/g, ''));
  const hasNumeric = Number.isFinite(numeric);
  const whiteShare = hasNumeric ? clamp(50 + numeric * 6, 8, 92) : 50;

  const toneColor = {
    winning: isDarkMode ? 'text-emerald-300' : 'text-emerald-700',
    losing: isDarkMode ? 'text-red-300' : 'text-red-700',
    equal: isDarkMode ? 'text-gray-300' : 'text-gray-600',
    unclear: isDarkMode ? 'text-amber-200' : 'text-amber-700',
  }[tone] || (isDarkMode ? 'text-gray-300' : 'text-gray-600');

  return (
    <div className="mb-3">
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className={isDarkMode ? 'text-gray-400' : 'text-gray-500'}>
          Position eval ({playerColor === 'black' ? 'your perspective' : 'your perspective'})
        </span>
        <span className={`font-semibold tabular-nums ${toneColor}`}>{evalText}</span>
      </div>
      <div
        className={`relative h-3 overflow-hidden rounded-full border ${
          isDarkMode ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-gray-100'
        }`}
        aria-label={`Position evaluation ${evalText}`}
      >
        <div
          className="absolute inset-y-0 left-0 bg-white/90"
          style={{ width: `${whiteShare}%` }}
        />
        <div
          className="absolute inset-y-0 right-0 bg-gray-900/85"
          style={{ width: `${100 - whiteShare}%` }}
        />
        <div className="absolute inset-y-0 left-1/2 w-px bg-black/20" />
      </div>
    </div>
  );
};

export default PositionEvalBar;
