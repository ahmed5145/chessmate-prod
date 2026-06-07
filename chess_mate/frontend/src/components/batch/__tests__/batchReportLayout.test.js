import {
  BATCH_REPORT_MOBILE_NAV_TOP,
  BATCH_REPORT_NAVBAR_HEIGHT_PX,
  BATCH_REPORT_PAGE_GUTTER_SX,
  BATCH_REPORT_STICKY_ACTIONS_TOP_PX,
} from '../batchReportLayout';

describe('batchReportLayout tokens', () => {
  it('aligns sticky chrome with navbar height', () => {
    expect(BATCH_REPORT_STICKY_ACTIONS_TOP_PX).toBe(BATCH_REPORT_NAVBAR_HEIGHT_PX);
    expect(BATCH_REPORT_NAVBAR_HEIGHT_PX).toBe(64);
  });

  it('stacks mobile nav below navbar and sticky actions', () => {
    expect(BATCH_REPORT_MOBILE_NAV_TOP).toContain('var(--batch-report-navbar-height');
    expect(BATCH_REPORT_MOBILE_NAV_TOP).toContain('var(--batch-report-sticky-actions-height');
  });

  it('exposes page gutter styles aligned with report container', () => {
    expect(BATCH_REPORT_PAGE_GUTTER_SX.maxWidth).toBe('lg');
    expect(BATCH_REPORT_PAGE_GUTTER_SX.px).toEqual({ xs: 2, sm: 3 });
  });
});
