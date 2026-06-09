import React, { useCallback, useEffect, useState } from 'react';
import { FaChevronLeft, FaChevronRight, FaCompress, FaExpand } from 'react-icons/fa';
import FenBoardImage from '../batch/FenBoardImage';
import EvalChart from '../analysis/EvalChart';
import { useTheme } from '../../context/ThemeContext';
import {
  findMoveIndexByNumber,
  formatBestMoveDisplay,
  formatMoveLabel,
  inferDisplayClassification,
  pickEvalSeries,
} from '../../utils/singleGameMoves';

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

const panelButtonClass = (isDarkMode, disabled = false) => {
  if (disabled) {
    return isDarkMode
      ? 'text-gray-600 cursor-not-allowed'
      : 'text-gray-300 cursor-not-allowed';
  }
  return isDarkMode
    ? 'text-gray-200 hover:bg-gray-700'
    : 'text-gray-700 hover:bg-gray-100';
};

const MoveCaption = ({ move, isDarkMode }) => {
  const bestMove = formatBestMoveDisplay(move);
  const classification = inferDisplayClassification(move);
  return (
    <p className={`text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
      {formatMoveLabel(move)} · Eval after: <strong>{Number(move.evalAfter).toFixed(2)}</strong>
      {bestMove && bestMove !== '-' ? (
        <> · Best: <strong>{bestMove}</strong></>
      ) : null}
      <span className={`ml-2 ${classificationClass(classification, isDarkMode)}`}>
        {classification}
      </span>
    </p>
  );
};

const MoveBoard = ({ move, playerColor, boardSize = 320 }) => {
  if (!move?.fen) {
    return <p className="text-gray-500">Board unavailable for this move.</p>;
  }

  return (
    <FenBoardImage
      fen={move.fen}
      size={boardSize}
      orientation={playerColor || 'white'}
      playedMoveUci={move.uci}
      bestMoveUci={move.isBest ? null : move.bestMoveUci}
    />
  );
};

const SingleGameBoardPanel = ({
  moves = [],
  momentChips = [],
  initialMoveNumber = null,
  initialMoveIsWhite = null,
  playerColor = 'white',
  onMoveIndexChange,
}) => {
  const { isDarkMode } = useTheme();
  const resolveIndex = useCallback((moveNumber, isWhite = initialMoveIsWhite) =>
    findMoveIndexByNumber(moves, moveNumber, {
      isWhite: isWhite === null ? undefined : isWhite,
      playerColor: isWhite === null ? playerColor : undefined,
    }), [initialMoveIsWhite, moves, playerColor]);

  const [selectedIndex, setSelectedIndex] = useState(() =>
    resolveIndex(initialMoveNumber)
  );
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    setSelectedIndex(resolveIndex(initialMoveNumber, initialMoveIsWhite));
  }, [initialMoveNumber, initialMoveIsWhite, resolveIndex]);

  const selectedMove = moves[selectedIndex] || moves[0];
  const evalPoints = pickEvalSeries(moves);
  const canGoBack = selectedIndex > 0;
  const canGoForward = selectedIndex < moves.length - 1;

  const handleSelect = useCallback((index) => {
    setSelectedIndex(index);
    if (onMoveIndexChange) {
      onMoveIndexChange(index);
    }
  }, [onMoveIndexChange]);

  const goToPrevious = useCallback(() => {
    if (selectedIndex > 0) {
      handleSelect(selectedIndex - 1);
    }
  }, [handleSelect, selectedIndex]);

  const goToNext = useCallback(() => {
    if (selectedIndex < moves.length - 1) {
      handleSelect(selectedIndex + 1);
    }
  }, [handleSelect, moves.length, selectedIndex]);

  useEffect(() => {
    if (!isExpanded) {
      return undefined;
    }

    const onKeyDown = (event) => {
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        goToPrevious();
      } else if (event.key === 'ArrowRight') {
        event.preventDefault();
        goToNext();
      } else if (event.key === 'Escape') {
        event.preventDefault();
        setIsExpanded(false);
      }
    };

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKeyDown);

    return () => {
      window.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [isExpanded, goToNext, goToPrevious]);

  if (!moves.length || !selectedMove) {
    return null;
  }

  const chips = momentChips.length
    ? momentChips
    : moves.filter((move) => move.isCritical).map((move) => ({
      moveNumber: move.moveNumber,
      label: move.displayLabel || formatMoveLabel(move),
      classification: move.classification,
    }));

  const expandButton = (
    <button
      type="button"
      onClick={() => setIsExpanded(true)}
      className={`inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium transition ${
        isDarkMode
          ? 'border-gray-600 text-gray-200 hover:bg-gray-700'
          : 'border-gray-300 text-gray-700 hover:bg-gray-50'
      }`}
      aria-label="Expand position review"
    >
      <FaExpand aria-hidden="true" />
      Expand
    </button>
  );

  return (
    <>
      <div className={`mb-8 rounded-lg border p-4 ${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h3 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Position review
          </h3>
          {expandButton}
        </div>

        {chips.length > 0 ? (
          <div className="single-game-no-print md:hidden sticky top-0 z-10 -mx-1 mb-4 pb-2 bg-inherit">
            <div className="flex gap-2 overflow-x-auto px-1 py-1 snap-x snap-mandatory">
              {chips.map((chip) => {
                const index = findMoveIndexByNumber(moves, chip.moveNumber, {
                  isWhite: chip.isWhite === undefined ? undefined : chip.isWhite,
                  playerColor: chip.isWhite === undefined ? playerColor : undefined,
                });
                if (index < 0) {
                  return null;
                }
                return (
                  <button
                    key={`chip-${chip.moveNumber}-${chip.isWhite ? 'w' : 'b'}`}
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
            <MoveBoard move={selectedMove} playerColor={playerColor} boardSize={320} />
            <div className="mt-3">
              <MoveCaption move={selectedMove} isDarkMode={isDarkMode} />
            </div>
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
                  <span className="font-medium">{move.displayLabel || formatMoveLabel(move)}</span>
                  <span className={`ml-2 text-xs ${classificationClass(inferDisplayClassification(move), isDarkMode)}`}>
                    {inferDisplayClassification(move)}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {isExpanded ? (
        <div
          className="single-game-no-print fixed inset-0 z-50 flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Expanded position review"
        >
          <button
            type="button"
            className="absolute inset-0 bg-black/60"
            aria-label="Close expanded position review"
            onClick={() => setIsExpanded(false)}
          />
          <div
            className={`relative flex w-full max-w-6xl flex-col overflow-hidden rounded-xl border shadow-2xl ${
              isDarkMode ? 'bg-gray-900 border-gray-700 text-white' : 'bg-white border-gray-200 text-gray-900'
            }`}
            style={{ maxHeight: '80vh' }}
          >
            <div className={`flex items-center justify-between gap-3 border-b px-4 py-3 ${
              isDarkMode ? 'border-gray-700' : 'border-gray-200'
            }`}
            >
              <div>
                <h3 className="text-lg font-semibold">Position review</h3>
                <p className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                  Move {selectedIndex + 1} of {moves.length} · Use arrow keys to step · Esc to close
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsExpanded(false)}
                className={`inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition ${panelButtonClass(isDarkMode)}`}
                aria-label="Close expanded position review"
              >
                <FaCompress aria-hidden="true" />
                Close
              </button>
            </div>

            <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-4 overflow-y-auto px-4 py-6">
              <div className="flex w-full max-w-3xl items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={goToPrevious}
                  disabled={!canGoBack}
                  className={`rounded-full p-3 transition ${panelButtonClass(isDarkMode, !canGoBack)}`}
                  aria-label="Previous move"
                >
                  <FaChevronLeft aria-hidden="true" />
                </button>

                <div className="flex min-w-0 flex-1 flex-col items-center">
                  <div className="w-full max-w-[min(72vh,560px)]">
                    <MoveBoard move={selectedMove} playerColor={playerColor} boardSize={560} />
                  </div>
                  <div className="mt-4 w-full max-w-xl text-center">
                    <MoveCaption move={selectedMove} isDarkMode={isDarkMode} />
                  </div>
                </div>

                <button
                  type="button"
                  onClick={goToNext}
                  disabled={!canGoForward}
                  className={`rounded-full p-3 transition ${panelButtonClass(isDarkMode, !canGoForward)}`}
                  aria-label="Next move"
                >
                  <FaChevronRight aria-hidden="true" />
                </button>
              </div>

              {chips.length > 0 ? (
                <div className="flex w-full max-w-3xl flex-wrap justify-center gap-2">
                  {chips.map((chip) => {
                    const index = findMoveIndexByNumber(moves, chip.moveNumber, {
                      isWhite: chip.isWhite === undefined ? undefined : chip.isWhite,
                      playerColor: chip.isWhite === undefined ? playerColor : undefined,
                    });
                    if (index < 0) {
                      return null;
                    }
                    return (
                      <button
                        key={`expanded-chip-${chip.moveNumber}-${chip.isWhite ? 'w' : 'b'}`}
                        type="button"
                        onClick={() => handleSelect(index)}
                        className={`rounded-full border px-3 py-1 text-xs font-semibold ${chipClass(index === selectedIndex, isDarkMode)}`}
                      >
                        {chip.label || `Move ${chip.moveNumber}`}
                      </button>
                    );
                  })}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
};

export default SingleGameBoardPanel;
