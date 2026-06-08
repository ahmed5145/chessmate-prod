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

const SingleGameBoardPanel = ({
  moves = [],
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

  return (
    <div className={`mb-8 rounded-lg border p-4 ${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
      <h3 className={`text-lg font-semibold mb-4 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
        Position review
      </h3>
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
