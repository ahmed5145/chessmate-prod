import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import WelcomeGuide, { shouldShowWelcomeGuide } from '../WelcomeGuide';
import { updateUserProfile } from '../../services/apiRequests';
import api from '../../services/api';

const mockRefreshUserData = jest.fn();

jest.mock('../../services/apiRequests');
jest.mock('../../contexts/UserContext', () => ({
  useUser: () => ({
    user: {
      username: 'newbie',
      preferences: {},
      credits: 15,
    },
    refreshUserData: mockRefreshUserData,
  }),
}));
jest.mock('../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

describe('shouldShowWelcomeGuide', () => {
  it('returns true when welcome_guide_seen is not set', () => {
    expect(shouldShowWelcomeGuide({ preferences: {} })).toBe(true);
  });

  it('returns false after welcome_guide_seen is true', () => {
    expect(shouldShowWelcomeGuide({ preferences: { welcome_guide_seen: true } })).toBe(false);
  });
});

describe('WelcomeGuide', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    updateUserProfile.mockResolvedValue({});
    mockRefreshUserData.mockResolvedValue(undefined);
    jest.spyOn(api, 'get').mockResolvedValue({ data: { signup_bonus_credits: 15 } });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('renders welcome content for new users', async () => {
    render(
      <BrowserRouter>
        <WelcomeGuide />
      </BrowserRouter>
    );

    expect(await screen.findByText('Welcome to ChessMate')).toBeInTheDocument();
    expect(screen.getByText(/15 free credits to get started/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /import games/i })).toHaveAttribute('href', '/fetch-games');
  });

  it('dismisses and persists welcome_guide_seen', async () => {
    render(
      <BrowserRouter>
        <WelcomeGuide />
      </BrowserRouter>
    );

    fireEvent.click(screen.getByRole('button', { name: /got it, don't show again/i }));

    await waitFor(() => {
      expect(updateUserProfile).toHaveBeenCalledWith({
        preferences: { welcome_guide_seen: true },
      });
    });
    expect(mockRefreshUserData).toHaveBeenCalled();
  });
});
