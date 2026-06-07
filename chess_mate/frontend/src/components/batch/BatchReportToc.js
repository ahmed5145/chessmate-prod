/**
 * Sticky section navigation for batch coach reports.
 */

import React, { useEffect, useState } from 'react';
import { Box, List, ListItemButton, ListItemText, Typography } from '@mui/material';

export const BATCH_REPORT_SECTIONS = [
  { id: 'batch-section-critical-moments', label: 'Critical moments' },
  { id: 'batch-section-time-management', label: 'Time management' },
  { id: 'batch-section-summary', label: 'Executive summary' },
  { id: 'batch-section-phases', label: 'Phase breakdown' },
  { id: 'batch-section-repertoire', label: 'Repertoire gaps' },
  { id: 'batch-section-patterns', label: 'Patterns' },
  { id: 'batch-section-coaching', label: 'Coaching narrative' },
  { id: 'batch-section-priorities', label: 'Top priorities' },
  { id: 'batch-section-training', label: 'Training plan' },
  { id: 'batch-section-games', label: 'Game breakdown' },
];

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

  const scrollToSection = (sectionId) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <Box
      className="batch-report-no-print"
      sx={{
        display: { xs: 'none', md: 'block' },
        position: 'sticky',
        top: 88,
        alignSelf: 'start',
        maxHeight: 'calc(100vh - 96px)',
        overflowY: 'auto',
        pr: 1,
      }}
    >
      <Typography variant="overline" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
        Sections
      </Typography>
      <List dense disablePadding>
        {sections.map((section) => (
          <ListItemButton
            key={section.id}
            selected={activeId === section.id}
            onClick={() => scrollToSection(section.id)}
            sx={{ borderRadius: 1, mb: 0.25 }}
          >
            <ListItemText
              primary={section.label}
              primaryTypographyProps={{ variant: 'body2' }}
            />
          </ListItemButton>
        ))}
      </List>
    </Box>
  );
};

export default BatchReportToc;
