import React from 'react';
import { render, screen } from '@testing-library/react';
import PhaseBreakdown from '../PhaseBreakdown';

describe('PhaseBreakdown', () => {
  it('renders nothing without phase performance data', () => {
    const { container } = render(<PhaseBreakdown batch_summary={{}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders phase scores, progress bars, and trend chips', () => {
    render(
      <PhaseBreakdown
        batch_summary={{
          phase_performance: {
            opening: { score: 0.82, trend: 'strong' },
            middlegame: { score: 0.48, trend: 'weak' },
            endgame: { accuracy_pct: 61.5, trend: 'inconsistent' },
          },
        }}
      />
    );

    expect(screen.getByText(/Phase performance/i)).toBeInTheDocument();
    expect(screen.getByText('Opening')).toBeInTheDocument();
    expect(screen.getByText('Middlegame')).toBeInTheDocument();
    expect(screen.getByText('Endgame')).toBeInTheDocument();
    expect(screen.getByText('82% stable')).toBeInTheDocument();
    expect(screen.getByText('48% stable')).toBeInTheDocument();
    expect(screen.getByText('61.5% move match')).toBeInTheDocument();
    expect(screen.getByText('Strong')).toBeInTheDocument();
    expect(screen.getByText('Weak')).toBeInTheDocument();
    expect(screen.getByText('Inconsistent')).toBeInTheDocument();
    expect(screen.getByRole('progressbar', { value: { now: 82 } })).toBeInTheDocument();
    expect(screen.getByRole('progressbar', { value: { now: 62 } })).toBeInTheDocument();
  });
});
