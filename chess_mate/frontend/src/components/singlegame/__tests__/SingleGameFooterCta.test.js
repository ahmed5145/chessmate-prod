import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SingleGameFooterCta from '../SingleGameFooterCta';

jest.mock('../../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

jest.mock('../../../utils/marketingAnalytics', () => ({
  trackSingleGameEvent: jest.fn(),
}));

const { trackSingleGameEvent } = require('../../../utils/marketingAnalytics');

describe('SingleGameFooterCta', () => {
  beforeEach(() => {
    trackSingleGameEvent.mockClear();
  });

  it('shows batch upsell when no batch context', () => {
    render(
      <MemoryRouter>
        <SingleGameFooterCta />
      </MemoryRouter>
    );

    expect(screen.getByText(/Want patterns across many games/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Start Batch Coach/i })).toHaveAttribute('href', '/batch-analysis');
  });

  it('shows pattern counts and tracks analytics when batch context present', () => {
    render(
      <MemoryRouter>
        <SingleGameFooterCta
          gameId={42}
          batchContext={{
            batch_id: 7,
            priority: { title: 'Fix tactics', rank: 1 },
            priority_rank: 1,
            pattern_count: 3,
            batch_game_count: 8,
          }}
        />
      </MemoryRouter>
    );

    expect(screen.getByText(/3 of 8 games/i)).toBeInTheDocument();
    const link = screen.getByRole('link', { name: /See batch priorities/i });
    expect(link).toHaveAttribute('href', '/batch-report/7?priority=1');

    fireEvent.click(link);
    expect(trackSingleGameEvent).toHaveBeenCalledWith(
      'single_game_batch_cta_click',
      expect.objectContaining({
        game_id: 42,
        batch_id: 7,
        variant: 'batch',
      })
    );
  });
});
