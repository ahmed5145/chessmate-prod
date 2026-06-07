/** Shared layout tokens for batch report sticky chrome (matches App Navbar h-16 / pt-16). */

export const BATCH_REPORT_NAVBAR_HEIGHT_PX = 64;

/** Sticky owner actions sit directly below the fixed navbar. */
export const BATCH_REPORT_STICKY_ACTIONS_TOP_PX = BATCH_REPORT_NAVBAR_HEIGHT_PX;

/** Pill nav stacks below navbar + owner actions (0 when actions are not sticky). */
export const BATCH_REPORT_MOBILE_NAV_TOP = `calc(var(--batch-report-navbar-height, ${BATCH_REPORT_NAVBAR_HEIGHT_PX}px) + var(--batch-report-sticky-actions-height, 0px))`;

/** Horizontal padding aligned with MUI Container gutters on the report page. */
export const BATCH_REPORT_PAGE_GUTTER_SX = {
  px: { xs: 2, sm: 3 },
  width: '100%',
  maxWidth: 'lg',
  mx: 'auto',
  boxSizing: 'border-box',
};

/** Scroll offset so section headings clear sticky chrome on mobile. */
export const BATCH_REPORT_MOBILE_SCROLL_MARGIN_PX = 200;
