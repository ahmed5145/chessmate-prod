import React, { useMemo, useState } from 'react';
import { useTheme } from '../../context/ThemeContext';
import { formatNumber } from '../../utils/formatters';
import { FaClock, FaChartLine, FaExclamationTriangle, FaHourglassHalf } from 'react-icons/fa';
import SingleGameHeader from './SingleGameHeader';
import SingleGameFooterCta from './SingleGameFooterCta';
import SingleGameHero from './SingleGameHero';
import ReportInsightCards from './ReportInsightCards';
import SingleGameBoardPanel from './SingleGameBoardPanel';
import CriticalMomentsSection from './CriticalMomentsSection';
import LichessActionButton from '../batch/LichessActionButton';
import {
  annotateMovesForPlayer,
  computePlayerMoveStats,
  findMoveIndexForMoment,
  formatBestMoveDisplay,
  formatMoveLabel,
  formatMovesSummaryLabel,
  normalizeSingleGameMoves,
} from '../../utils/singleGameMoves';
import MoveClassificationBadge from './MoveClassificationBadge';
import { resolveSingleGameDrillLink } from '../../utils/singleGameDrillLinks';
import {
  alignMomentsWithBatchContext,
  alignMovesWithBatchContext,
} from '../../utils/singleGameBatchAlign';
import PhaseStrip from './PhaseStrip';
import TrainingBlockSection from './TrainingBlockSection';
import SingleGameReportActions from './SingleGameReportActions';
import EngineMetaNote from './EngineMetaNote';
import { trackSingleGameEvent } from '../../utils/marketingAnalytics';
import './singleGamePrint.css';

const StatItem = ({ label, value, icon: Icon, isDarkMode }) => (
  <div className={`flex items-center p-4 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'} shadow-sm`}>
    <div className={`p-3 rounded-full ${isDarkMode ? 'bg-blue-900' : 'bg-blue-100'} mr-4`}>
      <Icon className={`text-xl ${isDarkMode ? 'text-blue-400' : 'text-blue-600'}`} />
    </div>
    <div>
      <p className={`text-sm font-medium ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>{label}</p>
      <p className={`text-2xl font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
        {typeof value === 'number' ? formatNumber(value) : value}
      </p>
    </div>
  </div>
);

const getClassificationBadgeClass = (classification, isDarkMode) => {
  const value = String(classification || 'neutral').toLowerCase().replace(/_/g, ' ');

  if (value === 'brilliant') {
    return isDarkMode ? 'bg-cyan-900 text-cyan-300' : 'bg-cyan-100 text-cyan-700';
  }
  if (value === 'great' || value === 'great move') {
    return isDarkMode ? 'bg-blue-950 text-blue-300' : 'bg-blue-900 text-blue-100';
  }
  if (value === 'blunder' || value === 'mistake') {
    return isDarkMode ? 'bg-red-900 text-red-300' : 'bg-red-100 text-red-700';
  }
  if (value === 'inaccuracy') {
    return isDarkMode ? 'bg-amber-900 text-amber-300' : 'bg-amber-100 text-amber-700';
  }
  if (value === 'best' || value === 'excellent' || value === 'good') {
    return isDarkMode ? 'bg-emerald-900 text-emerald-300' : 'bg-emerald-100 text-emerald-700';
  }
  return isDarkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700';
};

const formatClassificationLabel = (classification) => {
  const normalized = String(classification || 'neutral').toLowerCase().replace(/_/g, ' ');
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
};

const pickNumber = (...values) => {
  for (const value of values) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return 0;
};

const pickAccuracy = (overallAccuracy, moveQualityAccuracy, ...fallbacks) => {
  const overallParsed = Number(overallAccuracy);
  const moveQualityParsed = Number(moveQualityAccuracy);

  if (Number.isFinite(overallParsed) && overallParsed > 0) {
    return overallParsed;
  }
  if (Number.isFinite(moveQualityParsed) && moveQualityParsed > 0) {
    return moveQualityParsed;
  }
  return pickNumber(overallAccuracy, moveQualityAccuracy, ...fallbacks);
};

const SingleGameReport = ({
  analysisData,
  analysis,
  batchId = null,
  initialMoveNumber = null,
  gameId = null,
  priority = null,
  onReanalyze = null,
}) => {
  const { isDarkMode } = useTheme();
  const [focusMoveNumber, setFocusMoveNumber] = useState(initialMoveNumber);
  const [focusMoveIsWhite, setFocusMoveIsWhite] = useState(null);
  const resolvedAnalysisData = analysisData || analysis;

  const {
    gameContext,
    engineMeta,
    coaching,
    criticalMoments,
    displayMetrics,
    tableMoves,
    drillLink,
    playerColor,
    batchContext,
    trainingBlock,
    phaseData,
    playerStats,
    worstMoment,
  } = useMemo(() => {
    if (!resolvedAnalysisData) {
      return {};
    }

    const context = resolvedAnalysisData.game_context || {};
    const meta = resolvedAnalysisData.engine_meta || {};
    const coach = resolvedAnalysisData.coaching
      || resolvedAnalysisData.feedback?.coaching
      || {};
    const moments = Array.isArray(resolvedAnalysisData.critical_moments)
      ? resolvedAnalysisData.critical_moments
      : (coach.critical_moments || []);

    const analysisResults = resolvedAnalysisData.analysis_results || {};
    const metrics = resolvedAnalysisData.metrics || {};
    const hasMetrics = metrics && Object.keys(metrics).length > 0;
    const metricsSummary = metrics && typeof metrics.summary === 'object' ? metrics.summary : metrics;
    const metricsData = hasMetrics ? metricsSummary : (analysisResults.summary || analysisResults || {});
    const feedback = resolvedAnalysisData.feedback || resolvedAnalysisData.ai_feedback || {};
    const rawMoves = resolvedAnalysisData.moves
      || resolvedAnalysisData.movesAnalysis
      || analysisResults.moves
      || [];

    const overall = metricsData.overall || {};
    const moveQuality = metricsData.move_quality || metrics.move_quality || {};
    const phaseData = metricsData.phases || metrics.phases || {};
    const timeManagement = metricsData.time_management || analysisResults.time_management || {};

    const hasSummaryContent = Object.keys(overall).length > 0 || Object.keys(phaseData).length > 0 || rawMoves.length > 0;
    const hasUsefulFeedback = Array.isArray(feedback.strengths) ? feedback.strengths.length > 0 : false;
    const unavailable = metricsData.data_status === 'unavailable' && !hasSummaryContent && !hasUsefulFeedback;

    const hasMoveTimeData = rawMoves.some((move) => {
      const candidate = move.time_spent ?? move.time ?? move.clock;
      return Number.isFinite(Number(candidate)) && Number(candidate) > 0;
    });
    const hasComputedTimeMetrics = [
      timeManagement.time_management_score,
      timeManagement.time_pressure_percentage,
      timeManagement.average_time,
      timeManagement.avg_time_per_move,
    ].some((value) => Number.isFinite(Number(value)) && Number(value) > 0);
    const explicitTimeDataStatus = String(timeManagement.data_status || '').toLowerCase();
    const showTimeUnavailable = explicitTimeDataStatus
      ? explicitTimeDataStatus === 'unavailable'
      : (!hasMoveTimeData && !hasComputedTimeMetrics);

    const accuracy = unavailable
      ? 'N/A'
      : formatNumber(
        pickAccuracy(overall.accuracy, moveQuality.accuracy, overall.accuracy_score, metricsData.accuracy)
      );
    const mistakeCount = pickNumber(
      overall.mistakes,
      overall.total_mistakes,
      pickNumber(overall.blunders, 0) + pickNumber(overall.mistakes, 0)
    );
    const mistakes = unavailable ? 'N/A' : String(Math.round(mistakeCount));

    let timeMgmt = unavailable ? 'N/A' : formatNumber(pickNumber(timeManagement.time_management_score, overall.time_management_score));
    let timePressure = unavailable ? 'N/A' : formatNumber(pickNumber(timeManagement.time_pressure_percentage));
    if (showTimeUnavailable) {
      timeMgmt = 'N/A';
      timePressure = 'N/A';
    }

    const batchCtx = resolvedAnalysisData.batch_context || null;
    const playerSide = context.player_color || 'white';
    const normalizedMoves = annotateMovesForPlayer(
      alignMovesWithBatchContext(
        normalizeSingleGameMoves(rawMoves, playerSide),
        batchCtx,
      ),
      playerSide,
    );
    const computedStats = computePlayerMoveStats(normalizedMoves, playerSide);
    const alignedMoments = alignMomentsWithBatchContext(moments, batchCtx);
    const worstMoment = alignedMoments[0] || null;
    const drill = resolveSingleGameDrillLink({ moment: worstMoment, gameContext: context });
    const training = resolvedAnalysisData.training_block
      || feedback.training_block
      || {};

    return {
      gameContext: context,
      engineMeta: meta,
      coaching: coach,
      criticalMoments: alignedMoments,
      batchContext: batchCtx,
      trainingBlock: training,
      phaseData,
      displayMetrics: {
        accuracy: normalizedMoves.length ? `${computedStats.accuracy}%` : (accuracy === 'N/A' ? 'N/A' : `${accuracy}%`),
        errors: normalizedMoves.length ? String(computedStats.errors) : mistakes,
        showTimeStats: !showTimeUnavailable && timeMgmt !== 'N/A',
        timeManagement: timeMgmt === 'N/A' ? null : `${timeMgmt}%`,
        timePressure: timePressure === 'N/A' ? null : `${timePressure}%`,
      },
      playerStats: computedStats,
      tableMoves: normalizedMoves,
      drillLink: drill,
      worstMoment,
      playerColor: context.player_color || 'white',
    };
  }, [resolvedAnalysisData]);

  if (!resolvedAnalysisData) {
    return (
      <div className={`p-6 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'} shadow-sm`}>
        <p className={`text-center ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          No analysis data available
        </p>
      </div>
    );
  }

  const momentChips = criticalMoments.map((moment) => ({
    moveNumber: moment.move_number,
    label: `Move ${moment.move_number}`,
    classification: moment.type,
    isWhite: moment.player_color === 'white',
  }));

  return (
    <div className={`single-game-print-root p-6 ${isDarkMode ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-900'}`}>
      <SingleGameHeader gameContext={gameContext} />

      <SingleGameReportActions
        gameId={gameId || gameContext?.game_id}
        batchId={batchId || batchContext?.batch_id}
        move={focusMoveNumber ?? initialMoveNumber}
        priority={priority}
        onReanalyze={onReanalyze}
      />

      <EngineMetaNote engineMeta={engineMeta} batchContext={batchContext} />

      <SingleGameHero coaching={coaching} worstMoment={worstMoment} playerStats={playerStats} />

      <ReportInsightCards
        playerStats={playerStats}
        worstMoment={worstMoment}
        gameContext={gameContext}
        phaseData={phaseData}
        playerColor={playerColor}
      />

      <PhaseStrip
        phases={phaseData}
        phaseNotes={coaching.phase_notes || {}}
        batchPhasePerformance={batchContext?.batch_phase_performance}
      />

      <TrainingBlockSection trainingBlock={trainingBlock} />

      {drillLink?.url ? (
        <div className="mb-6">
          <LichessActionButton
            label={drillLink.label}
            url={drillLink.url}
            kind={drillLink.kind}
            onClick={() => trackSingleGameEvent('single_game_drill_click', {
              game_id: gameId || gameContext?.game_id,
              batch_id: batchId || batchContext?.batch_id,
              drill_kind: drillLink.kind,
            })}
          />
        </div>
      ) : null}

      <SingleGameBoardPanel
        moves={tableMoves}
        momentChips={momentChips}
        initialMoveNumber={focusMoveNumber ?? initialMoveNumber}
        initialMoveIsWhite={focusMoveIsWhite}
        playerColor={playerColor}
        onMoveIndexChange={(index) => {
          const move = tableMoves[index];
          if (move?.moveNumber) {
            setFocusMoveNumber(move.moveNumber);
            setFocusMoveIsWhite(move.isWhite);
          }
        }}
      />

      <CriticalMomentsSection
        moments={criticalMoments}
        playerColor={playerColor}
        onSelectMoment={(moment) => {
          const index = findMoveIndexForMoment(tableMoves, moment, playerColor);
          const move = tableMoves[index];
          if (move?.moveNumber != null) {
            setFocusMoveNumber(move.moveNumber);
            setFocusMoveIsWhite(move.isWhite);
          }
        }}
      />

      <div className={`grid grid-cols-1 gap-4 mb-8 ${
        displayMetrics.showTimeStats ? 'md:grid-cols-2 lg:grid-cols-4' : 'md:grid-cols-2'
      }`}
      >
        <StatItem label="Your accuracy" value={displayMetrics.accuracy} icon={FaChartLine} isDarkMode={isDarkMode} />
        <StatItem label="Your errors" value={displayMetrics.errors} icon={FaExclamationTriangle} isDarkMode={isDarkMode} />
        {displayMetrics.showTimeStats ? (
          <>
            <StatItem label="Time Management" value={displayMetrics.timeManagement} icon={FaClock} isDarkMode={isDarkMode} />
            <StatItem label="Time Pressure" value={displayMetrics.timePressure} icon={FaHourglassHalf} isDarkMode={isDarkMode} />
          </>
        ) : null}
      </div>
      {!displayMetrics.showTimeStats ? (
        <p className={`mb-8 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          Clock data was not available for this game, so time management stats are hidden.
        </p>
      ) : null}

      {tableMoves.length > 0 ? (
        <details className={`mb-8 rounded-lg border ${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
          <summary className={`cursor-pointer px-4 py-3 font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            All moves ({formatMovesSummaryLabel(tableMoves)})
          </summary>
          <div className="px-4 pb-4 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className={isDarkMode ? 'text-gray-300' : 'text-gray-600'}>
                  <th className="text-left py-2 pr-4">Move</th>
                  <th className="text-left py-2 pr-4">Side</th>
                  <th className="text-left py-2 pr-4">Played</th>
                  <th className="text-left py-2 pr-4">Best</th>
                  <th className="text-left py-2 pr-4">Class</th>
                  <th className="text-right py-2">Live / Best</th>
                </tr>
              </thead>
              <tbody>
                {tableMoves.map((move, idx) => (
                  <tr
                    key={`${move.moveNumber}-${move.san}-${idx}`}
                    className={`${
                      isDarkMode ? 'border-t border-gray-700' : 'border-t border-gray-200'
                    } ${move.isPlayerMove
                      ? (isDarkMode ? '' : '')
                      : (isDarkMode ? 'bg-gray-800/40' : 'bg-gray-50')}`}
                  >
                    <td className="py-2 pr-4">{move.displayLabel || formatMoveLabel(move)}</td>
                    <td className={`py-2 pr-4 text-xs font-semibold ${
                      move.isPlayerMove
                        ? (isDarkMode ? 'text-indigo-300' : 'text-indigo-700')
                        : (isDarkMode ? 'text-gray-400' : 'text-gray-500')
                    }`}
                    >
                      {move.sideLabel}
                    </td>
                    <td className="py-2 pr-4 font-medium">{move.san}</td>
                    <td className="py-2 pr-4">{move.displayBestMove || formatBestMoveDisplay(move)}</td>
                    <td className="py-2 pr-4">
                      <MoveClassificationBadge classification={move.displayClassification || 'neutral'} />
                    </td>
                    <td className="py-2 text-right tabular-nums">
                      <div>{move.displayLiveEval}</div>
                      {move.evalSummary?.showBestLine ? (
                        <div className={`text-xs ${isDarkMode ? 'text-emerald-300' : 'text-emerald-700'}`}>
                          {move.displayBestLineEval}
                        </div>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      ) : null}

      <SingleGameFooterCta batchId={batchId} />
    </div>
  );
};

export default SingleGameReport;
