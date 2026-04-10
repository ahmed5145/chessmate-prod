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
  });

  test('renders credit packages', () => {
    render(
      <BrowserRouter>
        <UserContext.Provider value={defaultProps}>
          <Credits />
        </UserContext.Provider>
      </BrowserRouter>
    );

    expect(screen.getByText(/Basic Package/i)).toBeInTheDocument();
    expect(screen.getByText(/Pro Package/i)).toBeInTheDocument();
    expect(screen.getByText(/Premium Package/i)).toBeInTheDocument();
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
        '/api/purchase-credits/',
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
