/**
 * Shared report body for owner and public share views.
 */

import React from 'react';
import { Box } from '@mui/material';
import BatchReportHero from './BatchReportHero';
import BatchReportHeader from './BatchReportHeader';
import CoachingUnavailableBanner from './CoachingUnavailableBanner';
import ExecutiveSummary from './ExecutiveSummary';
import PhaseBreakdown from './PhaseBreakdown';
import RecurringPatterns from './RecurringPatterns';
import TopPriorities from './TopPriorities';
import TrainingPlan from './TrainingPlan';
import GameAccordion from './GameAccordion';
import FailedGamesList from './FailedGamesList';
import TopCriticalMoments from './TopCriticalMoments';
import BatchCompareCard from './BatchCompareCard';
import TimeManagementInsight, { shouldShowTimeManagementInsight } from './TimeManagementInsight';
import OpeningSection from './OpeningSection';
import CoachingInsightsSection from './CoachingInsightsSection';
import StudyDrillLinks from './StudyDrillLinks';
import BatchReportToc, {
  buildBatchReportTocSections,
  hasCoachingInsightsSection,
  hasStudyDrillsSection,
  hasTacticalPatternsSection,
} from './BatchReportToc';
import BatchReportLegend from './BatchReportLegend';
import BatchReportMobileNav from './BatchReportMobileNav';
import PartialBatchBanner from './PartialBatchBanner';
import './batchReportPrint.css';
import './batchReportScreen.css';

const SectionWrap = ({ id, children }) => (
  <Box
    id={id}
    sx={{
      scrollMarginTop: { xs: '168px', md: '88px' },
    }}
  >
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

  const showTimeManagement = shouldShowTimeManagementInsight(batchReport.batch_summary);
  const showStudyDrills = hasStudyDrillsSection(batchReport);
  const tocSections = buildBatchReportTocSections(batchReport, {
    showTimeManagement,
    showStudyDrills,
  });

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
        <BatchReportToc sections={tocSections} />
        <Box sx={{ display: 'grid', gap: 2, minWidth: 0 }}>
          <BatchReportMobileNav sections={tocSections} />

          <BatchReportHero
            batch_summary={batchReport.batch_summary}
            games_count={batchReport.games_count}
            coaching_report={batchReport.coaching_report}
            status={status}
          />

          <PartialBatchBanner batchReport={batchReport} status={status} />

          <CoachingUnavailableBanner coachingReport={batchReport.coaching_report} />

          {status === 'partial' ? (
            <SectionWrap id="batch-section-failed-games">
              <FailedGamesList failures={batchReport.errors || batchReport.failed_games || []} />
            </SectionWrap>
          ) : null}

          <BatchReportHeader
            batch_summary={batchReport.batch_summary}
            games_count={batchReport.games_count}
          />

          <SectionWrap id="batch-section-summary">
            <ExecutiveSummary coaching_report={batchReport.coaching_report} />
          </SectionWrap>

          <SectionWrap id="batch-section-priorities">
            <TopPriorities
              coaching_report={batchReport.coaching_report}
              per_game_results={batchReport.per_game_results}
            />
          </SectionWrap>

          {!readOnly && batchId ? (
            <SectionWrap id="batch-section-compare">
              <BatchCompareCard batchId={batchId} />
            </SectionWrap>
          ) : null}

          <SectionWrap id="batch-section-phases">
            <PhaseBreakdown batch_summary={batchReport.batch_summary} />
          </SectionWrap>

          {showTimeManagement ? (
            <SectionWrap id="batch-section-time-management">
              <TimeManagementInsight batch_summary={batchReport.batch_summary} />
            </SectionWrap>
          ) : null}

          {hasCoachingInsightsSection(batchReport) ? (
            <SectionWrap id="batch-section-coaching-insights">
              <CoachingInsightsSection
                batch_summary={batchReport.batch_summary}
                coaching_report={batchReport.coaching_report}
              />
            </SectionWrap>
          ) : null}

          <SectionWrap id="batch-section-openings">
            <OpeningSection
              batch_summary={batchReport.batch_summary}
              per_game_results={batchReport.per_game_results}
            />
          </SectionWrap>

          {hasTacticalPatternsSection(batchReport) ? (
            <SectionWrap id="batch-section-patterns">
              <RecurringPatterns
                batch_summary={batchReport.batch_summary}
                per_game_results={batchReport.per_game_results}
              />
            </SectionWrap>
          ) : null}

          <SectionWrap id="batch-section-critical-moments">
            <TopCriticalMoments
              batch_summary={batchReport.batch_summary}
              per_game_results={batchReport.per_game_results}
              readOnly={readOnly}
            />
          </SectionWrap>

          {showStudyDrills ? (
            <SectionWrap id="batch-section-drills">
              <StudyDrillLinks batch_summary={batchReport.batch_summary} />
            </SectionWrap>
          ) : null}

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
