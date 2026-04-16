import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Login from '../Login';
import { toast } from 'react-hot-toast';
import { loginUser } from '../../services/apiRequests';

// Mock react-hot-toast
jest.mock('react-hot-toast');

const mockSetUser = jest.fn();

jest.mock('../../services/apiRequests', () => ({
  loginUser: jest.fn(),
}));

jest.mock('../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

jest.mock('../../contexts/UserContext', () => ({
  useUser: () => ({ setUser: mockSetUser }),
}));

// Mock useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

describe('Login Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const renderWithRouter = () =>
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Login />
      </MemoryRouter>
    );

  test('renders login form', () => {
    renderWithRouter();

    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  test('handles successful login', async () => {
    loginUser.mockResolvedValueOnce({
      success: true,
      user: { id: 1, email: 'test@example.com' },
    });

    renderWithRouter();

    fireEvent.change(screen.getByLabelText(/email address/i), {
      target: { value: 'test@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'testpass' },
    });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/dashboard'));
    expect(loginUser).toHaveBeenCalledWith('test@example.com', 'testpass');
    expect(mockSetUser).toHaveBeenCalledWith({ id: 1, email: 'test@example.com' });
    expect(toast.success).toHaveBeenCalledWith('Login successful!');
  });

  test('handles login failure', async () => {
    loginUser.mockRejectedValueOnce(new Error('Invalid credentials'));

    renderWithRouter();

    fireEvent.change(screen.getByLabelText(/email address/i), {
      target: { value: 'wrong@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'wrongpass' },
    });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Invalid credentials'));
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
