import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Profile from '../Profile';
import { fetchProfileData } from '../../services/apiRequests';

jest.mock('react-hot-toast', () => ({
  toast: { error: jest.fn(), success: jest.fn() },
}));

jest.mock('../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

jest.mock('../../services/apiRequests', () => ({
  fetchProfileData: jest.fn(),
}));

jest.mock('../LoadingSpinner', () => function MockSpinner() {
  return <div>Loading...</div>;
});

jest.mock('../profile/ProfileLinkedAccounts', () => function MockLinkedAccounts() {
  return null;
});

const profileFixture = {
  username: 'player1',
  total_games: 12,
  win_rate: 55,
  credits: 10,
  achievements: [
    { name: 'Rising Player', description: 'Play 10 games', progress: 5, target: 10, completed: false },
    { name: 'Rating Star', description: 'Reach 1200', progress: 1, target: 1, completed: true },
  ],
  time_control_distribution: { bullet: 0, blitz: 100, rapid: 0, classical: 0 },
};

describe('Profile achievements', () => {
  beforeEach(() => {
    fetchProfileData.mockResolvedValue(profileFixture);
  });

  it('shows back button when viewing a category inside the modal', async () => {
    render(<Profile />);

    await waitFor(
      () => {
        expect(screen.getAllByText('Achievements').length).toBeGreaterThan(0);
      },
      { timeout: 15000 },
    );

    fireEvent.click(screen.getByRole('button', { name: /View All/i }));

    const categoryButtons = await screen.findAllByRole('button', { name: /Game Milestones/i });
    fireEvent.click(categoryButtons[categoryButtons.length - 1]);

    expect(screen.getByRole('button', { name: /Back to all achievements/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Back to all achievements/i }));

    expect(screen.getByText('All Achievements')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /Rating Achievements/i }).length).toBeGreaterThan(0);
  });
});
