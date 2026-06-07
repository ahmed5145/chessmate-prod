import React from 'react';
import { render, screen } from '@testing-library/react';
import FailedGamesList, { normalizeFailedGames } from '../FailedGamesList';

describe('normalizeFailedGames', () => {
  it('returns empty array for non-arrays', () => {
    expect(normalizeFailedGames(null)).toEqual([]);
    expect(normalizeFailedGames([])).toEqual([]);
  });

  it('normalizes string entries', () => {
    expect(normalizeFailedGames(['game_0'])).toEqual([
      { game_id: 'game_0', message: 'Analysis failed' },
    ]);
  });

  it('prefers message then error on objects', () => {
    expect(
      normalizeFailedGames([
        { game_id: 42, message: 'Invalid PGN' },
        { id: 'game_1', error: 'Timeout' },
        { gameId: 'ext-9' },
      ])
    ).toEqual([
      { game_id: 42, message: 'Invalid PGN' },
      { game_id: 'game_1', message: 'Timeout' },
      { game_id: 'ext-9', message: 'Analysis failed' },
    ]);
  });

  it('falls back to indexed game id for invalid rows', () => {
    expect(normalizeFailedGames([null, 7])).toEqual([
      { game_id: 'game_0', message: 'Analysis failed' },
      { game_id: 'game_1', message: 'Analysis failed' },
    ]);
  });
});

describe('FailedGamesList', () => {
  it('renders nothing when there are no failures', () => {
    const { container } = render(<FailedGamesList failures={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders failed game labels and messages', () => {
    render(
      <FailedGamesList
        failures={[
          { game_id: 'game_0', message: 'Invalid PGN' },
          { game_id: 'lichess-abc', message: 'Engine timeout' },
        ]}
      />
    );

    expect(screen.getByText('Failed games (2)')).toBeInTheDocument();
    expect(screen.getByText('Game 1 (game_0)')).toBeInTheDocument();
    expect(screen.getByText('Invalid PGN')).toBeInTheDocument();
    expect(screen.getByText('lichess-abc')).toBeInTheDocument();
    expect(screen.getByText('Engine timeout')).toBeInTheDocument();
  });
});
