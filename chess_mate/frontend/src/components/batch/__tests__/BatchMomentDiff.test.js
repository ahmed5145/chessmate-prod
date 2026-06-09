import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import BatchMomentDiff from '../BatchMomentDiff';

describe('BatchMomentDiff', () => {
  it('renders nothing when moment diff is hidden', () => {
    const { container } = render(
      <MemoryRouter>
        <BatchMomentDiff momentDiff={{ show: false }} />
      </MemoryRouter>
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('renders compared patterns with swing columns and status chips', () => {
    render(
      <MemoryRouter>
        <BatchMomentDiff
          batchId={12}
          momentDiff={{
            show: true,
            title: 'Compared to last batch',
            previous_batch_id: 11,
            previous_batch_month: 'January',
            counts: { resolved: 1, unchanged: 1, new: 1 },
            rows: [
              {
                signature: 'a',
                label: 'hanging_piece',
                status: 'resolved',
                previous_swing: 1.4,
                current_swing: 0.6,
                sparkline: [1.4, 0.9, 0.6],
                proof_game_id: 42,
              },
              {
                signature: 'b',
                label: 'missed_fork',
                status: 'unchanged',
                previous_swing: 0.9,
                current_swing: 0.85,
                sparkline: [0.9, 0.85],
              },
              {
                signature: 'c',
                label: 'endgame_slip',
                status: 'new',
                previous_swing: null,
                current_swing: 1.1,
                sparkline: [1.1],
              },
            ],
          }}
        />
      </MemoryRouter>
    );

    expect(screen.getByText(/Compared to last batch/i)).toBeInTheDocument();
    expect(screen.getByText(/1 resolved/i)).toBeInTheDocument();
    expect(screen.getByText(/Hanging Piece/i)).toBeInTheDocument();
    expect(screen.getAllByText(/^Resolved$/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/^New$/i).length).toBeGreaterThan(0);
    expect(screen.getByRole('link', { name: /Review game/i })).toHaveAttribute(
      'href',
      '/game/42/analysis?batch=12'
    );
  });
});
