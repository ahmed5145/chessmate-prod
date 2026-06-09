import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import CoachInboxCard from '../CoachInboxCard';

jest.mock('../../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

jest.mock('../../../utils/marketingAnalytics', () => ({
  trackMarketingEvent: jest.fn(),
}));

const { trackMarketingEvent } = require('../../../utils/marketingAnalytics');

describe('CoachInboxCard', () => {
  beforeEach(() => {
    trackMarketingEvent.mockClear();
  });

  it('renders pending priorities with links', () => {
    render(
      <MemoryRouter>
        <CoachInboxCard
          priorityInbox={{
            pending_count: 1,
            pending_items: [
              {
                id: '5:1',
                batch_id: 5,
                priority_index: 1,
                title: 'Fix hanging pieces',
                proof_label: 'Sicilian Defense example: vs rival42, move 14',
                drill: 'Review game_2 move 14',
                href: '/game/12/analysis?mode=review&batch=5&priority=1&move=14',
              },
            ],
          }}
        />
      </MemoryRouter>
    );

    expect(screen.getByText('Coach inbox')).toBeInTheDocument();
    expect(screen.getByText('1 pending')).toBeInTheDocument();
    expect(screen.getByText('Fix hanging pieces')).toBeInTheDocument();
    expect(screen.getByText(/Sicilian Defense example/i)).toBeInTheDocument();
    const link = screen.getByRole('link', { name: /Fix hanging pieces/i });
    expect(link).toHaveAttribute('href', '/game/12/analysis?mode=review&batch=5&priority=1&move=14');
  });

  it('tracks analytics when opening an inbox item', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <CoachInboxCard
          priorityInbox={{
            pending_count: 1,
            pending_items: [
              {
                id: '5:1',
                batch_id: 5,
                priority_index: 1,
                title: 'Fix hanging pieces',
                href: '/game/12/analysis?mode=review&batch=5&priority=1',
              },
            ],
          }}
        />
      </MemoryRouter>
    );

    await user.click(screen.getByRole('link', { name: /Fix hanging pieces/i }));
    expect(trackMarketingEvent).toHaveBeenCalledWith('priority_inbox_open', {
      batch_id: 5,
      priority_index: 1,
      surface: 'dashboard',
    });
  });

  it('shows empty state CTA when no pending items', () => {
    render(
      <MemoryRouter>
        <CoachInboxCard
          priorityInbox={{
            pending_count: 0,
            pending_items: [],
            empty_state_cta: '/batch-analysis',
            empty_state_label: 'Start Batch Coach',
          }}
        />
      </MemoryRouter>
    );

    expect(screen.getByText(/No priorities waiting/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Start Batch Coach/i })).toHaveAttribute(
      'href',
      '/batch-analysis'
    );
  });
});
