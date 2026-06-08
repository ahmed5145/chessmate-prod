import React from 'react';
import FenBoardImage from '../batch/FenBoardImage';
import { useTheme } from '../../context/ThemeContext';
import { formatNumber } from '../../utils/formatters';

const severityClass = (type, isDarkMode) => {
  if (type === 'blunder') {
    return isDarkMode ? 'bg-red-900/50 text-red-200' : 'bg-red-100 text-red-800';
  }
  if (type === 'mistake') {
    return isDarkMode ? 'bg-amber-900/40 text-amber-200' : 'bg-amber-100 text-amber-800';
  }
  return isDarkMode ? 'bg-gray-700 text-gray-200' : 'bg-gray-100 text-gray-700';
};

const CriticalMomentsSection = ({ moments = [], playerColor = 'white', onSelectMove }) => {
  const { isDarkMode } = useTheme();

  if (!Array.isArray(moments) || moments.length === 0) {
    return null;
  }

  return (
    <div className="mb-8">
      <h3 className={`text-lg font-semibold mb-3 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
        Critical moments
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {moments.map((moment, index) => (
          <div
            key={`sg-moment-${moment.move_number}-${index}`}
            className={`rounded-lg border p-3 ${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}
          >
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${severityClass(moment.type, isDarkMode)}`}>
                {moment.type || 'moment'}
              </span>
              <span className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                Move {moment.move_number}
              </span>
            </div>
            {moment.fen ? (
              <button
                type="button"
                className="w-full text-left"
                onClick={() => onSelectMove && onSelectMove(moment.move_number)}
              >
                <FenBoardImage
                  fen={moment.fen}
                  size={220}
                  orientation={moment.player_color || playerColor}
                  playedMoveUci={moment.played_move_uci}
                  bestMoveUci={moment.best_move_uci}
                />
              </button>
            ) : null}
            <p className={`mt-2 text-sm font-medium ${isDarkMode ? 'text-gray-200' : 'text-gray-800'}`}>
              Played {moment.played_move || '?'} · best {moment.best_move || '?'}
              {moment.eval_swing != null ? ` · swing ${formatNumber(moment.eval_swing, 2)}` : ''}
            </p>
            {moment.explanation ? (
              <p className={`mt-1 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                {moment.explanation}
              </p>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
};

export default CriticalMomentsSection;
