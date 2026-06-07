import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';

jest.mock('./context/ThemeContext', () => ({
  ThemeProvider: ({ children }) => <>{children}</>,
  useTheme: () => ({ isDarkMode: false, toggleDarkMode: jest.fn() }),
}));

jest.mock('./contexts/UserContext', () => ({
  UserProvider: ({ children }) => <>{children}</>,
}));

jest.mock('./components/Navbar', () => () => <div>Navbar</div>);
jest.mock('./components/SiteFooter', () => () => <div>SiteFooter</div>);
jest.mock('./routes/AppRoutes', () => () => <div>AppRoutes</div>);
jest.mock('react-hot-toast', () => ({
  Toaster: () => <div>Toaster</div>,
}));
jest.mock('./components/AchievementToast', () => () => null);

const renderApp = () =>
  render(
    <MemoryRouter>
      <App />
    </MemoryRouter>
  );

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
    renderApp();
  });

  it('renders app shell components', () => {
    renderApp();
    expect(screen.getByText('Navbar')).toBeInTheDocument();
    expect(screen.getByText('AppRoutes')).toBeInTheDocument();
    expect(screen.getByText('SiteFooter')).toBeInTheDocument();
    expect(screen.getByText('Toaster')).toBeInTheDocument();
  });
});
