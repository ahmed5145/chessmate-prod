import React from 'react';
import { render, screen } from '@testing-library/react';
import CoachingInsightsSection from '../CoachingInsightsSection';

describe('CoachingInsightsSection', () => {
  it('renders nothing when there is no insight content', () => {
    const { container } = render(
      <CoachingInsightsSection batch_summary={{}} coaching_report={{}} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('renders rating band guidance and phase coaching notes', () => {
    render(
      <CoachingInsightsSection
        batch_summary={{
          rating_band_coaching: {
            label: '1200-1400',
            focus: 'Prioritize simple development and king safety.',
            daily_drill: '10 easy puzzles',
          },
        }}
        coaching_report={{
          coaching_narrative: {
            opening: 'You reached playable middlegames.',
            endgame: 'Rook endings need work.',
          },
        }}
      />
    );

    expect(screen.getByText(/Coaching insights/i)).toBeInTheDocument();
    expect(screen.getByText(/For your level \(1200-1400\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Prioritize simple development/i)).toBeInTheDocument();
    expect(screen.getByText(/Daily drill: 10 easy puzzles/i)).toBeInTheDocument();
    expect(screen.getByText(/Phase coaching notes/i)).toBeInTheDocument();
    expect(screen.getByText(/You reached playable middlegames/i)).toBeInTheDocument();
    expect(screen.getByText(/Rook endings need work/i)).toBeInTheDocument();
    expect(screen.queryByText('Middlegame')).not.toBeInTheDocument();
  });

  it('renders strength patterns with frequency', () => {
    render(
      <CoachingInsightsSection
        batch_summary={{
          strength_patterns: [
            {
              pattern: 'solid_opening_play',
              detail: 'You rarely fell behind in development.',
              frequency: '4 games',
            },
          ],
        }}
        coaching_report={{}}
      />
    );

    expect(screen.getByText(/What you did well/i)).toBeInTheDocument();
    expect(screen.getByText(/Solid Opening Play/i)).toBeInTheDocument();
    expect(screen.getByText(/You rarely fell behind/i)).toBeInTheDocument();
    expect(screen.getByText(/Seen in 4 games/i)).toBeInTheDocument();
  });
});
