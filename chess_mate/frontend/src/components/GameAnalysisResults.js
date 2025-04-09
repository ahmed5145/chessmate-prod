import React from 'react';
import { useTheme } from '../context/ThemeContext';
import { formatNumber } from '../utils/formatters';
import { FaChessKnight, FaClock, FaChartLine, FaExclamationTriangle, FaHourglassHalf } from 'react-icons/fa';

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

const GameAnalysisResults = ({ analysisData }) => {
    const { isDarkMode } = useTheme();

    if (!analysisData) {
        return (
            <div className={`p-6 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'} shadow-sm`}>
                <p className={`text-center ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    No analysis data available
                </p>
            </div>
        );
    }

    // Extract data from the normalized structure
    const analysisResults = analysisData.analysis_results || {};
    const summary = analysisResults.summary || {};
    const feedback = analysisData.feedback || {};

    // Extract metrics
    const overall = summary.overall || {};
    const phases = summary.phases || {};
    const timeManagement = summary.time_management || {};

    // Format metrics for display
    const displayMetrics = {
        accuracy: formatNumber(overall.accuracy || 0),
        mistakes: formatNumber(overall.mistakes || 0),
        timeManagement: formatNumber(timeManagement.time_management_score || 0),
        timePressure: formatNumber(timeManagement.time_pressure_percentage || 0)
    };

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
                    value={`${displayMetrics.timeManagement}%`}
                    icon={FaClock}
                    isDarkMode={isDarkMode}
                />
                <StatItem
                    label="Time Pressure"
                    value={`${displayMetrics.timePressure}%`}
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
    </div>
  );
};

export default GameAnalysisResults;
