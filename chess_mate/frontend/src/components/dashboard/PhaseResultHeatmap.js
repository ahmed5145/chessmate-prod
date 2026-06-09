import React, { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Grid3X3 } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

const RESULT_LABELS = {
  win: 'Wins',
  loss: 'Losses',
  draw: 'Draws',
};

const PHASE_LABELS = {
  opening: 'Opening',
  middlegame: 'Middlegame',
  endgame: 'Endgame',
};

const cellLookup = (cells = []) => {
  const map = new Map();
  cells.forEach((cell) => {
    map.set(`${cell.result}:${cell.phase}`, cell);
  });
  return map;
};

const intensityClass = (cell, isDarkMode) => {
  if (!cell?.highlight) {
    return isDarkMode ? 'bg-gray-800/60 text-gray-500' : 'bg-gray-100 text-gray-400';
  }
  const accuracy = Number(cell.avg_accuracy);
  if (cell.result === 'loss') {
    if (accuracy < 45) {
      return isDarkMode ? 'bg-red-900/70 text-red-100' : 'bg-red-200 text-red-900';
    }
    return isDarkMode ? 'bg-red-950/50 text-red-200' : 'bg-red-100 text-red-800';
  }
  if (cell.result === 'win') {
    return isDarkMode ? 'bg-amber-900/40 text-amber-100' : 'bg-amber-100 text-amber-900';
  }
  return isDarkMode ? 'bg-indigo-900/40 text-indigo-100' : 'bg-indigo-100 text-indigo-900';
};

const PhaseResultHeatmap = ({ phaseHeatmap }) => {
  const { isDarkMode } = useTheme();
  const lookup = useMemo(
    () => cellLookup(phaseHeatmap?.cells),
    [phaseHeatmap?.cells]
  );

  if (!phaseHeatmap?.show) {
    return null;
  }

  const results = phaseHeatmap.results || ['win', 'loss', 'draw'];
  const phases = phaseHeatmap.phases || ['opening', 'middlegame', 'endgame'];
  const topInsight = phaseHeatmap.top_insight;

  return (
    <section
      className={`mb-8 rounded-xl border overflow-hidden ${
        isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
      } shadow-lg`}
    >
      <div className={`px-5 py-4 border-b ${isDarkMode ? 'border-gray-700' : 'border-gray-100'}`}>
        <div className="flex items-center gap-2">
          <Grid3X3 className={`h-5 w-5 ${isDarkMode ? 'text-indigo-300' : 'text-indigo-600'}`} />
          <h2 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Result × phase patterns
          </h2>
        </div>
        <p className={`mt-1 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          Based on {phaseHeatmap.analyzed_games} analyzed games. Highlighted cells have ≥3 games
          with accuracy under 55% or heavy eval swings.
        </p>
        {topInsight?.headline ? (
          <p className={`mt-2 text-sm font-medium ${isDarkMode ? 'text-indigo-200' : 'text-indigo-700'}`}>
            {topInsight.href ? (
              <Link to={topInsight.href} className="hover:underline">
                {topInsight.headline}
              </Link>
            ) : (
              topInsight.headline
            )}
          </p>
        ) : null}
      </div>

      <div className="p-4 overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-2">
          <thead>
            <tr>
              <th className="w-24" />
              {phases.map((phase) => (
                <th
                  key={phase}
                  className={`text-xs font-semibold uppercase tracking-wide px-2 py-1 ${
                    isDarkMode ? 'text-gray-400' : 'text-gray-500'
                  }`}
                >
                  {PHASE_LABELS[phase] || phase}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {results.map((result) => (
              <tr key={result}>
                <th
                  className={`text-xs font-semibold uppercase tracking-wide text-left pr-3 ${
                    isDarkMode ? 'text-gray-400' : 'text-gray-500'
                  }`}
                >
                  {RESULT_LABELS[result] || result}
                </th>
                {phases.map((phase) => {
                  const cell = lookup.get(`${result}:${phase}`) || {};
                  const example = (cell.example_games || [])[0];
                  const content = (
                    <div className="flex flex-col items-center justify-center min-h-[72px]">
                      <span className="text-sm font-bold tabular-nums">
                        {cell.avg_accuracy != null ? `${cell.avg_accuracy}%` : '—'}
                      </span>
                      <span className="text-[11px] opacity-80">
                        {cell.game_count || 0} games
                      </span>
                    </div>
                  );

                  return (
                    <td key={`${result}-${phase}`}>
                      {cell.highlight && example?.href ? (
                        <Link
                          to={example.href}
                          className={`block rounded-lg border px-2 py-2 text-center transition-opacity hover:opacity-90 ${
                            isDarkMode ? 'border-gray-700' : 'border-gray-200'
                          } ${intensityClass(cell, isDarkMode)}`}
                          title={cell.headline || 'Review example game'}
                        >
                          {content}
                        </Link>
                      ) : (
                        <div
                          className={`rounded-lg border px-2 py-2 text-center ${
                            isDarkMode ? 'border-gray-700' : 'border-gray-200'
                          } ${intensityClass(cell, isDarkMode)}`}
                        >
                          {content}
                        </div>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default PhaseResultHeatmap;
