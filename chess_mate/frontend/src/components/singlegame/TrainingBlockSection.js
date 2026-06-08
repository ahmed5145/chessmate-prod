import React from 'react';
import { useTheme } from '../../context/ThemeContext';

const TrainingBlockSection = ({ trainingBlock = null }) => {
  const { isDarkMode } = useTheme();

  if (!trainingBlock || typeof trainingBlock !== 'object') {
    return null;
  }

  const focusAreas = Array.isArray(trainingBlock.focus_areas) ? trainingBlock.focus_areas : [];
  const drills = Array.isArray(trainingBlock.drills) ? trainingBlock.drills : [];
  const motifs = trainingBlock.phase_motifs?.motifs || [];
  const impact = trainingBlock.impact_metrics || {};

  if (!focusAreas.length && !drills.length && !motifs.length) {
    return null;
  }

  return (
    <div className={`mb-8 rounded-lg border p-4 ${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
      <h3 className={`text-lg font-semibold mb-3 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
        Training focus
      </h3>

      {focusAreas.length > 0 ? (
        <div className="mb-4">
          <p className={`text-sm font-medium mb-1 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>Focus areas</p>
          <ul className={`list-disc pl-5 text-sm space-y-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            {focusAreas.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {motifs.length > 0 ? (
        <div className="mb-4">
          <p className={`text-sm font-medium mb-1 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>Phase motifs</p>
          <div className="flex flex-wrap gap-2">
            {motifs.map((motif) => (
              <span
                key={motif}
                className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
                  isDarkMode ? 'bg-indigo-900/50 text-indigo-200' : 'bg-indigo-100 text-indigo-800'
                }`}
              >
                {motif}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {drills.length > 0 ? (
        <div className="mb-4">
          <p className={`text-sm font-medium mb-1 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>Drills</p>
          <ul className={`list-disc pl-5 text-sm space-y-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            {drills.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {impact.phase_risk ? (
        <p className={`text-xs ${isDarkMode ? 'text-gray-500' : 'text-gray-500'}`}>
          Weakest phase risk signal: {trainingBlock.phase_motifs?.weakest_phase || '—'}
        </p>
      ) : null}
    </div>
  );
};

export default TrainingBlockSection;
