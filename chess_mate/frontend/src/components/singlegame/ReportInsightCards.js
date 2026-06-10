import React from 'react';
import { FaBolt, FaChessBoard, FaChartLine } from 'react-icons/fa';
import { useTheme } from '../../context/ThemeContext';
import { formatListOpeningLabel } from '../../utils/formatListOpeningLabel';
import { formatBestLineEval, formatAfterMoveEval } from '../../utils/singleGameClassification';
import MetricInfoIcon from '../shared/MetricInfoIcon';

const InsightCard = ({ icon: Icon, title, value, detail, isDarkMode, metricKey = null }) => (
  <div className={`rounded-lg border p-4 ${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
    <div className="flex items-start gap-3">
      <div className={`rounded-full p-2 ${isDarkMode ? 'bg-indigo-900/50 text-indigo-300' : 'bg-indigo-100 text-indigo-700'}`}>
        <Icon aria-hidden="true" />
      </div>
      <div>
        <p className={`text-xs font-semibold uppercase tracking-wide flex items-center ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          {title}
          {metricKey ? <MetricInfoIcon metricKey={metricKey} isDarkMode={isDarkMode} /> : null}
        </p>
        <p className={`mt-1 text-xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>{value}</p>
        {detail ? (
          <p className={`mt-1 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>{detail}</p>
        ) : null}
      </div>
    </div>
  </div>
);

const weakestPhase = (phases = {}) => {
  const entries = ['opening', 'middlegame', 'endgame']
    .map((name) => {
      const phase = phases[name] || {};
      const accuracy = Number(phase.accuracy);
      return Number.isFinite(accuracy) ? { name, accuracy } : null;
    })
    .filter(Boolean);
  if (!entries.length) {
    return null;
  }
  return entries.reduce((min, item) => (item.accuracy < min.accuracy ? item : min));
};

const ReportInsightCards = ({
  playerStats = null,
  worstMoment = null,
  gameContext = {},
  phaseData = {},
  playerColor = 'white',
  inboxStreak = null,
}) => {
  const { isDarkMode } = useTheme();
  const openingLabel = formatListOpeningLabel({
    opening_name: gameContext.opening_name,
    eco_code: gameContext.eco,
  });
  const weak = weakestPhase(phaseData);

  if (!playerStats?.totalMoves && !worstMoment && !openingLabel) {
    return null;
  }

  let momentValue = '—';
  let momentDetail = 'No major swings flagged in your moves.';
  if (worstMoment) {
    momentValue = `Move ${worstMoment.move_number}`;
    const bestEval = formatBestLineEval({
      evalAfterBest: worstMoment.eval_after_best,
      evalAfter: worstMoment.eval_after,
    }, playerColor);
    const afterEval = formatAfterMoveEval({ evalAfter: worstMoment.eval_after }, playerColor);
    momentDetail = `${worstMoment.played_move || '?'} vs best ${worstMoment.best_move || '?'} `
      + `(${afterEval} after · ${bestEval} best line)`;
    if (worstMoment.rating_benchmark?.copy) {
      momentDetail = `${momentDetail} ${worstMoment.rating_benchmark.copy}`;
    }
  }

  return (
    <div className="mb-6">
      {inboxStreak?.show ? (
        <p
          className={`mb-4 inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium ${
            isDarkMode
              ? 'bg-orange-950/30 border-orange-800/50 text-orange-200'
              : 'bg-orange-50 border-orange-200 text-orange-900'
          }`}
        >
          <span aria-hidden="true">🔥</span>
          <span>{inboxStreak.label}</span>
          {inboxStreak.milestone_message ? (
            <span className={`font-normal ${isDarkMode ? 'text-orange-200/80' : 'text-orange-800/80'}`}>
              · {inboxStreak.milestone_message}
            </span>
          ) : null}
        </p>
      ) : null}
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <InsightCard
        icon={FaChartLine}
        title="Your accuracy"
        value={playerStats?.accuracy != null ? `${playerStats.accuracy}%` : '—'}
        detail={`${playerStats?.errors || 0} errors across ${playerStats?.totalMoves || 0} of your moves`}
        isDarkMode={isDarkMode}
        metricKey="single_game_accuracy"
      />
      <InsightCard
        icon={FaBolt}
        title="Turning point"
        value={momentValue}
        detail={momentDetail}
        isDarkMode={isDarkMode}
        metricKey="eval_swing"
      />
      <InsightCard
        icon={FaChessBoard}
        title={openingLabel || 'Opening'}
        value={weak ? `${weak.name}` : 'Balanced'}
        detail={
          weak
            ? `${weak.accuracy}% accuracy in ${weak.name} — focus here first`
            : 'Phase accuracy was balanced across the game'
        }
        isDarkMode={isDarkMode}
        metricKey="single_game_phase_accuracy"
      />
    </div>
    </div>
  );
};

export default ReportInsightCards;
