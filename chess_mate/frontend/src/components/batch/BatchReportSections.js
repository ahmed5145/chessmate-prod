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
import BatchMomentDiff from './BatchMomentDiff';
import TimeManagementInsight, { shouldShowTimeManagementInsight } from './TimeManagementInsight';
import OpeningSection from './OpeningSection';
import CoachingInsightsSection from './CoachingInsightsSection';
import StudyDrillLinks from './StudyDrillLinks';
import PracticeNextStrip from './PracticeNextStrip';
import {
  collectPracticeNextLinks,
  getRemainingStudyDrillLinks,
} from '../../utils/practiceNextLinks';
import BatchReportToc, {
  buildBatchReportTocSections,
  hasCoachingInsightsSection,
  hasTacticalPatternsSection,
} from './BatchReportToc';
import BatchReportLegend from './BatchReportLegend';
import BatchReportMobileNav from './BatchReportMobileNav';
import PartialBatchBanner from './PartialBatchBanner';
import { BATCH_REPORT_MOBILE_SCROLL_MARGIN_PX } from './batchReportLayout';
import './batchReportPrint.css';
import './batchReportScreen.css';

const SectionWrap = ({ id, children }) => (
  <Box
    id={id}
    sx={{
      scrollMarginTop: { xs: `${BATCH_REPORT_MOBILE_SCROLL_MARGIN_PX}px`, md: '88px' },
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
  const practiceLinks = collectPracticeNextLinks({
    coaching_report: batchReport.coaching_report,
    batch_summary: batchReport.batch_summary,
    per_game_results: batchReport.per_game_results,
  });
  const remainingDrillLinks = getRemainingStudyDrillLinks(batchReport);
  const showStudyDrills = remainingDrillLinks.length > 0;
  const tocSections = buildBatchReportTocSections(batchReport, {
    showTimeManagement,
    showStudyDrills,
  });

  return (
    <Box
      className="batch-report-print-root"
      sx={{ width: '100%', maxWidth: '100%', minWidth: 0, overflowX: 'clip' }}
    >
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
            per_game_results={batchReport.per_game_results}
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
            fix_rate={batchReport.fix_rate}
            batchId={batchId}
          />

          <SectionWrap id="batch-section-summary">
            <ExecutiveSummary
              coaching_report={batchReport.coaching_report}
              per_game_results={batchReport.per_game_results}
            />
          </SectionWrap>

          <SectionWrap id="batch-section-priorities">
            <TopPriorities
              coaching_report={batchReport.coaching_report}
              per_game_results={batchReport.per_game_results}
              batch_summary={batchReport.batch_summary}
              batchId={batchId}
            />
            <Box sx={{ mt: 1 }}>
              <PracticeNextStrip links={practiceLinks} />
            </Box>
          </SectionWrap>

          {!readOnly && batchId ? (
            <SectionWrap id="batch-section-compare">
              <BatchMomentDiff
                momentDiff={batchReport.moment_diff}
                batchId={batchId}
              />
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
              batchId={batchId}
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
              batchId={batchId}
            />
          </SectionWrap>

          {showStudyDrills ? (
            <SectionWrap id="batch-section-drills">
              <StudyDrillLinks links={remainingDrillLinks} />
            </SectionWrap>
          ) : null}

          <SectionWrap id="batch-section-training">
            <TrainingPlan coaching_report={batchReport.coaching_report} />
          </SectionWrap>

          <SectionWrap id="batch-section-games">
            <GameAccordion
              per_game_results={batchReport.per_game_results}
              readOnly={readOnly}
              batchId={batchId}
            />
          </SectionWrap>
        </Box>
      </Box>
    </Box>
  );
};

export default BatchReportSections;
