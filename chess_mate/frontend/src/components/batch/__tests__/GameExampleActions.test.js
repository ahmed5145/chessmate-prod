import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import GameExampleActions from '../GameExampleActions';
import { scrollToBatchGame } from '../../../utils/batchGameLinks';

jest.mock('../../../utils/batchGameLinks', () => ({
  ...jest.requireActual('../../../utils/batchGameLinks'),
  scrollToBatchGame: jest.fn(),
}));

const perGameResults = [
  {
    game_id: 'game_0',
    platform: 'lichess',
    platform_game_url: 'https://lichess.org/abc123',
  },
];

describe('GameExampleActions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders platform link and scroll action for a game moment', () => {
    render(
      <GameExampleActions
        perGameResults={perGameResults}
        gameId="game_0"
        moveNumber={18}
      />
    );

    expect(screen.getByRole('link', { name: /View on lichess/i })).toHaveAttribute(
      'href',
      'https://lichess.org/abc123'
    );

    fireEvent.click(screen.getByRole('button', { name: /See move 18 in report/i }));
    expect(scrollToBatchGame).toHaveBeenCalledWith('game_0');
  });

  it('renders only scroll action when platform url is missing', () => {
    render(<GameExampleActions perGameResults={[]} gameId="game_0" />);

    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /See in game breakdown/i })).toBeInTheDocument();
  });
});
