import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { UserContext } from '../../contexts/UserContext';
import { ThemeProvider } from '../../context/ThemeContext';
import Games from '../Games';
import { toast } from 'react-hot-toast';
import { fetchUserGames } from '../../services/apiRequests';
import { checkAuthStatus } from '../../services/authService';
import { analyzeSpecificGame } from '../../services/gameAnalysisService';

// Mock react-hot-toast
jest.mock('react-hot-toast');

jest.mock('../../context/ThemeContext', () => ({
  ThemeProvider: ({ children }) => <>{children}</>,
  useTheme: () => ({ isDarkMode: false, isAuthenticated: true }),
}));

jest.mock('../../services/apiRequests', () => ({
  fetchUserGames: jest.fn(),
  checkAnalysisStatus: jest.fn(),
  fetchGameAnalysis: jest.fn(),
}));

jest.mock('../../services/gameAnalysisService', () => ({
  checkMultipleAnalysisStatuses: jest.fn().mockResolvedValue({}),
  analyzeSpecificGame: jest.fn(),
  shouldPollStatus: jest.fn((status, progress) => {
    const normalizedStatus = String(status || '').toUpperCase();
    const numericProgress = Number(progress) || 0;
    if (numericProgress >= 100) return false;
    const SUCCESS_STATUSES = new Set(['SUCCESS', 'COMPLETED']);
    const TERMINAL_FAILURE_STATUSES = new Set(['FAILURE', 'FAILED', 'ERROR', 'REVOKED', 'AUTH_ERROR']);
    if (SUCCESS_STATUSES.has(normalizedStatus) || TERMINAL_FAILURE_STATUSES.has(normalizedStatus)) {
      return false;
    }
    return true;
  }),
}));

jest.mock('../../services/authService', () => ({
  checkAuthStatus: jest.fn().mockReturnValue(true),
}));

// Mock useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

describe('Games Component', () => {
  const mockGames = [
    {
      id: 1,
      opponent: 'opponent1',
      result: 'win',
      played_at: '2024-01-01T12:00:00Z',
      game_url: 'https://chess.com/game/1',
      opening_name: 'Sicilian Defense',
      is_white: true,
    },
    {
      id: 2,
      opponent: 'opponent2',
      result: 'loss',
      played_at: '2024-01-02T12:00:00Z',
      game_url: 'https://chess.com/game/2',
      opening_name: 'Queens Gambit',
      is_white: false,
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    fetchUserGames.mockResolvedValue(mockGames);
    checkAuthStatus.mockResolvedValue(true);
    analyzeSpecificGame.mockResolvedValue({ status: 'success' });
  });

  const renderWithProviders = () =>
    render(
      <ThemeProvider>
        <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <UserContext.Provider value={{ credits: 100 }}>
            <Games />
          </UserContext.Provider>
        </MemoryRouter>
      </ThemeProvider>
    );

  test('renders games list', async () => {
    renderWithProviders();

    await waitFor(() => {
      expect(screen.getByText(/opponent1/i)).toBeInTheDocument();
      expect(screen.getByText(/opponent2/i)).toBeInTheDocument();
      expect(screen.getByText(/Sicilian Defense/i)).toBeInTheDocument();
      expect(screen.getByText(/Queens Gambit/i)).toBeInTheDocument();
    });
  });

  test('renders filter controls', async () => {
    renderWithProviders();

    await waitFor(() => {
      expect(fetchUserGames).toHaveBeenCalled();
    });
  });

  test('handles fetch error', async () => {
    fetchUserGames.mockRejectedValueOnce(new Error('Failed to fetch games'));

    renderWithProviders();

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to fetch games');
    });
  });

  test('displays loading state', () => {
    fetchUserGames.mockImplementation(() => new Promise(() => {})); // Never resolves

    renderWithProviders();

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  test('handles analyze game click', async () => {
    renderWithProviders();

    await waitFor(() => {
      const analyzeButtons = screen.getAllByRole('button', { name: /analyze/i });
      fireEvent.click(analyzeButtons[0]);
      expect(mockNavigate).toHaveBeenCalledWith('/game/2/analysis');
    });
  });
});
