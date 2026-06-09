import React from 'react';
import { render, screen } from '@testing-library/react';
import TrainingBlockSection from '../TrainingBlockSection';

jest.mock('../../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

describe('TrainingBlockSection', () => {
  it('renders structured phase motifs without crashing', () => {
    render(
      <TrainingBlockSection
        trainingBlock={{
          focus_areas: ['Improve middlegame accuracy'],
          drills: ['Tactical puzzles focusing on middlegame positions'],
          phase_motifs: {
            weakest_phase: 'middlegame',
            correction_rule: 'Review tactical patterns in similar positions',
            motifs: [
              {
                name: 'Missed critical move in middlegame',
                count: 1,
                evidence: [{ move: 12, san: 'Nf3' }],
                correction_rule: 'Review tactical patterns in similar positions and practice tactics',
              },
            ],
          },
          weekly_target: {
            goal: 'Increase overall accuracy to 50%',
            measure: 'Analyze games and track accuracy improvement',
          },
        }}
      />
    );

    expect(screen.getByText('Training focus')).toBeInTheDocument();
    expect(screen.getByText(/Missed critical move in middlegame/i)).toBeInTheDocument();
    expect(screen.getByText(/Review tactical patterns in similar positions and practice tactics/i)).toBeInTheDocument();
    expect(screen.getByText(/Increase overall accuracy to 50%/i)).toBeInTheDocument();
    expect(screen.getByText(/Evidence: move 12 Nf3/i)).toBeInTheDocument();
  });
});
