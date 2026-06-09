import React from 'react';
import { render, screen } from '@testing-library/react';
import DashboardPageHeader from '../DashboardPageHeader';

jest.mock('../../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

describe('DashboardPageHeader', () => {
  it('renders eyebrow and subtitle', () => {
    render(
      <DashboardPageHeader
        eyebrow="Coach home"
        subtitle="Welcome back, alice. Here is what to focus on today."
      />
    );

    expect(screen.getByText('Coach home')).toBeInTheDocument();
    expect(screen.getByText(/Welcome back, alice/i)).toBeInTheDocument();
  });

  it('renders eyebrow without subtitle', () => {
    render(<DashboardPageHeader eyebrow="Coach home" subtitle="" />);
    expect(screen.getByText('Coach home')).toBeInTheDocument();
  });
});
