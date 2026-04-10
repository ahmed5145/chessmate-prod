import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

jest.mock('./context/ThemeContext', () => ({
  ThemeProvider: ({ children }) => <>{children}</>,
}));

jest.mock('./contexts/UserContext', () => ({
  UserProvider: ({ children }) => <>{children}</>,
}));

jest.mock('./components/Navbar', () => () => <div>Navbar</div>);
jest.mock('./routes/AppRoutes', () => () => <div>AppRoutes</div>);
jest.mock('react-hot-toast', () => ({
  Toaster: () => <div>Toaster</div>,
}));

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });

describe('App', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders without crashing', () => {
    render(<App />);
  });

  it('renders app shell components', () => {
    render(<App />);
    expect(screen.getByText('Navbar')).toBeInTheDocument();
    expect(screen.getByText('AppRoutes')).toBeInTheDocument();
    expect(screen.getByText('Toaster')).toBeInTheDocument();
  });
});
