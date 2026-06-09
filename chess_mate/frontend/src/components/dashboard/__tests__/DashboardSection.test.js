import React from 'react';
import { render, screen } from '@testing-library/react';
import DashboardSection from '../DashboardSection';

jest.mock('../../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

describe('DashboardSection', () => {
  it('renders title, description, and children', () => {
    render(
      <DashboardSection title="Today's coaching" description="Daily habit loop.">
        <p>Child content</p>
      </DashboardSection>
    );

    expect(screen.getByText("Today's coaching")).toBeInTheDocument();
    expect(screen.getByText('Daily habit loop.')).toBeInTheDocument();
    expect(screen.getByText('Child content')).toBeInTheDocument();
  });

  it('returns null when all children are empty', () => {
    const { container } = render(
      <DashboardSection title="Hidden" description="Should not render">
        {null}
        {false}
      </DashboardSection>
    );

    expect(container).toBeEmptyDOMElement();
  });
});
