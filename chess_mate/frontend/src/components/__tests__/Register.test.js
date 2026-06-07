import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Register from '../Register';

jest.mock('../../services/apiRequests', () => ({
  registerUser: jest.fn(),
}));
jest.mock('../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: true }),
}));

describe('Register', () => {
  it('shows passwords match requirement bullet', () => {
    render(
      <BrowserRouter>
        <Register />
      </BrowserRouter>
    );

    expect(screen.getByText('Passwords match')).toBeInTheDocument();
  });

  it('uses dark-mode friendly confirm password field classes', () => {
    render(
      <BrowserRouter>
        <Register />
      </BrowserRouter>
    );

    const confirmField = screen.getByLabelText(/confirm password/i);
    expect(confirmField).toHaveAttribute('autoComplete', 'new-password');
    expect(confirmField.className).toMatch(/bg-gray-700/);
    expect(confirmField.className).toMatch(/text-white/);
  });
});
