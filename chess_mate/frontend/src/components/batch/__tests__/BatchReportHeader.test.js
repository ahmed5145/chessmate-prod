import React from 'react';
import { render, screen } from '@testing-library/react';
import BatchReportHeader from '../BatchReportHeader';

describe('BatchReportHeader', () => {
  it('renders nothing without batch summary', () => {
    const { container } = render(<BatchReportHeader batch_summary={null} games_count={10} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders record, move match, eval stability, and blunder chip', () => {
    render(
      <BatchReportHeader
        games_count={10}
        batch_summary={{
          games_analyzed: 10,
          date_range: 'May 2025',
          win_loss_draw: { wins: 6, losses: 2, draws: 2 },
          overall_accuracy_pct: 72.4,
          overall_eval_stability: 0.81,
          player_rating: 1540,
          most_common_blunder_type: 'hanging_piece',
        }}
      />
    );

    expect(screen.getByText(/6W · 2L · 2D/)).toBeInTheDocument();
    expect(screen.getByText('72.4%')).toBeInTheDocument();
    expect(screen.getByText('81%')).toBeInTheDocument();
    expect(screen.getByText('1540')).toBeInTheDocument();
    expect(screen.getByText(/Top issue: Hanging Piece/i)).toBeInTheDocument();
    expect(screen.getByText(/May 2025/)).toBeInTheDocument();
  });

  it('hides blunder chip when type is unknown', () => {
    render(
      <BatchReportHeader
        batch_summary={{
          games_analyzed: 5,
          win_loss_draw: { wins: 3, losses: 2, draws: 0 },
          overall_accuracy: 0.7,
          most_common_blunder_type: 'unknown',
        }}
      />
    );

    expect(screen.queryByText(/Top issue:/i)).not.toBeInTheDocument();
    expect(screen.getByText('70%')).toBeInTheDocument();
  });
});
