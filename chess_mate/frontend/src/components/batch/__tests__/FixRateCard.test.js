import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import FixRateCard from '../FixRateCard';

describe('FixRateCard', () => {
  it('renders nothing when fix rate is hidden', () => {
    const { container } = render(
      <MemoryRouter>
        <FixRateCard fixRate={{ show: false }} />
      </MemoryRouter>
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('renders headline and pattern chips when visible', () => {
    render(
      <MemoryRouter>
        <FixRateCard
          fixRate={{
            show: true,
            headline: 'You fixed 2/3 patterns from your January batch.',
            tooltip: 'Fixed means absent or improved swing.',
            patterns: [
              { signature: 'a', label: 'hanging_piece', status: 'fixed' },
              { signature: 'b', label: 'missed_fork', status: 'improved' },
              { signature: 'c', label: 'endgame_slip', status: 'persisting', proof_game_id: 42 },
            ],
          }}
          batchId={9}
        />
      </MemoryRouter>
    );

    expect(
      screen.getByText(/You fixed 2\/3 patterns from your January batch/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Hanging Piece/i)).toBeInTheDocument();
    expect(screen.getByText(/Still needs work/i)).toBeInTheDocument();
    expect(screen.getByText(/Endgame Slip/i)).toBeInTheDocument();
  });
});
