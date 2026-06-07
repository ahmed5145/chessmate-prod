import React from 'react';
import { render, screen } from '@testing-library/react';
import RecurringPatterns from '../RecurringPatterns';

jest.mock('../GameExampleActions', () => function MockGameExampleActions({ gameId }) {
  return <button type="button">View {gameId}</button>;
});

const perGameResults = [
  { game_id: 'game_0', white: 'Alice', black: 'Bob', player_color: 'white' },
];

describe('RecurringPatterns', () => {
  it('renders nothing when there are no patterns', () => {
    const { container } = render(<RecurringPatterns batch_summary={{}} per_game_results={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders recurring weaknesses with example game labels', () => {
    render(
      <RecurringPatterns
        batch_summary={{
          recurring_weaknesses: [
            {
              pattern: 'hanging_piece',
              frequency: '4x',
              impact: 'high',
              detail: 'Left pieces undefended in the middlegame',
              example_game_ids: ['game_0'],
            },
          ],
        }}
        per_game_results={perGameResults}
      />
    );

    expect(screen.getByText(/Tactical & endgame patterns/i)).toBeInTheDocument();
    expect(screen.getByText('hanging_piece')).toBeInTheDocument();
    expect(screen.getByText('4x')).toBeInTheDocument();
    expect(screen.getByText('high')).toBeInTheDocument();
    expect(screen.getByText(/Left pieces undefended/i)).toBeInTheDocument();
    expect(screen.getByText(/Example: Game 1/i)).toBeInTheDocument();
  });

  it('renders endgame trouble spots with practice link', () => {
    render(
      <RecurringPatterns
        batch_summary={{
          endgame_insights: [
            {
              endgame_type: 'rook_and_pawn',
              label: 'Rook endings',
              frequency: '2 games',
              study_focus: 'Learn Lucena and Philidor basics',
              study_url: 'https://lichess.org/learn#/1',
            },
          ],
        }}
        per_game_results={[]}
      />
    );

    expect(screen.getByText('Rook endings')).toBeInTheDocument();
    expect(screen.getByText(/Learn Lucena and Philidor/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Practice on Lichess/i })).toHaveAttribute(
      'href',
      'https://lichess.org/learn#/1'
    );
  });
});
