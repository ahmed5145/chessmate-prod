import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { Box, Tab, Tabs } from '@mui/material';
import { useTheme } from '../../context/ThemeContext';
import { getDemoBatchReport } from '../../content/demoBatchReport';
import BatchReportHero from '../batch/BatchReportHero';
import BatchReportHeader from '../batch/BatchReportHeader';
import PriorityCard from '../batch/PriorityCard';
import PhaseBreakdown from '../batch/PhaseBreakdown';
import CoachingInsightsSection from '../batch/CoachingInsightsSection';
import TrainingPlan from '../batch/TrainingPlan';
import { trackMarketingEvent } from '../../utils/marketingAnalytics';
import { MARKETING_SOURCES } from '../../utils/marketingLinks';

const PREVIEW_TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'priority', label: 'Priority' },
  { id: 'insights', label: 'Insights' },
  { id: 'plan', label: 'Plan' },
];

const BatchReportPreview = () => {
  const { isDarkMode } = useTheme();
  const [activeTab, setActiveTab] = useState(0);
  const containerRef = useRef(null);
  const trackedVisible = useRef(false);
  const report = getDemoBatchReport();

  useEffect(() => {
    const node = containerRef.current;
    if (!node || typeof IntersectionObserver === 'undefined') {
      return undefined;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !trackedVisible.current) {
            trackedVisible.current = true;
            trackMarketingEvent('preview_visible', { source: MARKETING_SOURCES.LANDING_EXAMPLE });
          }
        });
      },
      { threshold: 0.35 },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const handleTabChange = (_, nextIndex) => {
    setActiveTab(nextIndex);
    trackMarketingEvent('preview_tab_change', {
      tab: PREVIEW_TABS[nextIndex]?.id,
      source: MARKETING_SOURCES.LANDING_EXAMPLE,
    });
  };

  const priority = report.coaching_report?.top_3_priorities?.[0];

  return (
    <section
      ref={containerRef}
      className="mb-4"
      aria-label="Example Batch Coach report preview"
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <div>
          <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wide ${
            isDarkMode ? 'bg-indigo-900/60 text-indigo-200' : 'bg-indigo-100 text-indigo-800'
          }`}>
            Example report · anonymized games
          </span>
          <p className={`text-sm mt-2 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Same sections as a real report — engine stats, priorities, coaching insights, and a 4-week plan.
          </p>
        </div>
        <Link
          to="/example/batch-report"
          onClick={() => trackMarketingEvent('full_example_open', { source: MARKETING_SOURCES.LANDING_EXAMPLE })}
          className={`inline-flex items-center gap-1 text-sm font-semibold shrink-0 ${
            isDarkMode ? 'text-indigo-300 hover:text-indigo-200' : 'text-indigo-600 hover:text-indigo-700'
          }`}
        >
          View full example
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      <div className={`rounded-2xl border overflow-hidden ${
        isDarkMode ? 'bg-gray-800/80 border-gray-700' : 'bg-white border-gray-200 shadow-lg'
      }`}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          variant="scrollable"
          scrollButtons="auto"
          aria-label="Example report sections"
          sx={{
            borderBottom: 1,
            borderColor: isDarkMode ? 'divider' : 'grey.200',
            minHeight: 44,
            '& .MuiTab-root': { textTransform: 'none', fontWeight: 600, minHeight: 44 },
          }}
        >
          {PREVIEW_TABS.map((tab) => (
            <Tab key={tab.id} label={tab.label} id={`preview-tab-${tab.id}`} aria-controls={`preview-panel-${tab.id}`} />
          ))}
        </Tabs>

        <Box
          role="tabpanel"
          id={`preview-panel-${PREVIEW_TABS[activeTab]?.id}`}
          aria-labelledby={`preview-tab-${PREVIEW_TABS[activeTab]?.id}`}
          sx={{
            position: 'relative',
            maxHeight: { xs: 400, sm: 440 },
            overflow: 'hidden',
            p: { xs: 1.5, sm: 2 },
            pointerEvents: 'none',
            '@media (prefers-reduced-motion: reduce)': {
              scrollBehavior: 'auto',
            },
            '& a, & button': { pointerEvents: 'none' },
          }}
        >
          {activeTab === 0 && (
            <>
              <BatchReportHero
                batch_summary={report.batch_summary}
                games_count={report.games_count}
                coaching_report={report.coaching_report}
                per_game_results={report.per_game_results}
                status={report.status}
                marketingMode
              />
              <BatchReportHeader
                batch_summary={report.batch_summary}
                games_count={report.games_count}
              />
            </>
          )}
          {activeTab === 1 && priority && (
            <PriorityCard
              priority={priority}
              per_game_results={report.per_game_results}
              batch_summary={report.batch_summary}
              showLichessLink={false}
            />
          )}
          {activeTab === 2 && (
            <>
              <PhaseBreakdown batch_summary={report.batch_summary} />
              <CoachingInsightsSection
                batch_summary={report.batch_summary}
                coaching_report={report.coaching_report}
              />
            </>
          )}
          {activeTab === 3 && (
            <TrainingPlan coaching_report={report.coaching_report} />
          )}

          <Box
            sx={{
              position: 'absolute',
              left: 0,
              right: 0,
              bottom: 0,
              height: 72,
              background: (theme) => (
                theme.palette.mode === 'dark'
                  ? 'linear-gradient(to top, rgba(17,24,39,0.95), transparent)'
                  : 'linear-gradient(to top, rgba(255,255,255,0.95), transparent)'
              ),
              pointerEvents: 'none',
            }}
          />
        </Box>
      </div>

      <p className={`mt-3 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
        Full report adds opening gaps, tactical patterns, critical moments, and per-game breakdown.
        {' '}
        <Link
          to="/example/batch-report"
          onClick={() => trackMarketingEvent('preview_deep_review_cta', { source: MARKETING_SOURCES.LANDING_EXAMPLE })}
          className={`font-semibold underline ${isDarkMode ? 'text-indigo-300' : 'text-indigo-600'}`}
        >
          Open full example →
        </Link>
      </p>
    </section>
  );
};

export default BatchReportPreview;
