/**
 * Owner actions — sticky below navbar on narrow viewports so Share stays reachable.
 */

import React, { useEffect, useRef } from 'react';
import { Box } from '@mui/material';
import BatchReportActions from './BatchReportActions';
import {
  BATCH_REPORT_NAVBAR_HEIGHT_PX,
  BATCH_REPORT_PAGE_GUTTER_SX,
  BATCH_REPORT_STICKY_ACTIONS_TOP_PX,
} from './batchReportLayout';

const setStickyActionsHeight = (heightPx) => {
  document.documentElement.style.setProperty(
    '--batch-report-sticky-actions-height',
    `${Math.max(0, Math.round(heightPx))}px`
  );
};

const BatchReportStickyActions = (props) => {
  const barRef = useRef(null);

  useEffect(() => {
    const element = barRef.current;
    if (!element || typeof ResizeObserver === 'undefined') {
      return undefined;
    }

    const syncHeight = () => setStickyActionsHeight(element.offsetHeight);

    syncHeight();
    const observer = new ResizeObserver(syncHeight);
    observer.observe(element);

    return () => {
      observer.disconnect();
      setStickyActionsHeight(0);
    };
  }, []);

  return (
    <Box
      ref={barRef}
      className="batch-report-no-print batch-report-sticky-actions"
      sx={{
        position: { xs: 'sticky', md: 'static' },
        top: { xs: BATCH_REPORT_STICKY_ACTIONS_TOP_PX, md: 0 },
        zIndex: { xs: 30, md: 'auto' },
        width: '100%',
        maxWidth: '100%',
        boxSizing: 'border-box',
        bgcolor: 'background.default',
        borderBottom: { xs: 1, md: 0 },
        borderColor: 'divider',
        py: { xs: 1.25, md: 0 },
        mb: { xs: 0, md: 2 },
      }}
      style={{
        '--batch-report-navbar-height': `${BATCH_REPORT_NAVBAR_HEIGHT_PX}px`,
      }}
    >
      <Box sx={BATCH_REPORT_PAGE_GUTTER_SX}>
        <BatchReportActions {...props} />
      </Box>
    </Box>
  );
};

export default BatchReportStickyActions;
