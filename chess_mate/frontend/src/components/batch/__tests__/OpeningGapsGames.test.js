import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import OpeningGapsGames from '../OpeningGapsGames';

describe('OpeningGapsGames', () => {
  it('renders loss copy and ChessMate review links', () => {
    render(
      <MemoryRouter>
        <OpeningGapsGames
          gap={{
            loss_copy: 'You lost 2 games in this line',
            lost_games: [
              {
                saved_game_id: 10,
                game_label: 'vs Alpha — Jan 1, 2026',
                href: '/game/10/analysis?mode=review&batch=5',
              },
              {
                saved_game_id: 11,
                game_label: 'vs Beta — Jan 2, 2026',
                href: '/game/11/analysis?mode=review&batch=5',
              },
            ],
          }}
        />
      </MemoryRouter>
    );

    expect(screen.getByText(/You lost 2 games in this line/i)).toBeInTheDocument();
    const reviewLinks = screen.getAllByRole('link', { name: /Review in ChessMate/i });
    expect(reviewLinks).toHaveLength(2);
    expect(reviewLinks[0]).toHaveAttribute('href', '/game/10/analysis?mode=review&batch=5');
  });

  it('returns null when there are no lost games', () => {
    const { container } = render(
      <MemoryRouter>
        <OpeningGapsGames gap={{ lost_games: [] }} />
      </MemoryRouter>
    );
    expect(container).toBeEmptyDOMElement();
  });
});
