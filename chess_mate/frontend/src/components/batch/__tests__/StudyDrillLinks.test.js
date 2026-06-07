import React from 'react';
import { render, screen } from '@testing-library/react';
import StudyDrillLinks from '../StudyDrillLinks';

describe('StudyDrillLinks', () => {
  it('renders nothing when there are no drill links', () => {
    const { container } = render(<StudyDrillLinks batch_summary={{}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders explicit drill links with kind labels', () => {
    render(
      <StudyDrillLinks
        links={[
          { kind: 'puzzle', label: 'Fork training', url: 'https://lichess.org/training/fork' },
          { kind: 'endgame', label: 'Rook endings', url: 'https://lichess.org/learn#/1' },
        ]}
      />
    );

    expect(screen.getByText(/More suggested drills/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Fork training/i })).toHaveAttribute(
      'href',
      'https://lichess.org/training/fork'
    );
    expect(screen.getByText('Tactics')).toBeInTheDocument();
    expect(screen.getByText('Endgame')).toBeInTheDocument();
  });

  it('collects links from batch summary when links prop is omitted', () => {
    render(
      <StudyDrillLinks
        batch_summary={{
          recurring_weaknesses: [{ pattern: 'fork', frequency: 3 }],
        }}
      />
    );

    expect(screen.getByText(/More suggested drills/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Fork Puzzles/i })).toHaveAttribute(
      'href',
      'https://lichess.org/training/fork'
    );
  });
});
