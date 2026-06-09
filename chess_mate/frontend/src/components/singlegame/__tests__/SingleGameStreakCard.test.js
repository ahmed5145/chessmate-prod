import React from 'react';
import { render, screen } from '@testing-library/react';
import SingleGameStreakCard from '../SingleGameStreakCard';

jest.mock('../../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

describe('SingleGameStreakCard', () => {
  it('renders nothing when streak is under threshold', () => {
    const { container } = render(<SingleGameStreakCard streak={{ count: 1 }} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders streak copy when count is at least two', () => {
    render(<SingleGameStreakCard streak={{ count: 4 }} />);
    expect(screen.getByText(/4 games without a 1\+ pawn blunder/i)).toBeInTheDocument();
  });
});
