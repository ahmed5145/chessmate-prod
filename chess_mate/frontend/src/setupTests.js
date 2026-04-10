// jest-dom adds custom jest matchers for asserting on DOM nodes.
import '@testing-library/jest-dom';

// Provide a safe default theme context for component tests that render
// components in isolation without app-level providers.
jest.mock('./context/ThemeContext', () => ({
  ThemeProvider: ({ children }) => children,
  useTheme: () => ({ isDarkMode: false, toggleDarkMode: jest.fn() }),
}));

// Mock the fetch API
global.fetch = jest.fn();

// Mock localStorage with proper jest functions
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: jest.fn((key) => store[key] || null),
    setItem: jest.fn((key, value) => {
      store[key] = value.toString();
    }),
    removeItem: jest.fn((key) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
  };
})();

global.localStorage = localStorageMock;

// Reset all mocks before each test
beforeEach(() => {
  fetch.mockClear();
  Object.values(localStorageMock).forEach(mockFn => {
    if (mockFn.mockClear) {
      mockFn.mockClear();
    }
  });
});
