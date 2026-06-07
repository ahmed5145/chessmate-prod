import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TrainingPlan from '../TrainingPlan';

describe('TrainingPlan', () => {
  it('renders nothing without a training plan', () => {
    const { container } = render(<TrainingPlan coaching_report={{}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders week accordions with plan copy', async () => {
    render(
      <TrainingPlan
        coaching_report={{
          training_plan: {
            week_1: 'Hanging-piece puzzles daily',
            week_2: 'Review Italian Game lines',
            week_3: 'Endgame rook drills',
          },
        }}
      />
    );

    expect(screen.getByText(/4-week training plan/i)).toBeInTheDocument();
    expect(screen.getByText('Hanging-piece puzzles daily')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /Week 2/i }));
    expect(screen.getByText('Review Italian Game lines')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /Week 4/i }));
    expect(screen.getByText('No training data available')).toBeInTheDocument();
  });
});
