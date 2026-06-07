import React from 'react';
import { render, screen } from '@testing-library/react';
import ExecutiveSummary from '../ExecutiveSummary';

describe('ExecutiveSummary', () => {
  it('humanizes game references in summary bullets', () => {
    render(
      <ExecutiveSummary
        coaching_report={{
          executive_summary:
            'Hanging pieces cost you in game_0. You also rushed in game_1 during the opening.',
        }}
        per_game_results={[
          { game_id: 'game_0', white: 'Alice', black: 'Bob', player_color: 'white' },
          { game_id: 'game_1', white: 'Alice', black: 'Bob', player_color: 'black' },
        ]}
      />
    );

    expect(screen.getByText(/Game 1/i)).toBeInTheDocument();
    expect(screen.getByText(/Game 2/i)).toBeInTheDocument();
    expect(screen.queryByText(/game_0/i)).not.toBeInTheDocument();
  });
});
