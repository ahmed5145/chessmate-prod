import React from 'react';
import { useTheme } from '../../context/ThemeContext';

const SingleGameHero = ({ coaching = {}, worstMoment = null, playerStats = null }) => {
  const { isDarkMode } = useTheme();
  const headline = coaching.headline;
  const takeaway = coaching.takeaway;
  const doToday = coaching.do_today;

  if (!headline && !takeaway && !doToday && !worstMoment && !playerStats) {
    return null;
  }

  return (
    <div
      className={`mb-6 rounded-lg border p-4 ${
        isDarkMode ? 'bg-indigo-950/30 border-indigo-800/50' : 'bg-indigo-50 border-indigo-100'
      }`}
    >
      {headline ? (
        <h3 className={`text-lg font-bold mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
          {headline}
        </h3>
      ) : null}
      {playerStats?.totalMoves ? (
        <p className={`text-xs font-semibold uppercase tracking-wide mb-2 ${
          isDarkMode ? 'text-indigo-300' : 'text-indigo-700'
        }`}
        >
          Depth-20 coach review · {playerStats.totalMoves} of your moves analyzed
        </p>
      ) : null}
      {takeaway ? (
        <p className={`text-base font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
          {takeaway}
        </p>
      ) : null}
      {worstMoment ? (
        <p className={`mt-2 text-sm ${isDarkMode ? 'text-amber-200' : 'text-amber-900'}`}>
          <span className="font-semibold">Replay this:</span>
          {' '}Move {worstMoment.move_number}
          {worstMoment.played_move ? ` — you played ${worstMoment.played_move}` : ''}
          {worstMoment.best_move ? `, engine wanted ${worstMoment.best_move}` : ''}
          {worstMoment.eval_swing != null ? ` (${worstMoment.eval_swing} pawn swing)` : ''}
        </p>
      ) : null}
      {doToday ? (
        <p className={`mt-2 text-sm ${isDarkMode ? 'text-indigo-200' : 'text-indigo-900'}`}>
          <span className="font-semibold">Do today (5 min):</span> {doToday}
        </p>
      ) : null}
    </div>
  );
};

export default SingleGameHero;
