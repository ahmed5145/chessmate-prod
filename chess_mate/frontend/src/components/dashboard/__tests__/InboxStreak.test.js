import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import CoachInboxCard from '../CoachInboxCard';
import InboxStreakChip from '../InboxStreakChip';

jest.mock('../../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

jest.mock('../../../utils/marketingAnalytics', () => ({
  trackMarketingEvent: jest.fn(),
}));

describe('InboxStreak', () => {
  it('renders streak chip when count >= 2', () => {
    render(<InboxStreakChip streak={{ show: true, label: '3-day coach streak' }} />);
    expect(screen.getByText(/3-day coach streak/i)).toBeInTheDocument();
  });

  it('hides streak chip below threshold', () => {
    const { container } = render(
      <InboxStreakChip streak={{ show: false, count: 1 }} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('shows streak on coach inbox card header', () => {
    render(
      <MemoryRouter>
        <CoachInboxCard
          priorityInbox={{
            pending_count: 1,
            pending_items: [
              {
                id: '1:1',
                title: 'Fix tactics',
                href: '/game/1/analysis?mode=review',
              },
            ],
            streak: { show: true, label: '4-day coach streak' },
          }}
        />
      </MemoryRouter>
    );

    expect(screen.getByText(/4-day coach streak/i)).toBeInTheDocument();
  });
});
