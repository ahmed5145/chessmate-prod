import React from 'react';
import { render, screen } from '@testing-library/react';
import MomentTimelineStrip from '../MomentTimelineStrip';

describe('MomentTimelineStrip', () => {
  it('renders nothing when timeline is hidden', () => {
    const { container } = render(
      <MomentTimelineStrip timeline={{ show: false }} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('renders headline and months when timeline is visible', () => {
    render(
      <MomentTimelineStrip
        timeline={{
          show: true,
          headline: 'This pattern appeared in 3 batches',
          months_label: 'Jan, Mar, Jun',
          trend_copy: 'Avg swing down 0.4 pawns since first sighting',
          sparkline: [1.2, 1.0, 0.8],
        }}
      />
    );

    expect(
      screen.getByText(/This pattern appeared in 3 batches/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Jan, Mar, Jun/i)).toBeInTheDocument();
    expect(screen.getByText(/Avg swing down 0.4 pawns/i)).toBeInTheDocument();
  });

  it('supports tailwind variant for single-game cards', () => {
    render(
      <MomentTimelineStrip
        variant="tailwind"
        timeline={{
          show: true,
          headline: 'This pattern appeared 2 times across your reviews',
          months_label: 'Jan, Feb',
        }}
      />
    );

    expect(
      screen.getByText(/2 times across your reviews/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Jan, Feb/i)).toBeInTheDocument();
  });
});
