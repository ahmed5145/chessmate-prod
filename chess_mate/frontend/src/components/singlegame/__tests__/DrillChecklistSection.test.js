import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import DrillChecklistSection from '../DrillChecklistSection';

jest.mock('../../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

jest.mock('../../../utils/marketingAnalytics', () => ({
  trackSingleGameEvent: jest.fn(),
}));

describe('DrillChecklistSection', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders checklist items and persists checked state', () => {
    render(
      <DrillChecklistSection
        gameId={99}
        completedAt="2026-06-08T12:00:00Z"
        coaching={{ do_today: 'Practice the fork pattern.' }}
        worstMoment={{ move_number: 8 }}
      />
    );

    expect(screen.getByText('5-minute drill checklist')).toBeInTheDocument();
    const checkbox = screen.getByRole('checkbox', { name: /Practice the fork pattern/i });
    fireEvent.click(checkbox);
    expect(checkbox).toBeChecked();

    const stored = JSON.parse(localStorage.getItem('sg_drill_99_2026-06-08T12_00_00Z'));
    expect(stored.do_today).toBe(true);
  });
});
