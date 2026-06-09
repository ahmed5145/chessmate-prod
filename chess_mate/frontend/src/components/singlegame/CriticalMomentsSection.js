import React from 'react';
import FenBoardImage from '../batch/FenBoardImage';
import { useTheme } from '../../context/ThemeContext';
import { formatNumber } from '../../utils/formatters';
import { formatBestMoveDisplay, formatUciMove } from '../../utils/singleGameMoves';
import { getMoveArrowStyle } from '../../utils/singleGameClassification';
import MoveClassificationBadge from './MoveClassificationBadge';

const severityClass = (type, isDarkMode) => {
  if (type === 'blunder') {
    return isDarkMode ? 'bg-red-900/50 text-red-200' : 'bg-red-100 text-red-800';
  }
  if (type === 'mistake') {
    return isDarkMode ? 'bg-amber-900/40 text-amber-200' : 'bg-amber-100 text-amber-800';
  }
  return isDarkMode ? 'bg-gray-700 text-gray-200' : 'bg-gray-100 text-gray-700';
};

const formatMomentBestMove = (moment) => {
  if (moment?.best_move && !/^[a-h][1-8][a-h][1-8]/i.test(moment.best_move)) {
    return moment.best_move;
  }
  if (moment?.best_move_uci) {
    return formatUciMove(moment.best_move_uci);
  }
  return formatBestMoveDisplay({ bestMove: moment?.best_move, bestMoveUci: moment?.best_move_uci });
};

const CriticalMomentsSection = ({ moments = [], playerColor = 'white', onSelectMoment }) => {
  const { isDarkMode } = useTheme();

  if (!Array.isArray(moments) || moments.length === 0) {
    return null;
  }

  return (
    <div className="mb-8">
      <h3 className={`text-lg font-semibold mb-3 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
        Critical moments
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {moments.map((moment, index) => {
          const momentPlayerColor = moment.player_color || playerColor;
          const arrowColors = getMoveArrowStyle({
            isBest: moment.classification === 'best',
            isWhite: momentPlayerColor === 'white',
            displayClassification: moment.type || moment.classification,
            bestMoveUci: moment.best_move_uci,
            uci: moment.played_move_uci,
            evalAfter: 0,
            evalChange: -(moment.eval_swing || 0),
          }, playerColor);

          return (
          <div
            key={`sg-moment-${moment.move_number}-${index}`}
            className={`rounded-lg border p-3 ${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}
          >
            <div className="flex items-center gap-2 mb-2">
              <MoveClassificationBadge classification={moment.type || moment.classification || 'inaccuracy'} />
              <span className={`text-xs ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                Move {moment.move_number}
              </span>
            </div>
            {moment.fen ? (
              <button
                type="button"
                className="w-full text-left"
                onClick={() => onSelectMoment && onSelectMoment(moment)}
              >
                <FenBoardImage
                  fen={moment.fen}
                  size={220}
                  orientation={moment.player_color || playerColor}
                  playedMoveUci={moment.played_move_uci}
                  bestMoveUci={arrowColors.bestArrowColor ? moment.best_move_uci : null}
                  playedArrowColor={arrowColors.playedArrowColor}
                  bestArrowColor={arrowColors.bestArrowColor}
                  playedArrowIcon={arrowColors.icon}
                />
              </button>
            ) : null}
            <p className={`mt-2 text-sm font-medium ${isDarkMode ? 'text-gray-200' : 'text-gray-800'}`}>
              Played {moment.played_move || '?'} · best {formatMomentBestMove(moment)}
              {moment.eval_swing != null ? ` · swing ${formatNumber(moment.eval_swing, 2)}` : ''}
            </p>
            {moment.explanation ? (
              <p className={`mt-1 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                {moment.explanation}
              </p>
            ) : null}
          </div>
          );
        })}
      </div>
    </div>
  );
};

export default CriticalMomentsSection;
