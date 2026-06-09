import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import NotificationCenter from '../NotificationCenter';
import {
  fetchNotifications,
  patchNotifications,
} from '../../../services/apiRequests';

jest.mock('../../../services/apiRequests', () => ({
  fetchNotifications: jest.fn(),
  patchNotifications: jest.fn(),
}));

jest.mock('../../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

describe('NotificationCenter', () => {
  beforeEach(() => {
    localStorage.setItem('tokens', JSON.stringify({ access: 'token' }));
    fetchNotifications.mockResolvedValue({
      unread_count: 1,
      notifications: [
        {
          id: 7,
          title: 'Batch coach ready — 5 games',
          body: 'Your priorities are waiting.',
          href: '/batch-report/12',
          is_read: false,
          created_at: new Date().toISOString(),
        },
      ],
    });
    patchNotifications.mockResolvedValue({
      unread_count: 0,
      notifications: [],
      marked_read: 1,
    });
  });

  afterEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
  });

  it('shows unread badge and notification item when opened', async () => {
    render(
      <MemoryRouter>
        <NotificationCenter />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('1')).toBeInTheDocument();
    });
    await userEvent.click(screen.getByLabelText(/Notifications/i));
    expect(screen.getByText(/Batch coach ready/i)).toBeInTheDocument();
  });

  it('marks notification read when item is clicked', async () => {
    render(
      <MemoryRouter>
        <NotificationCenter />
      </MemoryRouter>
    );

    await waitFor(() => expect(fetchNotifications).toHaveBeenCalled());
    await userEvent.click(screen.getByLabelText(/Notifications/i));
    await userEvent.click(screen.getByText(/Batch coach ready/i));

    await waitFor(() => {
      expect(patchNotifications).toHaveBeenCalledWith({ ids: [7] });
    });
  });
});
