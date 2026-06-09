import React, { useEffect, useMemo, useState } from 'react';
import { useTheme } from '../../context/ThemeContext';
import { trackSingleGameEvent } from '../../utils/marketingAnalytics';
import {
  buildDrillChecklistItems,
  countChecked,
  drillChecklistStorageKey,
  readDrillChecklistState,
  writeDrillChecklistState,
} from '../../utils/singleGameDrillChecklist';

const DrillChecklistSection = ({
  gameId,
  completedAt = null,
  coaching = {},
  worstMoment = null,
  drillLink = null,
  batchId = null,
}) => {
  const { isDarkMode } = useTheme();
  const [expanded, setExpanded] = useState(true);
  const items = useMemo(
    () => buildDrillChecklistItems({ coaching, worstMoment, drillLink }),
    [coaching, worstMoment, drillLink]
  );
  const storageKey = useMemo(
    () => (gameId ? drillChecklistStorageKey(gameId, completedAt) : null),
    [gameId, completedAt]
  );
  const [checkedMap, setCheckedMap] = useState(() => readDrillChecklistState(storageKey));

  useEffect(() => {
    setCheckedMap(readDrillChecklistState(storageKey));
  }, [storageKey]);

  if (!items.length) {
    return null;
  }

  const checkedCount = countChecked(items, checkedMap);

  const handleToggle = (itemId) => {
    const next = { ...checkedMap, [itemId]: !checkedMap[itemId] };
    setCheckedMap(next);
    writeDrillChecklistState(storageKey, next);

    const allDone = items.every((item) => next[item.id]);
    if (allDone) {
      trackSingleGameEvent('single_game_drill_complete', {
        game_id: gameId,
        batch_id: batchId,
        item_count: items.length,
      });
    }
  };

  return (
    <div className={`mb-6 rounded-lg border ${isDarkMode ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'} shadow-sm`}>
      <button
        type="button"
        className={`flex w-full items-center justify-between px-4 py-3 text-left ${isDarkMode ? 'text-white' : 'text-gray-900'}`}
        onClick={() => setExpanded((value) => !value)}
      >
        <span className="font-semibold">5-minute drill checklist</span>
        <span className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          {checkedCount}/{items.length} done
        </span>
      </button>
      {expanded ? (
        <ul className={`px-4 pb-4 space-y-2 ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>
          {items.map((item) => (
            <li key={item.id} className="flex items-start gap-2">
              <input
                id={`drill-${item.id}`}
                type="checkbox"
                className="mt-1"
                checked={Boolean(checkedMap[item.id])}
                onChange={() => handleToggle(item.id)}
              />
              <label htmlFor={`drill-${item.id}`} className="text-sm leading-snug">
                {item.label}
                {item.url ? (
                  <>
                    {' '}
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={isDarkMode ? 'text-blue-400 underline' : 'text-blue-600 underline'}
                    >
                      Open
                    </a>
                  </>
                ) : null}
              </label>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
};

export default DrillChecklistSection;
