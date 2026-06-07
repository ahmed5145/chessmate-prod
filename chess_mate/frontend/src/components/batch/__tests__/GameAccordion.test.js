import React from 'react';
import { render, screen, act } from '@testing-library/react';
import GameAccordion from '../GameAccordion';
import { BATCH_GAME_FOCUS_EVENT } from '../../../utils/batchGameLinks';

describe('GameAccordion', () => {
  const games = [
    {
      game_id: 'game_0',
      result: '0-1',
      player_color: 'white',
      opening_name: 'Italian Game: Classical Variation',
      total_moves: 40,
      move_quality: { blunder: 1 },
      critical_moments: [],
    },
    {
      game_id: 'game_1',
      result: '1-0',
      player_color: 'black',
      opening_name: 'Sicilian Defense',
      total_moves: 55,
      move_quality: { blunder: 0 },
      critical_moments: [{ type: 'blunder', move_number: 18 }],
    },
  ];

  beforeEach(() => {
    Element.prototype.scrollIntoView = jest.fn();
  });

  it('shows compact summary with label, result, and opening', () => {
    render(<GameAccordion per_game_results={games} />);

    expect(screen.getByText(/Game 1/i)).toBeInTheDocument();
    expect(screen.getAllByText('L').length).toBeGreaterThan(0);
    expect(screen.getByText(/Italian Game/i)).toBeInTheDocument();
  });

  it('expands and highlights a game when focus event fires', () => {
    jest.useFakeTimers();
    render(<GameAccordion per_game_results={games} />);

    act(() => {
      window.dispatchEvent(
        new CustomEvent(BATCH_GAME_FOCUS_EVENT, { detail: { gameId: 'game_1' } })
      );
    });

    const accordion = screen.getByTestId('batch-game-game_1');
    expect(accordion).toHaveClass('batch-game-highlight');
    expect(accordion).toHaveClass('Mui-expanded');

    act(() => {
      jest.advanceTimersByTime(2100);
    });

    expect(screen.getByTestId('batch-game-game_1')).not.toHaveClass('batch-game-highlight');
    jest.useRealTimers();
  });
});
