import React from 'react';
import { render, screen } from '@testing-library/react';
import PracticeNextStrip from '../PracticeNextStrip';

describe('PracticeNextStrip', () => {
  it('renders practice links', () => {
    render(
      <PracticeNextStrip
        links={[
          {
            source: 'priority',
            headline: 'Priority #1 drill',
            description: 'Do 15 hanging-piece puzzles.',
            label: 'Train on Lichess',
            url: 'https://lichess.org/training/hangingPiece',
            kind: 'puzzle',
          },
        ]}
      />
    );

    expect(screen.getByText(/Practice next/i)).toBeInTheDocument();
    expect(screen.getByText(/Priority #1 drill/i)).toBeInTheDocument();
    expect(screen.getByText(/Do 15 hanging-piece puzzles/i)).toBeInTheDocument();
  });

  it('renders nothing without links', () => {
    const { container } = render(<PracticeNextStrip links={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
