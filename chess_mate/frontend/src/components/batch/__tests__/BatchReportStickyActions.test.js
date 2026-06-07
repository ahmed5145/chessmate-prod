import React from 'react';
import { render, waitFor } from '@testing-library/react';
import BatchReportStickyActions from '../BatchReportStickyActions';

jest.mock('../BatchReportActions', () => function MockActions() {
  return <div data-testid="batch-report-actions">Actions</div>;
});

describe('BatchReportStickyActions', () => {
  const originalResizeObserver = global.ResizeObserver;

  beforeEach(() => {
    document.documentElement.style.removeProperty('--batch-report-sticky-actions-height');
  });

  afterEach(() => {
    global.ResizeObserver = originalResizeObserver;
    document.documentElement.style.removeProperty('--batch-report-sticky-actions-height');
  });

  it('renders actions inside sticky chrome', () => {
    const { getByTestId } = render(
      <BatchReportStickyActions batchId="batch-1" hasCoaching />
    );

    expect(getByTestId('batch-report-actions')).toBeInTheDocument();
  });

  it('syncs sticky height css variable via ResizeObserver', async () => {
    const observe = jest.fn();
    const disconnect = jest.fn();

    global.ResizeObserver = jest.fn(function ResizeObserverMock(callback) {
      this.observe = (element) => {
        observe(element);
        Object.defineProperty(element, 'offsetHeight', {
          configurable: true,
          value: 112,
        });
        callback();
      };
      this.disconnect = disconnect;
    });

    const { unmount } = render(<BatchReportStickyActions batchId="batch-1" hasCoaching />);

    await waitFor(() => {
      expect(document.documentElement.style.getPropertyValue('--batch-report-sticky-actions-height')).toBe(
        '112px'
      );
    });
    expect(observe).toHaveBeenCalled();

    unmount();

    expect(disconnect).toHaveBeenCalled();
    expect(document.documentElement.style.getPropertyValue('--batch-report-sticky-actions-height')).toBe(
      '0px'
    );
  });
});
