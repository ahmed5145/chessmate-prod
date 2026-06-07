import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import PartialBatchBanner from '../PartialBatchBanner';

describe('PartialBatchBanner', () => {
  beforeEach(() => {
    document.body.innerHTML = '<div id="batch-section-failed-games"></div>';
    Element.prototype.scrollIntoView = jest.fn();
  });

  it('shows analyzed count and view failures action', () => {
    render(
      <PartialBatchBanner
        status="partial"
        batchReport={{
          games_count: 10,
          batch_summary: { games_analyzed: 8 },
          coaching_report: { executive_summary: 'ok' },
          failed_games: [{ game_id: 'game_8', error: 'timeout' }],
        }}
      />
    );

    expect(screen.getByText(/8 of 10 games/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /View failed games/i })).toBeInTheDocument();
  });

  it('scrolls to failed games section', () => {
    render(
      <PartialBatchBanner
        status="partial"
        batchReport={{
          games_count: 6,
          per_game_results: [{}, {}, {}, {}, {}],
          failed_games: [{ game_id: 'game_5', error: 'fail' }],
        }}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /View failed games/i }));
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
  });

  it('renders nothing for completed batches', () => {
    const { container } = render(
      <PartialBatchBanner status="completed" batchReport={{ games_count: 10 }} />
    );
    expect(container).toBeEmptyDOMElement();
  });
});
