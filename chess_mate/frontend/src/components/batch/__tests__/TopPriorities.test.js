import React from 'react';
import { render, screen } from '@testing-library/react';
import TopPriorities from '../TopPriorities';

jest.mock('../PriorityCard', () => function MockPriorityCard({ priority, showLichessLink }) {
  return (
    <div data-testid={`priority-${priority.rank}`}>
      {priority.title}
      {showLichessLink ? ' (lichess)' : ' (no-lichess)'}
    </div>
  );
});

const priorities = [
  {
    rank: 1,
    title: 'Stop hanging pieces',
    why_it_matters: 'You lost material in game_0',
    how_to_fix: 'Scan for undefended pieces',
    specific_drill: 'Do 10 puzzles',
  },
  {
    rank: 2,
    title: 'Improve opening plans',
    why_it_matters: 'You fell behind early',
    how_to_fix: 'Study your main lines',
    specific_drill: 'Review Italian Game',
  },
];

describe('TopPriorities', () => {
  it('renders nothing without priorities', () => {
    const { container } = render(<TopPriorities coaching_report={{}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders priority cards and hides lichess link on rank 1', () => {
    render(
      <TopPriorities
        coaching_report={{ top_3_priorities: priorities }}
        per_game_results={[{ game_id: 'game_0' }]}
      />
    );

    expect(screen.getByText(/Top 3 priorities/i)).toBeInTheDocument();
    expect(screen.getByTestId('priority-1')).toHaveTextContent('Stop hanging pieces (no-lichess)');
    expect(screen.getByTestId('priority-2')).toHaveTextContent('Improve opening plans (lichess)');
  });
});
