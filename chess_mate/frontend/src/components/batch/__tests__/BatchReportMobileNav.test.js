import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import BatchReportMobileNav from '../BatchReportMobileNav';

describe('BatchReportMobileNav', () => {
  const sections = [
    { id: 'batch-section-summary', label: 'Executive summary' },
    { id: 'batch-section-priorities', label: 'Top priorities' },
  ];

  beforeAll(() => {
    global.IntersectionObserver = class {
      observe() {}

      disconnect() {}

      unobserve() {}
    };
  });

  beforeEach(() => {
    document.body.innerHTML = `
      <div id="batch-section-summary"></div>
      <div id="batch-section-priorities"></div>
    `;
    Element.prototype.scrollIntoView = jest.fn();
  });

  it('renders section pills', () => {
    render(<BatchReportMobileNav sections={sections} />);
    expect(screen.getByText('Executive summary')).toBeInTheDocument();
    expect(screen.getByText('Top priorities')).toBeInTheDocument();
  });

  it('scrolls when a pill is clicked', () => {
    render(<BatchReportMobileNav sections={sections} />);
    fireEvent.click(screen.getByText('Top priorities'));
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
  });

  it('renders nothing without sections', () => {
    const { container } = render(<BatchReportMobileNav sections={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
