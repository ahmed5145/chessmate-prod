import React, { useCallback, useEffect, useRef, useState } from 'react';
import { FaChevronLeft, FaChevronRight, FaCompress, FaExpand, FaVolumeMute, FaVolumeUp } from 'react-icons/fa';
import FenBoardImage from '../batch/FenBoardImage';
import EvalChart from '../analysis/EvalChart';
import { useTheme } from '../../context/ThemeContext';
import {
  countFullMoves,
  findMoveIndexByNumber,
  formatBestMoveDisplay,
  formatMoveLabel,
  formatMoveSideLabel,
  getMoveArrowColors,
  pickEvalSeries,
} from '../../utils/singleGameMoves';
import { formatReviewPositionEvalVerbose } from '../../utils/singleGameClassification';
import {
  emitMoveNavigationFeedback,
  readSoundEnabled,
  writeSoundEnabled,
} from '../../utils/singleGameMoveSound';
import MoveClassificationBadge from './MoveClassificationBadge';
import PositionEvalBar from './PositionEvalBar';

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

const MoveCaption = ({ move, playerColor, isDarkMode }) => {
  const bestMove = formatBestMoveDisplay(move);
  const sideLabel = formatMoveSideLabel(move, playerColor);
  const classification = move.displayClassification || 'neutral';
  const summary = move.evalSummary || {};
  return (
    <div className={`text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
      <p className="flex flex-wrap items-center gap-2">
        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
          move.isPlayerMove
            ? (isDarkMode ? 'bg-indigo-900/50 text-indigo-200' : 'bg-indigo-100 text-indigo-800')
            : (isDarkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700')
        }`}
        >
          {sideLabel}
        </span>
        <span className="font-medium">{formatMoveLabel(move)}</span>
        <MoveClassificationBadge classification={classification} />
      </p>
      {summary.showBestLine ? (
        <p className={`mt-1 text-xs ${isDarkMode ? 'text-emerald-300' : 'text-emerald-700'}`}>
          Best {bestMove}: <strong>{summary.bestLine}</strong>
        </p>
      ) : null}
      {summary.showAfter && move.isPlayerMove ? (
        <p className={`mt-1 text-xs ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          After {move.san}: <strong>{summary.after}</strong>
        </p>
      ) : null}
    </div>
  );
};

const MoveBoard = ({ move, playerColor, boardSize = 320 }) => {
  if (!move?.fen) {
    return <p className="text-gray-500">Board unavailable for this move.</p>;
  }

  const { playedArrowColor, bestArrowColor, icon } = getMoveArrowColors(move, playerColor);

  return (
    <FenBoardImage
      fen={move.fen}
      size={boardSize}
      orientation={playerColor || 'white'}
      playedMoveUci={move.uci}
      bestMoveUci={bestArrowColor ? move.bestMoveUci : null}
      playedArrowColor={playedArrowColor}
      bestArrowColor={bestArrowColor}
      playedArrowIcon={icon}
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
  const [soundEnabled, setSoundEnabled] = useState(() => readSoundEnabled());
  const isFirstNavigationRef = useRef(true);

  useEffect(() => {
    setSelectedIndex(resolveIndex(initialMoveNumber, initialMoveIsWhite));
  }, [initialMoveNumber, initialMoveIsWhite, resolveIndex]);

  const selectedMove = moves[selectedIndex] || moves[0];
  const evalPoints = pickEvalSeries(moves, playerColor);
  const selectedEval = formatReviewPositionEvalVerbose(selectedMove, playerColor);
  const canGoBack = selectedIndex > 0;
  const canGoForward = selectedIndex < moves.length - 1;

  const handleSelect = useCallback((index) => {
    const previousIndex = selectedIndex;
    setSelectedIndex(index);
    if (onMoveIndexChange) {
      onMoveIndexChange(index);
    }
    if (!isFirstNavigationRef.current && index !== previousIndex) {
      const move = moves[index];
      emitMoveNavigationFeedback(move?.displayClassification || move?.classification);
    }
    isFirstNavigationRef.current = false;
  }, [moves, onMoveIndexChange, selectedIndex]);

  const toggleSound = useCallback(() => {
    const next = !soundEnabled;
    setSoundEnabled(next);
    writeSoundEnabled(next);
    if (next) {
      emitMoveNavigationFeedback('neutral');
    }
  }, [soundEnabled]);

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

  const headerActionClass = isDarkMode
    ? 'border-gray-600 text-gray-200 hover:bg-gray-700'
    : 'border-gray-300 text-gray-700 hover:bg-gray-50';

  const soundToggleButton = (
    <button
      type="button"
      onClick={toggleSound}
      className={`inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium transition ${headerActionClass}`}
      aria-label={soundEnabled ? 'Mute move sounds' : 'Enable move sounds'}
      aria-pressed={soundEnabled}
    >
      {soundEnabled ? <FaVolumeUp aria-hidden="true" /> : <FaVolumeMute aria-hidden="true" />}
      {soundEnabled ? 'Sound on' : 'Sound off'}
    </button>
  );

  const expandButton = (
    <button
      type="button"
      onClick={() => setIsExpanded(true)}
      className={`inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium transition ${headerActionClass}`}
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
          <div className="flex flex-wrap items-center gap-2">
            {soundToggleButton}
            {expandButton}
          </div>
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
              <PositionEvalBar
                evalText={selectedEval.text}
                tone={selectedEval.tone}
                playerColor={playerColor}
              />
              <MoveCaption move={selectedMove} playerColor={playerColor} isDarkMode={isDarkMode} />
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
                  className={`flex w-full items-center gap-2 text-left px-3 py-2 text-sm border-b last:border-b-0 ${
                    index === selectedIndex
                      ? (isDarkMode ? 'bg-indigo-900/40 text-white' : 'bg-indigo-50 text-indigo-900')
                      : (isDarkMode ? 'text-gray-300 hover:bg-gray-700' : 'text-gray-700 hover:bg-gray-50')
                  } ${isDarkMode ? 'border-gray-700' : 'border-gray-100'}`}
                >
                  <span className="font-medium">{move.displayLabel || formatMoveLabel(move)}</span>
                  <span className="ml-2 inline-flex">
                    <MoveClassificationBadge classification={move.displayClassification || 'neutral'} showIcon={false} />
                  </span>
                  <span className={`ml-auto text-xs tabular-nums ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    {move.displayLiveEval}
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
                  {formatMoveLabel(selectedMove)} · {countFullMoves(moves)} moves · Arrow keys to step · Esc to close
                </p>
              </div>
              <div className="flex items-center gap-2">
                {soundToggleButton}
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
                    <PositionEvalBar
                      evalText={selectedEval.text}
                      tone={selectedEval.tone}
                      playerColor={playerColor}
                    />
                    <MoveCaption move={selectedMove} playerColor={playerColor} isDarkMode={isDarkMode} />
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
