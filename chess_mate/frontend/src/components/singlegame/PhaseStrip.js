import React from 'react';
import { useTheme } from '../../context/ThemeContext';

const PHASES = ['opening', 'middlegame', 'endgame'];

const phaseScore = (phaseData = {}) => {
  if (phaseData.accuracy_pct != null) {
    return Number(phaseData.accuracy_pct);
  }
  if (phaseData.accuracy != null) {
    return Number(phaseData.accuracy);
  }
  if (phaseData.score != null) {
    return Math.round(Number(phaseData.score) * 100);
  }
  return null;
};

const scoreClass = (score, isDarkMode) => {
  if (score == null) {
    return isDarkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600';
  }
  if (score >= 75) {
    return isDarkMode ? 'bg-emerald-900/50 text-emerald-200' : 'bg-emerald-100 text-emerald-800';
  }
  if (score >= 50) {
    return isDarkMode ? 'bg-amber-900/40 text-amber-200' : 'bg-amber-100 text-amber-800';
  }
  return isDarkMode ? 'bg-red-900/40 text-red-200' : 'bg-red-100 text-red-800';
};

const PhaseStrip = ({ phases = {}, phaseNotes = {}, batchPhasePerformance = null }) => {
  const { isDarkMode } = useTheme();
  const source = batchPhasePerformance && Object.keys(batchPhasePerformance).length > 0
    ? batchPhasePerformance
    : phases;

  if (!source || Object.keys(source).length === 0) {
    return null;
  }

  return (
    <div className={`mb-8 rounded-lg border p-4 ${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
      <h3 className={`text-lg font-semibold mb-3 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
        Phase snapshot
      </h3>
      <div className="flex flex-wrap gap-2 mb-3">
        {PHASES.map((phase) => {
          const phaseData = source[phase];
          if (!phaseData) {
            return null;
          }
          const score = phaseScore(phaseData);
          return (
            <span
              key={phase}
              className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${scoreClass(score, isDarkMode)}`}
            >
              <span className="capitalize">{phase}</span>
              <span>{score == null ? '—' : `${Number(score).toFixed(score >= 10 ? 0 : 1)}%`}</span>
            </span>
          );
        })}
      </div>
      {Object.keys(phaseNotes).length > 0 ? (
        <ul className={`space-y-1 text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          {Object.entries(phaseNotes).map(([phase, note]) => (
            <li key={phase}>
              <span className="font-medium capitalize">{phase}:</span> {note}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
};

export default PhaseStrip;
