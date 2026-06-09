import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import BatchContextBanner from '../BatchContextBanner';

jest.mock('../../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

jest.mock('../../../services/apiRequests', () => ({
  markPriorityInboxReviewed: jest.fn(),
}));

jest.mock('../../../utils/marketingAnalytics', () => ({
  trackMarketingEvent: jest.fn(),
}));

const { markPriorityInboxReviewed } = require('../../../services/apiRequests');
const { trackMarketingEvent } = require('../../../utils/marketingAnalytics');

describe('BatchContextBanner', () => {
  beforeEach(() => {
    markPriorityInboxReviewed.mockReset();
    trackMarketingEvent.mockReset();
  });

  it('renders priority, pattern, and opening from batch_context', () => {
    render(
      <MemoryRouter>
        <BatchContextBanner
          batchId={9}
          move={18}
          priority={1}
          batchContext={{
            batch_id: 9,
            priority_rank: 1,
            priority: { title: 'Fix Najdorf prep' },
            pattern_label: 'hanging_pieces',
            opening_name: 'Sicilian Defense',
            opening_eco: 'B90',
            game_result: '0-1',
            linked_moment: { move_number: 18 },
            classification_disclaimer: 'Batch depth-14 differs from depth-20.',
          }}
        />
      </MemoryRouter>
    );

    expect(screen.getByText(/From your Batch Coach report/i)).toBeInTheDocument();
    expect(screen.getByText('hanging_pieces')).toBeInTheDocument();
    expect(screen.getByText(/Fix Najdorf prep/i)).toBeInTheDocument();
    expect(screen.getByText(/Sicilian Defense \(B90\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Batch depth-14 differs/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Back to batch report/i })).toHaveAttribute('href', '/batch-report/9');
    expect(screen.getByRole('button', { name: /Mark reviewed/i })).toBeInTheDocument();
  });

  it('renders coach alignment badge when batch_context includes score', () => {
    render(
      <MemoryRouter>
        <BatchContextBanner
          batchId={9}
          batchContext={{
            batch_id: 9,
            priority_rank: 1,
            coach_alignment: {
              alignment_pct: 75,
              tier: 'high',
              headline: 'Batch focused on opening — this game confirms 3/4 critical moments.',
              tooltip: '3 of 4 depth-20 critical moments occurred in the batch opening focus area.',
            },
          }}
        />
      </MemoryRouter>
    );

    expect(screen.getByText(/75% aligned/i)).toBeInTheDocument();
    expect(screen.getByText(/confirms 3\/4 critical moments/i)).toBeInTheDocument();
  });

  it('marks priority reviewed via API', async () => {
    const user = userEvent.setup();
    markPriorityInboxReviewed.mockResolvedValue({ detail: 'Priority marked reviewed' });

    render(
      <MemoryRouter>
        <BatchContextBanner batchId={9} priority={2} />
      </MemoryRouter>
    );

    await user.click(screen.getByRole('button', { name: /Mark reviewed/i }));

    await waitFor(() => {
      expect(markPriorityInboxReviewed).toHaveBeenCalledWith({
        batchId: 9,
        priorityIndex: 2,
      });
    });
    expect(trackMarketingEvent).toHaveBeenCalledWith('priority_inbox_reviewed', {
      batch_id: 9,
      priority_index: 2,
      surface: 'single_game',
    });
    expect(screen.getByRole('button', { name: /Marked reviewed/i })).toBeDisabled();
  });

  it('returns null without batch id', () => {
    const { container } = render(
      <MemoryRouter>
        <BatchContextBanner batchId={null} />
      </MemoryRouter>
    );
    expect(container).toBeEmptyDOMElement();
  });
});
