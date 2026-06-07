/**
 * Horizontal section pills for mobile / narrow viewports (desktop uses BatchReportToc).
 */

import React, { useEffect, useState } from 'react';
import { Box, Chip } from '@mui/material';
import { scrollToBatchSection } from '../../utils/batchReportScroll';
import {
  BATCH_REPORT_MOBILE_NAV_TOP,
  BATCH_REPORT_PAGE_GUTTER_SX,
} from './batchReportLayout';

const INDIGO = '#4f46e5';

const BatchReportMobileNav = ({ sections = [] }) => {
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
      { rootMargin: '-24% 0px -50% 0px', threshold: [0.1, 0.35, 0.6] }
    );

    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, [sections]);

  if (!sections.length) {
    return null;
  }

  return (
    <Box
      className="batch-report-no-print batch-report-mobile-nav"
      sx={{
        display: { xs: 'block', md: 'none' },
        position: 'sticky',
        top: BATCH_REPORT_MOBILE_NAV_TOP,
        zIndex: 28,
        width: '100vw',
        maxWidth: '100vw',
        marginLeft: 'calc(50% - 50vw)',
        minWidth: 0,
        mb: 1,
        py: 1,
        bgcolor: 'background.default',
        borderBottom: 1,
        borderColor: 'divider',
        boxSizing: 'border-box',
      }}
    >
      <Box
        sx={{
          ...BATCH_REPORT_PAGE_GUTTER_SX,
          display: 'flex',
          gap: 0.75,
          overflowX: 'auto',
          flexWrap: 'nowrap',
          pb: 0.25,
          WebkitOverflowScrolling: 'touch',
          scrollbarWidth: 'none',
          '&::-webkit-scrollbar': { display: 'none' },
        }}
      >
        {sections.map((section) => {
          const isActive = activeId === section.id;
          return (
            <Chip
              key={section.id}
              label={section.label}
              size="small"
              clickable
              onClick={() => {
                scrollToBatchSection(section.id);
                setActiveId(section.id);
              }}
              sx={{
                flexShrink: 0,
                fontWeight: isActive ? 700 : 500,
                bgcolor: isActive ? 'rgba(99, 102, 241, 0.14)' : 'action.hover',
                color: isActive ? INDIGO : 'text.primary',
                border: '1px solid',
                borderColor: isActive ? 'rgba(99, 102, 241, 0.45)' : 'divider',
              }}
            />
          );
        })}
      </Box>
    </Box>
  );
};

export default BatchReportMobileNav;
