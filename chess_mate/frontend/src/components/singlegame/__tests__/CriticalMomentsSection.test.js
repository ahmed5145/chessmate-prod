import React from 'react';
import { render, screen } from '@testing-library/react';
import CriticalMomentsSection from '../CriticalMomentsSection';

jest.mock('../../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

jest.mock('../../batch/FenBoardImage', () => function MockFenBoardImage() {
  return null;
});

describe('CriticalMomentsSection', () => {
  it('shows rating benchmark copy when present on a moment', () => {
    render(
      <CriticalMomentsSection
        moments={[
          {
            move_number: 14,
            type: 'mistake',
            played_move: 'Nf3',
            best_move: 'Nd2',
            rating_benchmark: {
              copy: 'ChessMate benchmark: players near 1300 miss this tactic about 35-45% of the time in similar positions.',
            },
          },
        ]}
      />
    );

    expect(screen.getByText(/ChessMate benchmark/i)).toBeInTheDocument();
    expect(screen.getByText(/35-45%/)).toBeInTheDocument();
  });
});
