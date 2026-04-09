import React from 'react';
import { useTheme } from '../context/ThemeContext';
import { formatNumber } from '../utils/formatters';
import { FaClock, FaChartLine, FaExclamationTriangle, FaHourglassHalf } from 'react-icons/fa';

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

const PhaseAnalysis = ({ phase, data, isDarkMode }) => (
    <div className="mb-6 p-4 rounded-lg bg-gray-800 shadow-sm">
        <h3 className={`text-lg font-semibold mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>{phase}</h3>
        {data.feedback.analysis && (
            <p className="mb-4 text-gray-400">{data.feedback.analysis}</p>
        )}
        <div className="grid grid-cols-2 gap-4">
            <div>
                <p className="text-sm font-medium text-gray-400">Accuracy</p>
                <p className="text-xl font-semibold text-white">{formatNumber(data.accuracy)}%</p>
            </div>
            <div>
                <p className="text-sm font-medium text-gray-400">Mistakes</p>
                <p className="text-xl font-semibold text-white">{data.mistakes}</p>
            </div>
            {data.opportunities > 0 && (
                <div>
                    <p className="text-sm font-medium text-gray-400">Opportunities</p>
                    <p className="text-xl font-semibold text-white">{data.opportunities}</p>
          </div>
            )}
            {data.bestMoves > 0 && (
                <div>
                    <p className="text-sm font-medium text-gray-400">Best Moves</p>
                    <p className="text-xl font-semibold text-white">{data.bestMoves}</p>
          </div>
            )}
        </div>
    </div>
);

const getClassificationBadgeClass = (classification, isDarkMode) => {
    const value = String(classification || 'neutral').toLowerCase();

    if (value === 'brilliant') {
        return isDarkMode ? 'bg-cyan-900 text-cyan-300' : 'bg-cyan-100 text-cyan-700';
    }
    if (value === 'great' || value === 'great move') {
        return isDarkMode ? 'bg-blue-950 text-blue-300' : 'bg-blue-900 text-blue-100';
    }

    if (value === 'best' || value === 'excellent') {
        return isDarkMode ? 'bg-emerald-900 text-emerald-300' : 'bg-emerald-100 text-emerald-700';
    }
    if (value === 'good') {
        return isDarkMode ? 'bg-blue-900 text-blue-300' : 'bg-blue-100 text-blue-700';
    }
    if (value === 'inaccuracy') {
        return isDarkMode ? 'bg-amber-900 text-amber-300' : 'bg-amber-100 text-amber-700';
    }
    if (value === 'mistake' || value === 'blunder') {
        return isDarkMode ? 'bg-red-900 text-red-300' : 'bg-red-100 text-red-700';
    }

    return isDarkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700';
};

const normalizeMove = (move) => {
    const rawDelta =
        move.eval_change ??
        move.evaluation_change ??
        move.delta ??
        move.evaluation ??
        0;

    return {
        moveNumber: move.move_number || 0,
        san: move.san || move.move || '-',
        classification: move.classification || 'neutral',
        evalDelta: Number.isFinite(Number(rawDelta)) ? Number(rawDelta) : 0
    };
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

const GameAnalysisResults = ({ analysisData, analysis }) => {
    const { isDarkMode } = useTheme();
    const resolvedAnalysisData = analysisData || analysis;

    if (!resolvedAnalysisData) {
        return (
            <div className={`p-6 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'} shadow-sm`}>
                <p className={`text-center ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    No analysis data available
                </p>
            </div>
        );
    }

    // Support both legacy and normalized backend response shapes.
    const analysisResults = resolvedAnalysisData.analysis_results || {};
    const metrics = resolvedAnalysisData.metrics || {};
    const hasMetrics = metrics && Object.keys(metrics).length > 0;
    const summary = hasMetrics ? metrics : (analysisResults.summary || analysisResults || {});
    const feedback = resolvedAnalysisData.feedback || resolvedAnalysisData.ai_feedback || {};
    const rawMoves =
        resolvedAnalysisData.moves ||
        resolvedAnalysisData.movesAnalysis ||
        analysisResults.moves ||
        [];
    const moves = Array.isArray(rawMoves) ? rawMoves.map(normalizeMove) : [];

    // Extract metrics
    const overall = summary.overall || {};
    const moveQuality = summary.move_quality || metrics.move_quality || analysisResults.move_quality || {};
    const phases = summary.phases || metrics.phases || analysisResults.phases || {};
    const timeManagement = summary.time_management || analysisResults.time_management || {};
    const hasMoveTimeData = rawMoves.some((move) => {
        const candidate = move.time_spent ?? move.time ?? move.clock;
        const parsed = Number(candidate);
        return Number.isFinite(parsed) && parsed > 0;
    });

    const hasComputedTimeMetrics = [
        timeManagement.time_management_score,
        timeManagement.time_pressure_percentage,
        timeManagement.average_time,
        timeManagement.avg_time_per_move
    ].some((value) => {
        const parsed = Number(value);
        return Number.isFinite(parsed) && parsed > 0;
    });
    const showTimeAsUnavailable = !hasMoveTimeData && !hasComputedTimeMetrics;

    // Format metrics for display
    const displayMetrics = {
        accuracy: formatNumber(
            pickAccuracy(
                overall.accuracy,
                moveQuality.accuracy,
                overall.accuracy_score,
                summary.accuracy
            )
        ),
        mistakes: formatNumber(
            pickNumber(
                overall.mistakes,
                moveQuality.mistakes,
                overall.total_mistakes,
                pickNumber(overall.blunders, 0) + pickNumber(overall.inaccuracies, 0)
            )
        ),
        timeManagement: formatNumber(
            pickNumber(
                timeManagement.time_management_score,
                overall.time_management_score,
                summary.time_management_score
            )
        ),
        timePressure: formatNumber(
            pickNumber(
                timeManagement.time_pressure_percentage,
                summary.time_pressure_percentage
            )
        )
    };

    if (showTimeAsUnavailable) {
        displayMetrics.timeManagement = 'N/A';
        displayMetrics.timePressure = 'N/A';
    }

    return (
        <div className={`p-6 ${isDarkMode ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-900'}`}>
            {/* Overall Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                <StatItem
                    label="Overall Accuracy"
                    value={`${displayMetrics.accuracy}%`}
                    icon={FaChartLine}
                    isDarkMode={isDarkMode}
                />
                <StatItem
                    label="Mistakes"
                    value={displayMetrics.mistakes}
                    icon={FaExclamationTriangle}
                    isDarkMode={isDarkMode}
                />
                <StatItem
                    label="Time Management"
                    value={displayMetrics.timeManagement === 'N/A' ? 'N/A' : `${displayMetrics.timeManagement}%`}
                    icon={FaClock}
                    isDarkMode={isDarkMode}
                />
                <StatItem
                    label="Time Pressure"
                    value={displayMetrics.timePressure === 'N/A' ? 'N/A' : `${displayMetrics.timePressure}%`}
                    icon={FaHourglassHalf}
                    isDarkMode={isDarkMode}
                />
            </div>

            {/* Phase Analysis */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                {['opening', 'middlegame', 'endgame'].map(phase => (
                    <PhaseAnalysis
                        key={phase}
                        phase={phase.charAt(0).toUpperCase() + phase.slice(1)}
                        data={{
                            accuracy: phases[phase]?.accuracy || 0,
                            mistakes: phases[phase]?.mistakes || 0,
                            opportunities: phases[phase]?.opportunities || 0,
                            bestMoves: phases[phase]?.best_moves || 0,
                            feedback: feedback[phase] || {}
                        }}
                        isDarkMode={isDarkMode}
                    />
                ))}
            </div>

            {/* Feedback Sections */}
            <div className="space-y-6">
                {feedback.strengths && feedback.strengths.length > 0 && (
                    <div className={`p-4 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'}`}>
                        <h3 className="text-lg font-semibold mb-2">Strengths</h3>
                        <ul className="list-disc pl-5 space-y-1">
                            {feedback.strengths.map((strength, idx) => (
                                <li key={idx}>{strength}</li>
              ))}
            </ul>
          </div>
        )}

                {feedback.weaknesses && feedback.weaknesses.length > 0 && (
                    <div className={`p-4 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'}`}>
                        <h3 className="text-lg font-semibold mb-2">Areas for Improvement</h3>
                        <ul className="list-disc pl-5 space-y-1">
                            {feedback.weaknesses.map((weakness, idx) => (
                                <li key={idx}>{weakness}</li>
              ))}
            </ul>
          </div>
        )}

                {feedback.critical_moments && feedback.critical_moments.length > 0 && (
                    <div className={`p-4 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'}`}>
                        <h3 className="text-lg font-semibold mb-2">Critical Moments</h3>
                        <ul className="list-disc pl-5 space-y-1">
                            {feedback.critical_moments.map((moment, idx) => (
                                <li key={idx}>{moment}</li>
                            ))}
                        </ul>
                    </div>
                )}

                {feedback.suggestions && feedback.suggestions.length > 0 && (
                    <div className={`p-4 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'}`}>
                        <h3 className="text-lg font-semibold mb-2">Suggestions</h3>
                        <ul className="list-disc pl-5 space-y-1">
                            {feedback.suggestions.map((suggestion, idx) => (
                                <li key={idx}>{suggestion}</li>
                            ))}
                        </ul>
            </div>
                )}
          </div>

            {moves.length > 0 && (
                <div className={`mt-8 p-4 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'}`}>
                    <h3 className="text-lg font-semibold mb-3">Move Insights</h3>
                    <div className="overflow-x-auto">
                        <table className="min-w-full text-sm">
                            <thead>
                                <tr className={isDarkMode ? 'text-gray-300' : 'text-gray-600'}>
                                    <th className="text-left py-2 pr-4">Move</th>
                                    <th className="text-left py-2 pr-4">Played</th>
                                    <th className="text-left py-2 pr-4">Classification</th>
                                    <th className="text-right py-2">Eval Delta</th>
                                </tr>
                            </thead>
                            <tbody>
                                {moves.map((move, idx) => (
                                    <tr key={`${move.moveNumber}-${move.san}-${idx}`} className={isDarkMode ? 'border-t border-gray-700' : 'border-t border-gray-200'}>
                                        <td className="py-2 pr-4">{move.moveNumber}</td>
                                        <td className="py-2 pr-4 font-medium">{move.san}</td>
                                        <td className="py-2 pr-4">
                                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getClassificationBadgeClass(move.classification, isDarkMode)}`}>
                                                {move.classification}
                                            </span>
                                        </td>
                                        <td className="py-2 text-right">{move.evalDelta.toFixed(2)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
    </div>
  );
};

export default GameAnalysisResults;
