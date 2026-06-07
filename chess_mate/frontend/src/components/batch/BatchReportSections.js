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
import RatingBandCoaching from './RatingBandCoaching';
import BatchReportToc from './BatchReportToc';
import BatchReportLegend from './BatchReportLegend';
import './batchReportPrint.css';
import './batchReportScreen.css';

const SectionWrap = ({ id, children }) => (
  <Box id={id} sx={{ scrollMarginTop: '88px' }}>
    {children}
  </Box>
);

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
    <Box className="batch-report-print-root">
      <BatchReportLegend />
      <Box
        className="batch-report-sections-layout"
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', md: '212px 1fr' },
          gap: { xs: 0, md: 2 },
          alignItems: 'start',
        }}
      >
        <BatchReportToc />
        <Box sx={{ display: 'grid', gap: 2, minWidth: 0 }}>
          {status === 'partial' ? (
            <FailedGamesList failures={batchReport.errors || batchReport.failed_games || []} />
          ) : null}
          <BatchReportHeader
            batch_summary={batchReport.batch_summary}
            games_count={batchReport.games_count}
          />
          {!readOnly && batchId ? <BatchCompareCard batchId={batchId} /> : null}
          <SectionWrap id="batch-section-critical-moments">
            <TopCriticalMoments
              batch_summary={batchReport.batch_summary}
              per_game_results={batchReport.per_game_results}
              readOnly={readOnly}
            />
          </SectionWrap>
          <SectionWrap id="batch-section-time-management">
            <TimeManagementInsight batch_summary={batchReport.batch_summary} />
          </SectionWrap>
          <SectionWrap id="batch-section-summary">
            <ExecutiveSummary coaching_report={batchReport.coaching_report} />
          </SectionWrap>
          <SectionWrap id="batch-section-phases">
            <PhaseBreakdown batch_summary={batchReport.batch_summary} />
          </SectionWrap>
          <SectionWrap id="batch-section-repertoire">
            <RepertoireGaps
              batch_summary={batchReport.batch_summary}
              per_game_results={batchReport.per_game_results}
            />
          </SectionWrap>
          <SectionWrap id="batch-section-patterns">
            <RecurringPatterns
              batch_summary={batchReport.batch_summary}
              per_game_results={batchReport.per_game_results}
            />
          </SectionWrap>
          <RatingBandCoaching batch_summary={batchReport.batch_summary} />
          <StudyDrillLinks batch_summary={batchReport.batch_summary} />
          <SectionWrap id="batch-section-coaching">
            <CoachingNarrative coaching_report={batchReport.coaching_report} />
          </SectionWrap>
          <SectionWrap id="batch-section-priorities">
            <TopPriorities
              coaching_report={batchReport.coaching_report}
              per_game_results={batchReport.per_game_results}
            />
          </SectionWrap>
          <SectionWrap id="batch-section-training">
            <TrainingPlan coaching_report={batchReport.coaching_report} />
          </SectionWrap>
          <SectionWrap id="batch-section-games">
            <GameAccordion per_game_results={batchReport.per_game_results} readOnly={readOnly} />
          </SectionWrap>
        </Box>
      </Box>
    </Box>
  );
};

export default BatchReportSections;
