import React, { useEffect, useState } from 'react';
import FenBoardImage from '../batch/FenBoardImage';
import EvalChart from '../analysis/EvalChart';
import { useTheme } from '../../context/ThemeContext';
import { findMoveIndexByNumber, pickEvalSeries } from '../../utils/singleGameMoves';

const classificationClass = (classification, isDarkMode) => {
  const value = String(classification || '').toLowerCase();
  if (value === 'blunder' || value === 'mistake') {
    return isDarkMode ? 'text-red-300' : 'text-red-700';
  }
  if (value === 'inaccuracy') {
    return isDarkMode ? 'text-amber-300' : 'text-amber-700';
  }
  if (value === 'best' || value === 'excellent' || value === 'good') {
    return isDarkMode ? 'text-emerald-300' : 'text-emerald-700';
  }
  return isDarkMode ? 'text-gray-300' : 'text-gray-600';
};

const chipClass = (active, isDarkMode) => {
  if (active) {
    return isDarkMode
      ? 'bg-indigo-800 text-white border-indigo-600'
      : 'bg-indigo-600 text-white border-indigo-600';
  }
  return isDarkMode
    ? 'bg-gray-700 text-gray-200 border-gray-600 hover:bg-gray-600'
    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50';
};

const SingleGameBoardPanel = ({
  moves = [],
  momentChips = [],
  initialMoveNumber = null,
  playerColor = 'white',
  onMoveIndexChange,
}) => {
  const { isDarkMode } = useTheme();
  const [selectedIndex, setSelectedIndex] = useState(() =>
    findMoveIndexByNumber(moves, initialMoveNumber)
  );

  useEffect(() => {
    setSelectedIndex(findMoveIndexByNumber(moves, initialMoveNumber));
  }, [moves, initialMoveNumber]);

  const selectedMove = moves[selectedIndex] || moves[0];
  const evalPoints = pickEvalSeries(moves);

  const handleSelect = (index) => {
    setSelectedIndex(index);
    if (onMoveIndexChange) {
      onMoveIndexChange(index);
    }
  };

  if (!moves.length || !selectedMove) {
    return null;
  }

  const chips = momentChips.length
    ? momentChips
    : moves.filter((move) => move.isCritical).map((move) => ({
      moveNumber: move.moveNumber,
      label: `${move.moveNumber}. ${move.san}`,
      classification: move.classification,
    }));

  return (
    <div className={`mb-8 rounded-lg border p-4 ${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
      <h3 className={`text-lg font-semibold mb-4 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
        Position review
      </h3>

      {chips.length > 0 ? (
        <div className="single-game-no-print md:hidden sticky top-0 z-10 -mx-1 mb-4 pb-2 bg-inherit">
          <div className="flex gap-2 overflow-x-auto px-1 py-1 snap-x snap-mandatory">
            {chips.map((chip) => {
              const index = moves.findIndex((move) => move.moveNumber === chip.moveNumber);
              if (index < 0) {
                return null;
              }
              return (
                <button
                  key={`chip-${chip.moveNumber}`}
                  type="button"
                  onClick={() => handleSelect(index)}
                  className={`shrink-0 snap-start rounded-full border px-3 py-1 text-xs font-semibold ${chipClass(index === selectedIndex, isDarkMode)}`}
                >
                  {chip.label || `Move ${chip.moveNumber}`}
                </button>
              );
            })}
          </div>
        </div>
      ) : null}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          {selectedMove.fen ? (
            <FenBoardImage
              fen={selectedMove.fen}
              size={320}
              orientation={playerColor || 'white'}
              playedMoveUci={selectedMove.uci}
              bestMoveUci={selectedMove.isBest ? null : selectedMove.bestMoveUci}
            />
          ) : (
            <p className={isDarkMode ? 'text-gray-400' : 'text-gray-500'}>Board unavailable for this move.</p>
          )}
          <p className={`mt-3 text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            Move {selectedMove.moveNumber}: <strong>{selectedMove.san}</strong>
            {selectedMove.bestMove && selectedMove.bestMove !== '-' ? (
              <> · Best: <strong>{selectedMove.bestMove}</strong></>
            ) : null}
            <span className={`ml-2 ${classificationClass(selectedMove.classification, isDarkMode)}`}>
              {selectedMove.classification}
            </span>
          </p>
        </div>
        <div>
          <EvalChart
            points={evalPoints}
            selectedIndex={selectedIndex}
            onSelectIndex={handleSelect}
          />
          <div className={`mt-3 max-h-48 overflow-y-auto rounded border ${
            isDarkMode ? 'border-gray-700' : 'border-gray-200'
          }`}
          >
            {moves.map((move, index) => (
              <button
                key={`move-row-${move.moveNumber}-${index}`}
                type="button"
                onClick={() => handleSelect(index)}
                className={`w-full text-left px-3 py-2 text-sm border-b last:border-b-0 ${
                  index === selectedIndex
                    ? (isDarkMode ? 'bg-indigo-900/40 text-white' : 'bg-indigo-50 text-indigo-900')
                    : (isDarkMode ? 'text-gray-300 hover:bg-gray-700' : 'text-gray-700 hover:bg-gray-50')
                } ${isDarkMode ? 'border-gray-700' : 'border-gray-100'}`}
              >
                <span className="font-medium">{move.moveNumber}.</span> {move.san}
                <span className={`ml-2 text-xs ${classificationClass(move.classification, isDarkMode)}`}>
                  {move.classification}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SingleGameBoardPanel;
