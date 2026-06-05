/**
 * Shared report body for owner and public share views.
 */

import React from 'react';
import { Box } from '@mui/material';
import BatchReportHeader from './BatchReportHeader';
import ExecutiveSummary from './ExecutiveSummary';
import PhaseBreakdown from './PhaseBreakdown';
import RecurringPatterns from './RecurringPatterns';
import CoachingNarrative from './CoachingNarrative';
import TopPriorities from './TopPriorities';
import TrainingPlan from './TrainingPlan';
import GameAccordion from './GameAccordion';
import FailedGamesList from './FailedGamesList';
import TopCriticalMoments from './TopCriticalMoments';
import BatchCompareCard from './BatchCompareCard';
import TimeManagementInsight from './TimeManagementInsight';
import RepertoireGaps from './RepertoireGaps';
import StudyDrillLinks from './StudyDrillLinks';
import './batchReportPrint.css';

const BatchReportSections = ({
  batchReport,
  status = 'completed',
  batchId = null,
  readOnly = false
}) => {
  if (!batchReport) {
    return null;
  }

  return (
    <Box className="batch-report-print-root" sx={{ display: 'grid', gap: 2 }}>
      {status === 'partial' ? (
        <FailedGamesList failures={batchReport.errors || batchReport.failed_games || []} />
      ) : null}
      <BatchReportHeader
        batch_summary={batchReport.batch_summary}
        games_count={batchReport.games_count}
      />
      {!readOnly && batchId ? <BatchCompareCard batchId={batchId} /> : null}
      <TopCriticalMoments
        batch_summary={batchReport.batch_summary}
        per_game_results={batchReport.per_game_results}
        readOnly={readOnly}
      />
      <TimeManagementInsight batch_summary={batchReport.batch_summary} />
      <ExecutiveSummary coaching_report={batchReport.coaching_report} />
      <PhaseBreakdown batch_summary={batchReport.batch_summary} />
      <RepertoireGaps batch_summary={batchReport.batch_summary} />
      <RecurringPatterns batch_summary={batchReport.batch_summary} />
      <StudyDrillLinks batch_summary={batchReport.batch_summary} />
      <CoachingNarrative coaching_report={batchReport.coaching_report} />
      <TopPriorities coaching_report={batchReport.coaching_report} />
      <TrainingPlan coaching_report={batchReport.coaching_report} />
      <GameAccordion per_game_results={batchReport.per_game_results} readOnly={readOnly} />
    </Box>
  );
};

export default BatchReportSections;
