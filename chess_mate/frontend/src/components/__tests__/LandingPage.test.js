import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LandingPage from '../LandingPage';

jest.mock('../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

jest.mock('../../contexts/UserContext', () => ({
  useUser: () => ({ user: null }),
}));

import api from '../../services/api';

jest.mock('../../services/api', () => ({
  get: jest.fn(),
}));

jest.mock('../marketing/BatchReportPreview', () => function MockPreview() {
  return <div data-testid="batch-report-preview">Preview</div>;
});

jest.mock('../marketing/LandingValueBullets', () => function MockBullets() {
  return <div data-testid="value-bullets">Bullets</div>;
});

describe('LandingPage', () => {
  beforeEach(() => {
    api.get.mockResolvedValue({ data: { signup_bonus_credits: 15 } });
  });

  it('renders hero, preview, and primary CTAs for logged-out visitors', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/Your last 10 games/i)).toBeInTheDocument();
    expect(screen.getByText(/Not engine lines per move/i)).toBeInTheDocument();
    expect(screen.getByTestId('batch-report-preview')).toBeInTheDocument();
    expect(screen.getByTestId('value-bullets')).toBeInTheDocument();

    const registerLinks = screen.getAllByRole('link', { name: /Get your own report — free/i });
    expect(registerLinks[0]).toHaveAttribute('href', '/register?from=landing-hero');

    expect(screen.getAllByRole('link', { name: /View full example report/i })[0]).toHaveAttribute(
      'href',
      '/example/batch-report'
    );
  });
});
