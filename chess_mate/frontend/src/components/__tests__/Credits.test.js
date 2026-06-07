import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { UserContext } from '../../contexts/UserContext';
import Credits from '../Credits';
import { toast } from 'react-hot-toast';
import api from '../../services/api';

jest.mock('../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

// Mock react-hot-toast
jest.mock('react-hot-toast');

jest.mock('../../services/api', () => ({
  post: jest.fn(),
  get: jest.fn(),
}));

// Mock useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

describe('Credits Component', () => {
  const mockSetCredits = jest.fn();
  const mockFetchUserData = jest.fn();
  const defaultProps = {
    credits: 100,
    setCredits: mockSetCredits,
    fetchUserData: mockFetchUserData,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    api.post.mockReset();
    api.get.mockReset();
    api.get.mockResolvedValue({ data: { packages: [] } });
  });

  test('renders how credits work summary', async () => {
    api.get.mockResolvedValueOnce({
      data: {
        packages: [],
        summary_points: [
          '1 credit per game import from Chess.com or Lichess',
          'Batch Coach analysis is included once games are on your account',
        ],
        batch_included: true,
        batch_games_recommended: 10,
      },
    });

    render(
      <BrowserRouter>
        <UserContext.Provider value={defaultProps}>
          <Credits />
        </UserContext.Provider>
      </BrowserRouter>
    );

    expect(await screen.findByRole('heading', { name: /How credits work/i })).toBeInTheDocument();
    expect(screen.getByText(/1 credit per game import from Chess.com or Lichess/i)).toBeInTheDocument();
  });

  test('renders credit packages', () => {
    render(
      <BrowserRouter>
        <UserContext.Provider value={defaultProps}>
          <Credits />
        </UserContext.Provider>
      </BrowserRouter>
    );

    expect(screen.getByRole('heading', { name: /Buy credits once/i })).toBeInTheDocument();
    expect(screen.getByText(/Not a subscription — credits never expire/i)).toBeInTheDocument();
    expect(screen.getByText(/Coach Starter/i)).toBeInTheDocument();
    expect(screen.getByText(/Coach Plus/i)).toBeInTheDocument();
    expect(screen.getByText(/Coach Pro/i)).toBeInTheDocument();
  });

  test('displays current credits', () => {
    render(
      <BrowserRouter>
        <UserContext.Provider value={defaultProps}>
          <Credits />
        </UserContext.Provider>
      </BrowserRouter>
    );

    expect(screen.getByText(/currently have\s*100\s*credits available/i)).toBeInTheDocument();
  });

  test('handles successful purchase initiation', async () => {
    localStorage.setItem('tokens', JSON.stringify({ access: 'test-access-token' }));
    api.post.mockResolvedValueOnce({ data: { checkout_url: 'https://stripe.com/checkout' } });

    render(
      <BrowserRouter>
        <UserContext.Provider value={defaultProps}>
          <Credits />
        </UserContext.Provider>
      </BrowserRouter>
    );

    // Find and click the purchase button for the Basic package
    const purchaseButtons = screen.getAllByRole('button', { name: /purchase/i });
    fireEvent.click(purchaseButtons[0]); // Basic package button

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/api/v1/purchase-credits/',
        { package_id: 'basic' },
        {
          headers: {
            Authorization: 'Bearer test-access-token',
          },
        }
      );
    });
  });

  test('handles purchase error', async () => {
    localStorage.setItem('tokens', JSON.stringify({ access: 'test-access-token' }));
    api.post.mockRejectedValueOnce(new Error('Purchase failed'));

    render(
      <BrowserRouter>
        <UserContext.Provider value={defaultProps}>
          <Credits />
        </UserContext.Provider>
      </BrowserRouter>
    );

    const purchaseButtons = screen.getAllByRole('button', { name: /purchase/i });
    fireEvent.click(purchaseButtons[0]); // Basic package button

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Purchase failed');
    });
  });

  test('updates credits display when credits change', () => {
    const { rerender } = render(
      <BrowserRouter>
        <UserContext.Provider value={defaultProps}>
          <Credits />
        </UserContext.Provider>
      </BrowserRouter>
    );

    expect(screen.getByText(/currently have\s*100\s*credits available/i)).toBeInTheDocument();

    rerender(
      <BrowserRouter>
        <UserContext.Provider value={{ ...defaultProps, credits: 200 }}>
          <Credits />
        </UserContext.Provider>
      </BrowserRouter>
    );

    expect(screen.getByText(/currently have\s*200\s*credits available/i)).toBeInTheDocument();
  });
});
