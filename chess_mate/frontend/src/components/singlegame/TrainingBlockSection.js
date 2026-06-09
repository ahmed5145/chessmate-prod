import React from 'react';
import { useTheme } from '../../context/ThemeContext';

const formatListLabel = (item) => {
  if (item == null) {
    return '';
  }
  if (typeof item === 'string' || typeof item === 'number') {
    return String(item);
  }
  if (typeof item === 'object') {
    return item.name || item.label || item.goal || item.title || '';
  }
  return String(item);
};

const listItemKey = (item, index, prefix) => {
  const label = formatListLabel(item);
  return label ? `${prefix}-${label}-${index}` : `${prefix}-${index}`;
};

const formatMotifEvidence = (evidence = []) => {
  if (!Array.isArray(evidence) || evidence.length === 0) {
    return '';
  }
  return evidence
    .map((entry) => {
      const move = entry?.move_number ?? entry?.move;
      const san = entry?.san || '';
      if (move != null && Number(move) > 0) {
        return `move ${move}${san ? ` ${san}` : ''}`.trim();
      }
      return san || null;
    })
    .filter(Boolean)
    .join(', ');
};

const TrainingBlockSection = ({ trainingBlock = null }) => {
  const { isDarkMode } = useTheme();

  if (!trainingBlock || typeof trainingBlock !== 'object') {
    return null;
  }

  const focusAreas = Array.isArray(trainingBlock.focus_areas) ? trainingBlock.focus_areas : [];
  const drills = Array.isArray(trainingBlock.drills) ? trainingBlock.drills : [];
  const checklist = Array.isArray(trainingBlock.checklist) ? trainingBlock.checklist : [];
  const motifs = Array.isArray(trainingBlock.phase_motifs?.motifs)
    ? trainingBlock.phase_motifs.motifs
    : [];
  const phaseMotifs = trainingBlock.phase_motifs || {};
  const weeklyTarget = trainingBlock.weekly_target || null;
  const impact = trainingBlock.impact_metrics || {};

  if (!focusAreas.length && !drills.length && !motifs.length && !checklist.length && !weeklyTarget) {
    return null;
  }

  const textMuted = isDarkMode ? 'text-gray-400' : 'text-gray-600';
  const textBody = isDarkMode ? 'text-gray-300' : 'text-gray-700';

  return (
    <div className={`mb-8 rounded-lg border p-4 ${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
      <h3 className={`text-lg font-semibold mb-3 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
        Training focus
      </h3>

      {weeklyTarget?.goal ? (
        <div className={`mb-4 rounded-md border px-3 py-2 text-sm ${isDarkMode ? 'border-indigo-800 bg-indigo-950/30' : 'border-indigo-100 bg-indigo-50'}`}>
          <p className={`font-medium ${isDarkMode ? 'text-indigo-200' : 'text-indigo-900'}`}>
            {weeklyTarget.goal}
          </p>
          {weeklyTarget.measure ? (
            <p className={`mt-1 text-xs ${textMuted}`}>{weeklyTarget.measure}</p>
          ) : null}
        </div>
      ) : null}

      {focusAreas.length > 0 ? (
        <div className="mb-4">
          <p className={`text-sm font-medium mb-1 ${textBody}`}>Focus areas</p>
          <ul className={`list-disc pl-5 text-sm space-y-1 ${textMuted}`}>
            {focusAreas.map((item, index) => (
              <li key={listItemKey(item, index, 'focus')}>{formatListLabel(item)}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {motifs.length > 0 ? (
        <div className="mb-4">
          <p className={`text-sm font-medium mb-1 ${textBody}`}>
            Phase motifs
            {phaseMotifs.weakest_phase ? ` (${phaseMotifs.weakest_phase})` : ''}
          </p>
          {phaseMotifs.correction_rule ? (
            <p className={`text-sm mb-2 ${textMuted}`}>{phaseMotifs.correction_rule}</p>
          ) : null}
          <ul className={`space-y-2 text-sm ${textMuted}`}>
            {motifs.map((motif, index) => {
              const evidence = formatMotifEvidence(motif?.evidence);
              return (
                <li
                  key={listItemKey(motif, index, 'motif')}
                  className={`rounded-md border px-3 py-2 ${isDarkMode ? 'border-gray-700' : 'border-gray-200'}`}
                >
                  <p className={`font-medium ${textBody}`}>
                    {motif?.name || 'Motif'}
                    {motif?.count != null ? ` · ${motif.count} occurrence${motif.count === 1 ? '' : 's'}` : ''}
                  </p>
                  {motif?.correction_rule ? (
                    <p className="mt-1">{motif.correction_rule}</p>
                  ) : null}
                  {evidence ? (
                    <p className={`mt-1 text-xs ${isDarkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                      Evidence: {evidence}
                    </p>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}

      {drills.length > 0 ? (
        <div className="mb-4">
          <p className={`text-sm font-medium mb-1 ${textBody}`}>Drills</p>
          <ul className={`list-disc pl-5 text-sm space-y-1 ${textMuted}`}>
            {drills.map((item, index) => (
              <li key={listItemKey(item, index, 'drill')}>{formatListLabel(item)}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {checklist.length > 0 ? (
        <div className="mb-4">
          <p className={`text-sm font-medium mb-1 ${textBody}`}>Checklist</p>
          <ul className={`list-disc pl-5 text-sm space-y-1 ${textMuted}`}>
            {checklist.map((item, index) => (
              <li key={listItemKey(item, index, 'check')}>{formatListLabel(item)}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {impact.phase_risk ? (
        <p className={`text-xs ${isDarkMode ? 'text-gray-500' : 'text-gray-500'}`}>
          Weakest phase risk signal: {phaseMotifs.weakest_phase || '—'}
        </p>
      ) : null}
    </div>
  );
};

export default TrainingBlockSection;
