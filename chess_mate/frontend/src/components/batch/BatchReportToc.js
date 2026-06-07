/**
 * Sticky section navigation for batch coach reports.
 */

import React, { useEffect, useState } from 'react';
import { Box, List, ListItemButton, ListItemText, Paper, Typography } from '@mui/material';
import { getRemainingStudyDrillLinks } from '../../utils/practiceNextLinks';
import { scrollToBatchSection } from '../../utils/batchReportScroll';

export const BATCH_REPORT_SECTIONS = [
  { id: 'batch-section-summary', label: 'Executive summary' },
  { id: 'batch-section-priorities', label: 'Top priorities' },
  { id: 'batch-section-phases', label: 'Phase breakdown' },
  { id: 'batch-section-time-management', label: 'Time management' },
  { id: 'batch-section-coaching-insights', label: 'Coaching insights' },
  { id: 'batch-section-openings', label: 'Openings' },
  { id: 'batch-section-patterns', label: 'Tactical patterns' },
  { id: 'batch-section-critical-moments', label: 'Critical moments' },
  { id: 'batch-section-drills', label: 'Suggested drills' },
  { id: 'batch-section-training', label: 'Training plan' },
  { id: 'batch-section-games', label: 'Game breakdown' },
];

export const hasCoachingInsightsSection = (batchReport) => {
  const band = batchReport?.batch_summary?.rating_band_coaching;
  const strengths = batchReport?.batch_summary?.strength_patterns || [];
  const narrative = batchReport?.coaching_report?.coaching_narrative;
  const phases = narrative && typeof narrative === 'object'
    ? ['opening', 'middlegame', 'endgame'].filter((key) => narrative[key])
    : [];
  return Boolean(band?.focus) || strengths.length > 0 || phases.length > 0;
};

export const hasTacticalPatternsSection = (batchReport) => {
  const weaknesses = batchReport?.batch_summary?.recurring_weaknesses || [];
  const endgameInsights = batchReport?.batch_summary?.endgame_insights || [];
  return weaknesses.length > 0 || endgameInsights.length > 0;
};

export const hasStudyDrillsSection = (batchReport) => (
  getRemainingStudyDrillLinks(batchReport).length > 0
);

export const buildBatchReportTocSections = (
  batchReport,
  { showTimeManagement = true, showStudyDrills = true } = {}
) => {
  let sections = [...BATCH_REPORT_SECTIONS];
  if (!showTimeManagement) {
    sections = sections.filter((section) => section.id !== 'batch-section-time-management');
  }
  if (!hasCoachingInsightsSection(batchReport)) {
    sections = sections.filter((section) => section.id !== 'batch-section-coaching-insights');
  }
  if (!hasTacticalPatternsSection(batchReport)) {
    sections = sections.filter((section) => section.id !== 'batch-section-patterns');
  }
  if (!showStudyDrills || !hasStudyDrillsSection(batchReport)) {
    sections = sections.filter((section) => section.id !== 'batch-section-drills');
  }
  return sections;
};

const INDIGO = '#4f46e5';

const BatchReportToc = ({ sections = BATCH_REPORT_SECTIONS }) => {
  const [activeId, setActiveId] = useState(sections[0]?.id || null);

  useEffect(() => {
    const elements = sections
      .map((section) => document.getElementById(section.id))
      .filter(Boolean);

    if (elements.length === 0) {
      return undefined;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]?.target?.id) {
          setActiveId(visible[0].target.id);
        }
      },
      { rootMargin: '-20% 0px -55% 0px', threshold: [0.1, 0.35, 0.6] }
    );

    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, [sections]);

  const handleSectionClick = (sectionId) => {
    scrollToBatchSection(sectionId);
    setActiveId(sectionId);
  };

  return (
    <Box
      className="batch-report-no-print batch-report-toc"
      sx={{
        display: { xs: 'none', md: 'block' },
        position: 'sticky',
        top: 88,
        alignSelf: 'start',
        maxHeight: 'calc(100vh - 96px)',
        overflowY: 'auto',
        width: '100%',
        maxWidth: 196,
      }}
    >
      <Paper
        elevation={0}
        sx={(theme) => ({
          p: 1.25,
          borderRadius: 2,
          border: '1px solid',
          borderColor: theme.palette.mode === 'dark' ? 'grey.700' : 'grey.200',
          bgcolor: theme.palette.mode === 'dark' ? 'grey.900' : 'grey.50',
          boxShadow:
            theme.palette.mode === 'dark'
              ? 'none'
              : '0 1px 3px rgba(15, 23, 42, 0.06)',
        })}
      >
        <Typography
          variant="caption"
          sx={{
            display: 'block',
            mb: 1,
            px: 0.75,
            fontWeight: 700,
            letterSpacing: '0.08em',
            color: 'text.secondary',
          }}
        >
          ON THIS PAGE
        </Typography>
        <List dense disablePadding>
          {sections.map((section) => {
            const isActive = activeId === section.id;
            return (
              <ListItemButton
                key={section.id}
                selected={isActive}
                onClick={() => handleSectionClick(section.id)}
                sx={(theme) => ({
                  borderRadius: 1.5,
                  py: 0.65,
                  px: 1,
                  mb: 0.35,
                  borderLeft: '3px solid',
                  borderLeftColor: isActive ? INDIGO : 'transparent',
                  transition: 'background-color 0.15s ease, border-color 0.15s ease',
                  '&:hover': {
                    bgcolor:
                      theme.palette.mode === 'dark'
                        ? 'rgba(99, 102, 241, 0.12)'
                        : 'rgba(99, 102, 241, 0.06)',
                  },
                  '&.Mui-selected': {
                    bgcolor:
                      theme.palette.mode === 'dark'
                        ? 'rgba(99, 102, 241, 0.18)'
                        : 'rgba(99, 102, 241, 0.1)',
                    '&:hover': {
                      bgcolor:
                        theme.palette.mode === 'dark'
                          ? 'rgba(99, 102, 241, 0.22)'
                          : 'rgba(99, 102, 241, 0.14)',
                    },
                  },
                })}
              >
                <ListItemText
                  primary={section.label}
                  primaryTypographyProps={{
                    variant: 'body2',
                    sx: {
                      fontSize: '0.8125rem',
                      lineHeight: 1.35,
                      fontWeight: isActive ? 600 : 500,
                      color: isActive ? INDIGO : 'text.primary',
                    },
                  }}
                />
              </ListItemButton>
            );
          })}
        </List>
      </Paper>
    </Box>
  );
};

export default BatchReportToc;
